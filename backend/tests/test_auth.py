"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.passwords import hash_password
from app.core.rate_limiter import LOGIN_FAILURE_WINDOW_SECONDS, MAX_LOGIN_FAILURES, RateLimiter
from app.core.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    create_access_token,
)
from app.core.session_store import SessionDenylist


def _login(client: TestClient) -> None:
    """Sign in through the API; the client keeps the session and CSRF cookies."""
    response = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert response.status_code == 200


def _csrf_header(client: TestClient) -> dict[str, str]:
    """Repeat the CSRF cookie in the header, as the SPA does."""
    return {CSRF_HEADER_NAME: client.cookies[CSRF_COOKIE_NAME]}


def test_login_success(client: TestClient) -> None:
    """A successful login answers with the administrator and an httpOnly session cookie."""
    response = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )

    assert response.status_code == 200
    assert response.json() == {"email": settings.admin_email}
    assert "access_token" not in response.json()

    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()
    assert "path=/" in set_cookie.lower()
    # Development runs over plain HTTP, where a Secure cookie would be dropped.
    assert "secure" not in set_cookie.lower()


def test_session_lasts_thirty_minutes(client: TestClient) -> None:
    """The session and CSRF cookies both expire 30 minutes after sign-in."""
    response = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )

    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all("max-age=1800" in cookie.lower() for cookie in cookies)


def test_session_cookie_is_accepted_without_header(client: TestClient) -> None:
    """The browser's session cookie alone authorizes the admin API and /me."""
    client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )

    assert client.get("/api/auth/me").json() == {"email": settings.admin_email}
    assert client.get("/api/admin/reviews").status_code == 200


def test_bearer_header_remains_a_fallback(client: TestClient) -> None:
    """API clients that send the token in the Authorization header keep working."""
    token = create_access_token({"sub": settings.admin_email})

    response = client.get(
        "/api/admin/reviews",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_me_requires_a_session(client: TestClient) -> None:
    """Without a session cookie or header the current-session endpoint answers 401."""
    client.cookies.clear()

    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/admin/reviews").status_code == 401


def test_logout_expires_the_session_cookie(client: TestClient) -> None:
    """Logout answers 204 and tells the browser to drop the session cookie."""
    client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )

    response = client.post("/api/auth/logout", headers=_csrf_header(client))

    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in set_cookie
    assert "max-age=0" in set_cookie


