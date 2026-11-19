"""Tests for the public review submission endpoint."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.deps import get_review_service
from app.services.review_service import ReviewService
from main import app

#: A valid submission, reused by the tests that only vary one field.
_VALID_REVIEW = {"author_name": "Test User", "email": "test@example.com", "text": "This is a test review."}


def test_submit_review_success(client: TestClient) -> None:
    """Test successful review submission."""
    response = client.post(
        "/api/reviews", json={"author_name": "Test User", "email": "test@example.com", "text": "This is a test review."}
    )

    assert response.status_code == 202
    data = response.json()
    assert data["author_name"] == "Test User"
    assert "email" not in data  # Email must not be exposed in public ReviewDto
    assert data["text"] == "This is a test review."
    assert data["analysis_status"] == "Pending"
    assert "id" in data


def test_submit_review_enqueues_analysis(client: TestClient, mock_celery_enqueue: MagicMock) -> None:
    """The submitted review is handed over to the background worker."""
    response = client.post("/api/reviews", json=_VALID_REVIEW)

    assert response.status_code == 202
    mock_celery_enqueue.assert_called_once()
    assert mock_celery_enqueue.call_args.kwargs["args"] == [response.json()["id"]]
    assert mock_celery_enqueue.call_args.kwargs["queue"] == "reviews"


def test_submit_review_survives_broker_outage(client: TestClient, mock_celery_enqueue: MagicMock) -> None:
    """A broken broker must not lose the review itself."""
    mock_celery_enqueue.side_effect = OSError("no broker")

    response = client.post("/api/reviews", json=_VALID_REVIEW)

    assert response.status_code == 202
    assert response.json()["analysis_status"] == "Pending"


def test_submit_review_missing_fields(client: TestClient) -> None:
    """Test review submission with missing required fields."""
    response = client.post(
        "/api/reviews",
        json={
            "author_name": "Test User",
            "email": "test@example.com",
            # Missing "text" field
        },
    )

    assert response.status_code == 422


def test_submit_review_empty_fields_names_every_field(client: TestClient) -> None:
    """An empty form is reported with one sentence per field.

    The message is what the user reads, so a blank field has to be named
    the same way as a missing one — the frontend shows it verbatim.
    """
    response = client.post(
        "/api/reviews",
        json={"author_name": "", "email": "", "text": ""},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == ("Name is required. Email is required. Review is required")


def test_submit_review_invalid_email(client: TestClient) -> None:
    """Test review submission with invalid email."""
    response = client.post(
        "/api/reviews", json={"author_name": "Test User", "email": "invalid-email", "text": "This is a test review."}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Email must be a valid email address"


def test_submit_review_drops_nul_characters(client: TestClient) -> None:
    """PostgreSQL cannot store a NUL character, so it is removed, not a 500."""
    response = client.post(
        "/api/reviews",
        json={**_VALID_REVIEW, "author_name": "Te\u0000st", "text": "Hello\u0000 world"},
    )

    assert response.status_code == 202
    assert response.json()["author_name"] == "Test"
    assert response.json()["text"] == "Hello world"


def test_submit_review_made_of_nul_characters_is_blank(client: TestClient) -> None:
    """A field holding nothing but NUL characters counts as an empty one."""
    response = client.post("/api/reviews", json={**_VALID_REVIEW, "text": "\u0000\u0000"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Review is required"


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ("{bad", "Request body must be valid JSON"),
        ("", "Request body is required"),
        ("[1]", "Request body: Input should be a valid dictionary or object to extract fields from"),
    ],
)
def test_a_malformed_body_gets_a_readable_message(client: TestClient, body: str, detail: str) -> None:
    """An error about the body as a whole is named, not shown as a bare position."""
    response = client.post("/api/reviews", content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert response.json()["detail"] == detail


def test_a_database_outage_is_a_readable_503(client: TestClient) -> None:
    """A lost database connection is reported as JSON 503, not as a bare 500."""

    def unavailable() -> ReviewService:
        raise OperationalError("SELECT 1", {}, ConnectionRefusedError("connection refused"))

    app.dependency_overrides[get_review_service] = unavailable
    try:
        response = client.post("/api/reviews", json=_VALID_REVIEW)
    finally:
        del app.dependency_overrides[get_review_service]

    assert response.status_code == 503
    assert response.json() == {"detail": "The database is temporarily unavailable. Please try again in a minute."}
