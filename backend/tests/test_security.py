"""Tests for JWT token creation, verification and the authorization guard."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, decode_admin_token


def test_valid_token_is_accepted() -> None:
    """A freshly minted token passes verification and yields the subject."""
    email = settings.admin_email
    token = create_access_token({"sub": email})

    assert decode_admin_token(token) == email


def test_token_carries_expected_claims() -> None:
    """The minted token carries the subject, issuer, audience and expiry."""
    token = create_access_token({"sub": "admin@example.com"})

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )

    assert payload["sub"] == "admin@example.com"
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience
    assert "exp" in payload


def test_expired_token_is_rejected() -> None:
    """An expired token is refused by the verifier."""
    expired = datetime.now(UTC) - timedelta(minutes=1)
    token = jwt.encode(
        {
            "sub": "admin@example.com",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": expired,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc:
        decode_admin_token(token)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Your session has expired. Please sign in again"


def test_forged_token_is_rejected() -> None:
    """A token signed with the wrong secret is refused by the verifier."""
    token = jwt.encode(
        {
            "sub": "admin@example.com",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "a-wrong-signing-secret-of-sufficient-length",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc:
        decode_admin_token(token)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Your session has expired. Please sign in again"


def test_token_with_wrong_issuer_is_rejected() -> None:
    """A token minted for another issuer is refused."""
    token = jwt.encode(
        {
            "sub": "admin@example.com",
            "iss": "some-other-service",
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc:
        decode_admin_token(token)

    assert exc.value.status_code == 401


def test_token_without_subject_is_rejected() -> None:
    """A token without a ``sub`` claim is refused."""
    token = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc:
        decode_admin_token(token)

    assert exc.value.status_code == 401


def test_token_with_another_subject_is_rejected() -> None:
    """A correctly signed token for a different subject is refused."""
    token = jwt.encode(
        {
            "sub": "somebody-else@example.com",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc:
        decode_admin_token(token)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Your session has expired. Please sign in again"


def test_protected_endpoint_rejects_a_token_of_another_subject(
    client: TestClient,
) -> None:
    """The admin API refuses a token that was not issued for this panel."""
    token = jwt.encode(
        {
            "sub": "somebody-else@example.com",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/admin/reviews",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_protected_endpoint_rejects_forged_token(
    client: TestClient,
) -> None:
    """The admin API refuses a request carrying a forged token."""
    token = jwt.encode(
        {
            "sub": "admin@example.com",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "a-wrong-signing-secret-of-sufficient-length",
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/admin/reviews",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_protected_endpoint_rejects_expired_token(client: TestClient) -> None:
    """The admin API refuses a request carrying an expired token."""
    token = jwt.encode(
        {
            "sub": "admin@example.com",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/admin/reviews",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_protected_endpoint_rejects_missing_token(client: TestClient) -> None:
    """The admin API refuses a request without any credentials."""
    response = client.get("/api/admin/reviews")

    assert response.status_code == 401
