"""Tests for protected admin review management endpoints."""

import asyncio
import csv
import io

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.errors import AiProviderError
from app.ai.response_generator import IAiResponseGenerator
from app.ai.stub_analyzer import StubAiReviewAnalyzer
from app.ai.stub_response_generator import StubAiResponseGenerator
from app.api.deps import get_review_ai_service
from app.core.rate_limiter import DRAFT_REGENERATION_WINDOW_SECONDS, MAX_DRAFT_REGENERATIONS
from app.models.review import Review
from app.schemas.ai import AiResponseGenerationRequest, AiResponseGenerationResult
from app.services.review_ai_service import ReviewAiService
from main import app
from tests.doubles import FAKE_DRAFT, FakeChatServer


def test_get_all_reviews_unauthorized(client: TestClient) -> None:
    """Test getting all reviews without authentication."""
    response = client.get("/api/admin/reviews")

    assert response.status_code == 401


def test_get_all_reviews_authorized(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test getting all reviews with authentication."""
    response = client.get("/api/admin/reviews", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    # Backend now returns PaginatedResponse: {items, total, page, page_size, total_pages}
    assert isinstance(data, dict)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data


def test_get_all_reviews_with_filters(client: TestClient, auth_headers: dict[str, str], db_session: Session) -> None:
    """The status and priority filters return only the matching reviews."""
    review = db_session.get(Review, _create_review(client))
    assert review is not None
    review.priority = "High"
    db_session.commit()

    def total(query: str) -> int:
        response = client.get(f"/api/admin/reviews?{query}", headers=auth_headers)
        assert response.status_code == 200
        return int(response.json()["total"])

    assert total("status=Pending") == 1
    assert total("status=Completed") == 0
    assert total("priority=High") == 1
    assert total("priority=Low") == 0
    assert total("status=Pending&priority=High") == 1


def test_get_statistics_unauthorized(client: TestClient) -> None:
    """Test getting statistics without authentication."""
    response = client.get("/api/admin/reviews/statistics")

    assert response.status_code == 401


def test_get_statistics_authorized(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test getting statistics with authentication."""
    # The public form sends no rating: it is set by the AI analysis later.
    client.post(
        "/api/reviews",
        json={"author_name": "Test User", "email": "test@example.com", "text": "This is a test review."},
    )

    response = client.get("/api/admin/reviews/statistics", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "rating_1" in data
    assert "rating_2" in data
    assert "rating_3" in data
    assert "rating_4" in data
    assert "rating_5" in data
    assert "total" in data


def test_get_statistics_reports_the_aggregates(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    """The total counts every review; the average covers the rated ones only."""
    for rating in (5, 3):
        review = db_session.get(Review, _create_review(client))
        assert review is not None
        review.rating = rating
        db_session.commit()
    _create_review(client)  # Not analysed yet, so it has no rating.

    response = client.get("/api/admin/reviews/statistics", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert [data[f"rating_{stars}"] for stars in range(1, 6)] == [0, 0, 1, 0, 1]
    assert data["total"] == 3
    assert data["avg_rating"] == 4.0


def _analyze(review_id: str, db_session: Session) -> None:
    """Run the AI analysis of a review with the offline stub providers.

    This is the same work the background worker does after a review was
    submitted through the public form.

    Args:
        review_id: Unique review UUID to analyse.
        db_session: The session bound to the temporary test database.
    """
    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )
    asyncio.run(service.analyze(review_id))


def test_get_statistics_counts_ratings(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Analysed reviews are counted per star rating."""
    create_response = client.post(
        "/api/reviews",
        json={
            "author_name": "Test User",
            "email": "stats@example.com",
            "text": "My payment was charged twice, I need a refund.",
        },
    )
    review_id = create_response.json()["id"]
    _analyze(review_id, db_session)

    response = client.get("/api/admin/reviews/statistics", headers=auth_headers)
    data = response.json()

    assert data["rating_1"] == 1
    assert data["total"] == 1
    assert data["avg_rating"] == 1.0


def test_get_all_reviews_accepts_empty_filters(client: TestClient, auth_headers: dict[str, str]) -> None:
    """An empty "All ..." filter must not produce a validation error.

    The admin panel sends the value of the selected dropdown option. The
    "All ..." options carry an empty value, so the endpoint has to treat
    an empty string as "no filter" instead of rejecting it with HTTP 422.
    """
    client.post(
        "/api/reviews",
        json={
            "author_name": "Test User",
            "email": "empty-filter@example.com",
            "text": "This is a test review.",
        },
    )

    response = client.get(
        "/api/admin/reviews?status=&rating=&priority=&sort_by=&descending=&page=1&page_size=10",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_get_all_reviews_rejects_an_unknown_filter_value(client: TestClient, auth_headers: dict[str, str]) -> None:
    """A filter value that is neither empty nor a known enum is rejected."""
    response = client.get(
        "/api/admin/reviews?status=All+Statuses",
        headers=auth_headers,
    )

    assert response.status_code == 422


def _parse_csv(body: str) -> list[list[str]]:
    """Parse a CSV document into rows.

    Args:
        body: The raw CSV payload, possibly starting with a UTF-8 BOM.

    Returns:
        The parsed rows, header row included.
    """
    return list(csv.reader(io.StringIO(body.lstrip("﻿"))))


def test_export_reviews_unauthorized(client: TestClient) -> None:
    """Test exporting the reviews without authentication."""
    response = client.get("/api/admin/reviews/export?format=csv")

    assert response.status_code == 401


def test_export_reviews_authorized(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The export endpoint returns a downloadable CSV file."""
    client.post(
        "/api/reviews",
        json={
            "author_name": "Test User",
            "email": "export@example.com",
            "text": "This is a test review.",
        },
    )

    response = client.get("/api/admin/reviews/export?format=csv", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]

    rows = _parse_csv(response.text)
    assert rows[0][0] == "id"
    assert "email" in rows[0]
    assert len(rows) == 2  # the header row plus the one created review


def test_export_reviews_respects_the_filters(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The exported file contains exactly the filtered reviews."""
    client.post(
        "/api/reviews",
        json={
            "author_name": "Test User",
            "email": "export-filter@example.com",
            "text": "This is a test review.",
        },
    )

    response = client.get(
        "/api/admin/reviews/export?format=csv&status=Completed",
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = _parse_csv(response.text)
    # Only the header row — the review is still pending
    assert len(rows) == 1


def test_export_reviews_rejects_an_unknown_format(client: TestClient, auth_headers: dict[str, str]) -> None:
    """An unsupported export format is rejected."""
    response = client.get("/api/admin/reviews/export?format=xlsx", headers=auth_headers)

    assert response.status_code == 422


def test_export_reviews_is_not_shadowed_by_the_id_route(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The ``/export`` path is not treated as a review id."""
    response = client.get("/api/admin/reviews/export", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_update_review_status_unauthorized(client: TestClient) -> None:
    """Test updating review status without authentication."""
    response = client.patch("/api/admin/reviews/test-id/status")

    assert response.status_code == 401


def test_update_review_status_authorized(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test updating review status with authentication."""
    # First create a review
    create_response = client.post(
        "/api/reviews", json={"author_name": "Test User", "email": "test@example.com", "text": "This is a test review."}
    )
    review_id = create_response.json()["id"]

    # Update status
    response = client.patch(
        f"/api/admin/reviews/{review_id}/status", json={"analysis_status": "Processing"}, headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_status"] == "Processing"


def test_get_review_by_id_includes_email(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test that admin endpoints return author email."""
    create_response = client.post(
        "/api/reviews",
        json={"author_name": "Test User", "email": "admin-check@example.com", "text": "Checking email visibility."},
    )
    review_id = create_response.json()["id"]

    response = client.get(f"/api/admin/reviews/{review_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin-check@example.com"


def test_get_missing_review_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    """An unknown review id is a 404, never a 500."""
    response = client.get("/api/admin/reviews/does-not-exist", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"


def test_priority_sort_orders_by_urgency(client: TestClient, auth_headers: dict[str, str], db_session: Session) -> None:
    """Sorting by priority ranks High above Medium above Low.

    The column stores the priority as a string, so an alphabetical sort
    would put "High" first and "Medium" last.  The list has to be ordered
    by urgency instead.
    """
    priorities = ["Medium", "Low", "High"]
    for index, priority in enumerate(priorities):
        response = client.post(
            "/api/reviews",
            json={
                "author_name": "Test User",
                "email": f"sort-{index}@example.com",
                "text": "A review used to check the priority sorting.",
            },
        )
        review_id = response.json()["id"]
        review = db_session.get(Review, review_id)
        assert review is not None
        review.priority = priority
        db_session.commit()

    response = client.get(
        "/api/admin/reviews?sort_by=priority&descending=false&page_size=10",
        headers=auth_headers,
    )
    assert response.status_code == 200
    ascending = [item["priority"] for item in response.json()["items"]]

    response = client.get(
        "/api/admin/reviews?sort_by=priority&descending=true&page_size=10",
        headers=auth_headers,
    )
    assert response.status_code == 200
    descending = [item["priority"] for item in response.json()["items"]]

    assert ascending == ["Low", "Medium", "High"]
    assert descending == ["High", "Medium", "Low"]


def test_paging_through_equal_ratings_shows_every_review_once(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    """Ties in the sort key are broken, so pages never repeat or skip a review."""
    created: list[str] = []
    for index in range(6):
        response = client.post(
            "/api/reviews",
            json={
                "author_name": "Tie User",
                "email": f"tie-{index}@example.com",
                "text": "A review that shares its rating with the others.",
            },
        )
        review = db_session.get(Review, response.json()["id"])
        assert review is not None
        review.rating = 4
        db_session.commit()
        created.append(review.id)

    seen: list[str] = []
    for page in range(1, 4):
        response = client.get(
            f"/api/admin/reviews?sort_by=rating&page={page}&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        seen.extend(item["id"] for item in response.json()["items"])

    assert sorted(seen) == sorted(created)


def test_update_missing_review_status_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Updating an unknown review id is a 404, never a 500."""
    response = client.patch(
        "/api/admin/reviews/does-not-exist/status",
        json={"analysis_status": "Processing"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"


class _FailingResponseGenerator(IAiResponseGenerator):
    """Response generator that simulates an unreachable AI provider."""

    async def generate(self, request: AiResponseGenerationRequest) -> AiResponseGenerationResult:
        """Raise the error httpx reports for a refused connection."""
        raise httpx.ConnectError("connection refused")


def _create_review(client: TestClient) -> str:
    """Submit a review through the public API and return its id."""
    response = client.post(
        "/api/reviews",
        json={
            "author_name": "Test User",
            "email": "draft@example.com",
            "text": "The app crashes when I open the settings page.",
        },
    )
    return str(response.json()["id"])


def test_regenerate_draft_unauthorized(client: TestClient) -> None:
    """Regenerating a draft requires an admin session."""
    response = client.post("/api/admin/reviews/any-id/regenerate-draft")

    assert response.status_code == 401


def test_regenerate_draft_stores_a_new_draft(client: TestClient, auth_headers: dict[str, str]) -> None:
    """A successful regeneration returns the review with its draft filled in."""
    review_id = _create_review(client)

    response = client.post(f"/api/admin/reviews/{review_id}/regenerate-draft", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == review_id
    assert data["ai_draft_response"]
    assert data["ai_draft_response_provider"]


def test_regenerating_again_still_reaches_the_provider(
    client: TestClient, auth_headers: dict[str, str], fake_groq: FakeChatServer
) -> None:
    """Every regeneration gets a draft, not only the first one.

    Each request runs the provider in its own event loop, and the provider
    is reached over a real socket, as in production.
    """
    review_id = _create_review(client)
    url = f"/api/admin/reviews/{review_id}/regenerate-draft"

    responses = [client.post(url, headers=auth_headers) for _ in range(3)]

    assert [response.status_code for response in responses] == [200] * 3
    assert {response.json()["ai_draft_response"] for response in responses} == {FAKE_DRAFT}


def test_regenerate_draft_for_missing_review_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    """An unknown review id is a 404, never a 500."""
    response = client.post("/api/admin/reviews/does-not-exist/regenerate-draft", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"


def test_regenerate_draft_reports_a_provider_outage_as_502(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    """A failing AI provider is a readable 502, and the stored draft survives."""
    review_id = _create_review(client)
    review = db_session.get(Review, review_id)
    assert review is not None
    review.ai_draft_response = "Previous draft"
    db_session.commit()

    app.dependency_overrides[get_review_ai_service] = lambda: ReviewAiService(
        db_session, StubAiReviewAnalyzer(), _FailingResponseGenerator()
    )
    try:
        response = client.post(f"/api/admin/reviews/{review_id}/regenerate-draft", headers=auth_headers)
    finally:
        del app.dependency_overrides[get_review_ai_service]

    assert response.status_code == 502
    assert "AI provider is unavailable" in response.json()["detail"]
    db_session.refresh(review)
    assert review.ai_draft_response == "Previous draft"


def test_regenerating_too_often_is_refused(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The paid AI call is capped per client: the extra click gets a 429."""
    review_id = _create_review(client)
    url = f"/api/admin/reviews/{review_id}/regenerate-draft"

    for _ in range(MAX_DRAFT_REGENERATIONS):
        assert client.post(url, headers=auth_headers).status_code == 200

    response = client.post(url, headers=auth_headers)

    assert response.status_code == 429
    assert "Too many draft regenerations" in response.json()["detail"]
    assert response.headers["Retry-After"] == str(DRAFT_REGENERATION_WINDOW_SECONDS)


class _MalformedResponseGenerator(IAiResponseGenerator):
    """Response generator whose provider answered with an unusable payload."""

    async def generate(self, request: AiResponseGenerationRequest) -> AiResponseGenerationResult:
        """Raise the error the provider layer reports for a malformed answer."""
        raise AiProviderError("Groq returned an unexpected answer")


class _BuggyResponseGenerator(IAiResponseGenerator):
    """Response generator with a programming error."""

    async def generate(self, request: AiResponseGenerationRequest) -> AiResponseGenerationResult:
        """Fail the way a bug does, not the way a provider does."""
        raise TypeError("bug")


def test_a_malformed_provider_answer_is_a_502(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    """An unusable provider reply is reported like an outage."""
    review_id = _create_review(client)
    app.dependency_overrides[get_review_ai_service] = lambda: ReviewAiService(
        db_session, StubAiReviewAnalyzer(), _MalformedResponseGenerator()
    )
    try:
        response = client.post(f"/api/admin/reviews/{review_id}/regenerate-draft", headers=auth_headers)
    finally:
        del app.dependency_overrides[get_review_ai_service]

    assert response.status_code == 502


def test_a_bug_is_not_disguised_as_a_provider_outage(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    """A programming error surfaces as a server error, never as a 502."""
    review_id = _create_review(client)
    app.dependency_overrides[get_review_ai_service] = lambda: ReviewAiService(
        db_session, StubAiReviewAnalyzer(), _BuggyResponseGenerator()
    )
    try:
        with pytest.raises(TypeError):
            client.post(f"/api/admin/reviews/{review_id}/regenerate-draft", headers=auth_headers)
    finally:
        del app.dependency_overrides[get_review_ai_service]