def test_session_cookie_is_secure_only_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Secure flag follows the deployment environment."""
    monkeypatch.setattr(settings, "environment", "development")
    assert settings.session_cookie_secure is False

    monkeypatch.setattr(settings, "environment", "production")
    assert settings.session_cookie_secure is True


def test_login_invalid_credentials(client: TestClient) -> None:
    """Test login with invalid credentials."""
    response = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login or password. Please try again"


def test_login_missing_fields(client: TestClient) -> None:
    """Test login with missing required fields."""
    response = client.post("/api/auth/login", json={"email": "admin@example.com"})

    assert response.status_code == 422
    assert "Password is required" in response.json()["detail"]


def test_login_empty_fields(client: TestClient) -> None:
    """Empty fields are reported as missing, not as malformed ones."""
    response = client.post("/api/auth/login", json={"email": "", "password": ""})

    assert response.status_code == 422
    assert response.json()["detail"] == "Email is required. Password is required"


def test_repeated_failures_lock_the_client_out(client: TestClient) -> None:
    """Too many failed attempts make the API answer with HTTP 429."""
    payload = {"email": "wrong@example.com", "password": "wrong"}

    for _ in range(MAX_LOGIN_FAILURES):
        assert client.post("/api/auth/login", json=payload).status_code == 401

    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 429
    assert "Too many failed sign-in attempts" in response.json()["detail"]
    assert response.headers["Retry-After"] == str(LOGIN_FAILURE_WINDOW_SECONDS)


def test_successful_login_clears_the_failure_counter(client: TestClient) -> None:
    """A correct sign-in gives the client its budget back."""
    wrong = {"email": "wrong@example.com", "password": "wrong"}
    right = {"email": settings.admin_email, "password": settings.admin_password}

    for _ in range(MAX_LOGIN_FAILURES - 1):
        assert client.post("/api/auth/login", json=wrong).status_code == 401

    assert client.post("/api/auth/login", json=right).status_code == 200

    # The counter was reset, so the next failed attempt is a plain 401 again.
    assert client.post("/api/auth/login", json=wrong).status_code == 401


def test_a_locked_out_client_is_refused_even_with_the_right_password(client: TestClient) -> None:
    """A spent budget stops the guessing: no answer reveals a correct password."""
    wrong = {"email": "wrong@example.com", "password": "wrong"}
    right = {"email": settings.admin_email, "password": settings.admin_password}

    for _ in range(MAX_LOGIN_FAILURES):
        assert client.post("/api/auth/login", json=wrong).status_code == 401

    assert client.post("/api/auth/login", json=wrong).status_code == 429
    assert client.post("/api/auth/login", json=right).status_code == 429


def test_the_lockout_only_affects_the_guessing_client(client: TestClient) -> None:
    """The budget is per address, so the administrator elsewhere still gets in."""
    wrong = {"email": "wrong@example.com", "password": "wrong"}
    right = {"email": settings.admin_email, "password": settings.admin_password}
    attacker = {"X-Forwarded-For": "203.0.113.7"}
    admin = {"X-Forwarded-For": "198.51.100.20"}

    for _ in range(MAX_LOGIN_FAILURES + 1):
        client.post("/api/auth/login", json=wrong, headers=attacker)

    assert client.post("/api/auth/login", json=right, headers=attacker).status_code == 429
    assert client.post("/api/auth/login", json=right, headers=admin).status_code == 200


def test_login_with_non_ascii_email_returns_401(client: TestClient) -> None:
    """A non-ASCII email must be rejected with 401, never 500."""
    response = client.post(
        "/api/auth/login",
        json={"email": "адмін@example.com", "password": settings.admin_password},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login or password. Please try again"


def test_login_with_a_password_hash(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """With ADMIN_PASSWORD_HASH set, the hash decides and the plain value is ignored."""
    monkeypatch.setattr(settings, "admin_password_hash", hash_password("hashed-secret-1"))

    accepted = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": "hashed-secret-1"},
    )
    refused = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )

    assert accepted.status_code == 200
    assert refused.status_code == 401


def test_a_signed_out_token_is_refused_even_if_replayed(client: TestClient) -> None:
    """Logout revokes the token itself, not only the browser cookie."""
    _login(client)
    token = client.cookies[SESSION_COOKIE_NAME]
    assert client.post("/api/auth/logout", headers=_csrf_header(client)).status_code == 204

    client.cookies.clear()
    replay = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert replay.status_code == 401


def test_a_token_without_jti_is_refused(client: TestClient) -> None:
    """Every session must be revocable, so a token without an id is invalid."""
    import jwt

    token = jwt.encode(
        {"sub": settings.admin_email, "iss": settings.jwt_issuer, "aud": settings.jwt_audience, "exp": 4_102_444_800},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_login_issues_a_readable_csrf_cookie(client: TestClient) -> None:
    """The CSRF cookie is not httpOnly, so the SPA can copy it into the header."""
    response = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )

    csrf_cookie = [
        value for value in response.headers.get_list("set-cookie") if value.startswith(f"{CSRF_COOKIE_NAME}=")
    ]
    assert len(csrf_cookie) == 1
    assert "httponly" not in csrf_cookie[0].lower()
    assert "samesite=lax" in csrf_cookie[0].lower()


def test_unsafe_cookie_request_without_csrf_header_is_forbidden(client: TestClient) -> None:
    """A cookie-authenticated PATCH without the header is refused with 403."""
    _login(client)

    missing = client.patch("/api/admin/reviews/any-id/status", json={"analysis_status": "Processing"})
    wrong = client.patch(
        "/api/admin/reviews/any-id/status",
        json={"analysis_status": "Processing"},
        headers={CSRF_HEADER_NAME: "forged"},
    )
    right = client.patch(
        "/api/admin/reviews/any-id/status",
        json={"analysis_status": "Processing"},
        headers=_csrf_header(client),
    )

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert right.status_code == 404  # passed the check; the review does not exist


def test_safe_requests_and_bearer_clients_skip_the_csrf_check(client: TestClient) -> None:
    """GET needs no header, and a Bearer token is never attached by a browser."""
    _login(client)
    assert client.get("/api/admin/reviews").status_code == 200

    token = client.cookies[SESSION_COOKIE_NAME]
    client.cookies.clear()
    response = client.patch(
        "/api/admin/reviews/any-id/status",
        json={"analysis_status": "Processing"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_me_reissues_a_missing_csrf_cookie(client: TestClient) -> None:
    """A session that lost its CSRF cookie gets a new one on start-up."""
    _login(client)
    del client.cookies[CSRF_COOKIE_NAME]

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert CSRF_COOKIE_NAME in response.cookies


def test_logout_without_csrf_clears_cookies_but_keeps_the_token_valid(
    client: TestClient,
) -> None:
    """The user can always sign out; only a verified request revokes the token."""
    _login(client)
    token = client.cookies[SESSION_COOKIE_NAME]

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    client.cookies.clear()
    still_valid = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert still_valid.status_code == 200


def test_a_redis_outage_during_sign_in_is_an_honest_503(client: TestClient, login_limiter: RateLimiter) -> None:
    """Sign-in fails closed, but says so instead of claiming a lockout."""
    login_limiter.client.fail = True  # type: ignore[attr-defined]
    right = {"email": settings.admin_email, "password": settings.admin_password}

    response = client.post("/api/auth/login", json=right)

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_a_redis_outage_on_an_admin_request_is_an_honest_503(
    client: TestClient, auth_headers: dict[str, str], session_denylist: SessionDenylist
) -> None:
    """A session check that cannot reach Redis says so instead of "expired"."""
    session_denylist.client.fail = True  # type: ignore[attr-defined]

    response = client.get("/api/admin/reviews", headers=auth_headers)

    assert response.status_code == 503


def test_logout_can_be_retried_after_a_redis_outage(
    client: TestClient,
    session_denylist: SessionDenylist,
) -> None:
    """A failed revocation retains the session until a retry can revoke it."""
    _login(client)
    token = client.cookies[SESSION_COOKIE_NAME]
    csrf = _csrf_header(client)
    session_denylist.client.fail = True  # type: ignore[attr-defined]

    failed = client.post("/api/auth/logout", headers=csrf)

    assert failed.status_code == 503
    assert "temporarily unavailable" in failed.json()["detail"]
    assert "set-cookie" not in failed.headers
    assert client.cookies[SESSION_COOKIE_NAME] == token
    assert client.cookies[CSRF_COOKIE_NAME] == csrf[CSRF_HEADER_NAME]

    session_denylist.client.fail = False  # type: ignore[attr-defined]
    assert client.post("/api/auth/logout", headers=csrf).status_code == 204
    client.cookies.clear()
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
