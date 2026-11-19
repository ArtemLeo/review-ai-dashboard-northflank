"""Tests for the Redis sliding-window rate limiter."""

from unittest.mock import patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.exceptions import AuthStoreUnavailableError
from app.core.rate_limiter import (
    SUBMISSION_WINDOW_SECONDS,
    RateLimiter,
    get_client_ip,
    rate_limit_review_submission,
)
from main import app
from tests.doubles import FakeRedis


def _make_request(
    headers: dict[str, str] | None = None,
    client: tuple[str, int] | None = ("172.18.0.2", 54321),
) -> Request:
    """Build a Starlette request with the given headers and peer address.

    Args:
        headers: The headers of the request.
        client: The address of the peer the request came from.

    Returns:
        A request object usable by the rate limiter.
    """
    raw_headers = [(name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw_headers,
            "client": client,
        }
    )


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Provide an in-memory Redis double."""
    return FakeRedis()


def test_allows_requests_below_the_limit(fake_redis: FakeRedis) -> None:
    """Requests under the limit are allowed."""
    limiter = RateLimiter(max_requests=3, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    assert limiter.is_allowed("10.0.0.1") is True
    assert limiter.is_allowed("10.0.0.1") is True
    assert limiter.is_allowed("10.0.0.1") is True


def test_blocks_requests_above_the_limit(fake_redis: FakeRedis) -> None:
    """The request that exceeds the limit is rejected."""
    limiter = RateLimiter(max_requests=3, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    for _ in range(3):
        assert limiter.is_allowed("203.0.113.5") is True

    assert limiter.is_allowed("203.0.113.5") is False


def test_clients_have_separate_budgets(fake_redis: FakeRedis) -> None:
    """One client exhausting its budget does not affect another client."""
    limiter = RateLimiter(max_requests=2, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    assert limiter.is_allowed("10.0.0.1") is True
    assert limiter.is_allowed("10.0.0.1") is True
    assert limiter.is_allowed("10.0.0.1") is False

    assert limiter.is_allowed("10.0.0.2") is True


def test_fails_open_when_redis_is_unavailable(fake_redis: FakeRedis) -> None:
    """A Redis outage must not reject submissions."""
    limiter = RateLimiter(max_requests=1, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]
    assert limiter.is_allowed("192.168.1.1") is True
    fake_redis.fail = True

    # Over the limit, yet allowed: the outage is not a reason to refuse.
    assert limiter.is_allowed("192.168.1.1") is True


def test_expired_requests_leave_the_window(fake_redis: FakeRedis) -> None:
    """Requests older than the window no longer count."""
    limiter = RateLimiter(max_requests=2, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    # Pretend the client already used its budget two minutes ago.
    fake_redis.store["ratelimit:reviews:10.0.0.1"] = {"first": 1.0, "second": 2.0}

    assert limiter.is_allowed("10.0.0.1") is True


def test_default_policy_allows_ten_requests_per_minute(
    fake_redis: FakeRedis,
) -> None:
    """The production policy allows exactly ten requests per window."""
    limiter = RateLimiter(client=fake_redis)  # type: ignore[arg-type]

    assert limiter.max_requests == 10
    assert limiter.window_seconds == 60

    for _ in range(10):
        assert limiter.is_allowed("10.0.0.1") is True

    assert limiter.is_allowed("10.0.0.1") is False


def test_registered_attempts_consume_the_budget(fake_redis: FakeRedis) -> None:
    """Attempts within the limit pass; the one that exceeds it is refused."""
    limiter = RateLimiter(max_requests=2, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    assert limiter.register_attempt("198.51.100.7") is True
    assert limiter.register_attempt("198.51.100.7") is True
    assert limiter.register_attempt("198.51.100.7") is False


def test_refused_attempts_do_not_prolong_the_lockout(fake_redis: FakeRedis) -> None:
    """A client knocking while locked out leaves only the allowed attempts in the window."""
    limiter = RateLimiter(max_requests=2, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    limiter.register_attempt("198.51.100.7")
    limiter.register_attempt("198.51.100.7")
    for _ in range(5):
        assert limiter.register_attempt("198.51.100.7") is False

    assert len(fake_redis.store["ratelimit:reviews:198.51.100.7"]) == 2


def test_resetting_gives_the_full_budget_back(fake_redis: FakeRedis) -> None:
    """A successful sign-in wipes the recorded attempts."""
    limiter = RateLimiter(max_requests=1, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    limiter.register_attempt("198.51.100.7")
    assert limiter.register_attempt("198.51.100.7") is False

    limiter.reset("198.51.100.7")
    assert limiter.register_attempt("198.51.100.7") is True


def test_failure_counter_fails_closed_when_redis_is_unavailable(
    fake_redis: FakeRedis,
) -> None:
    """A Redis outage must not open an unlimited password-guessing window."""
    limiter = RateLimiter(
        max_requests=5,
        window_seconds=60,
        client=fake_redis,  # type: ignore[arg-type]
        fail_closed=True,
    )
    fake_redis.fail = True

    with pytest.raises(AuthStoreUnavailableError):
        limiter.register_attempt("198.51.100.7")


def test_the_last_forwarded_entry_is_the_client_address() -> None:
    """Only the address appended by the proxy is trusted.

    The platform's load balancer appends the real client to the header, so
    the entries in front of it are supplied by the client itself.  Trusting
    them would let every request claim a fresh budget.
    """
    request = _make_request({"X-Forwarded-For": "9.9.9.9, 203.0.113.5"})

    assert get_client_ip(request) == "203.0.113.5"


def test_a_single_forwarded_entry_is_the_client_address() -> None:
    """The header of a proxy that overwrites it holds one address."""
    request = _make_request({"X-Forwarded-For": "203.0.113.5"})

    assert get_client_ip(request) == "203.0.113.5"


def test_the_real_ip_header_is_used_without_a_forwarded_header() -> None:
    """The proxy also reports the client in ``X-Real-IP``."""
    request = _make_request({"X-Real-IP": "203.0.113.5"})

    assert get_client_ip(request) == "203.0.113.5"


def test_the_peer_address_is_used_without_any_proxy_header() -> None:
    """A request without proxy headers is attributed to its peer."""
    request = _make_request(client=("172.18.0.2", 54321))

    assert get_client_ip(request) == "172.18.0.2"


def test_endpoint_returns_429_after_the_limit(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    """The submission endpoint rejects the client once the limit is reached.

    The shared ``client`` fixture replaces the rate limiter with a no-op, so
    the dependency is overridden here with a thin wrapper around the real
    production dependency.  Only the limiter's storage is swapped — the
    in-memory Redis double — so the whole production code path (client IP
    resolution, sliding window, HTTP 429) is exercised.
    """
    limiter = RateLimiter(max_requests=2, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]

    def limited_dependency(request: Request) -> None:
        """Run the production dependency against the in-memory limiter."""
        rate_limit_review_submission(request)

    app.dependency_overrides[rate_limit_review_submission] = limited_dependency

    with patch("app.core.rate_limiter._review_submission_limiter", limiter):
        payload = {
            "author_name": "Test User",
            "email": "test@example.com",
            "text": "This is a test review.",
        }

        assert client.post("/api/reviews", json=payload).status_code == 202
        assert client.post("/api/reviews", json=payload).status_code == 202

        response = client.post("/api/reviews", json=payload)
        assert response.status_code == 429
        assert "Too many requests" in response.json()["detail"]
        assert response.headers["Retry-After"] == str(SUBMISSION_WINDOW_SECONDS)


def test_rejected_requests_do_not_extend_the_window(fake_redis: FakeRedis) -> None:
    """A client that keeps retrying regains access once its window expires."""
    limiter = RateLimiter(max_requests=1, window_seconds=60, client=fake_redis)  # type: ignore[arg-type]
    key = "ratelimit:reviews:10.0.0.9"

    assert limiter.is_allowed("10.0.0.9") is True
    for _ in range(5):
        assert limiter.is_allowed("10.0.0.9") is False

    assert len(fake_redis.store[key]) == 1
