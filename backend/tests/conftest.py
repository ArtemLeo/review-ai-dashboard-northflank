"""Pytest configuration and fixtures for Review AI Dashboard API tests.

The test suite is fully offline: the AI provider is forced to the stub
implementation, or (``fake_groq``) pointed at a chat server on localhost, so
no test ever performs an external API call.
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai.groq_analyzer import GroqReviewAnalyzer
from app.ai.groq_response_generator import GroqResponseGenerator
from app.core import session_store
from app.core.config import settings
from app.core.rate_limiter import (
    DRAFT_REGENERATION_WINDOW_SECONDS,
    LOGIN_FAILURE_WINDOW_SECONDS,
    MAX_DRAFT_REGENERATIONS,
    MAX_LOGIN_FAILURES,
    RateLimiter,
    get_draft_regeneration_limiter,
    get_login_failure_limiter,
    rate_limit_review_submission,
)
from app.core.security import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from app.core.session_store import SessionDenylist
from app.db.base_class import Base
from app.db.session import get_db
from main import app
from tests.doubles import FakeChatServer, FakeRedis


@pytest.fixture
def db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    """Create a temporary file-backed SQLite database for a single test.

    This is used only for test isolation — the production setup uses
    PostgreSQL via the ``DATABASE_URL`` environment variable.  The SQLite
    path is temporary and lives only in the function scope of each test.
    """
    engine: Engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Create a session bound to the temporary test database.

    Args:
        db_engine: The temporary database engine.

    Yields:
        An open SQLAlchemy Session.
    """
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session: Session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def stub_ai_provider() -> Generator[None, None, None]:
    """Force the offline stub AI provider for the duration of a test.

    Yields:
        ``None`` while the stub provider is active.
    """
    original_provider: str = settings.ai_provider
    settings.ai_provider = "stub"
    try:
        yield
    finally:
        settings.ai_provider = original_provider


@pytest.fixture
def fake_groq(monkeypatch: pytest.MonkeyPatch) -> Generator[FakeChatServer, None, None]:
    """Switch the factory to the Groq provider, pointed at a local chat server.

    Unlike the stub, the provider then makes real HTTP requests over a local
    socket, so the test covers the network path of the worker and of the
    regenerate-draft endpoint.  Nothing leaves the machine.

    Yields:
        The running chat server.
    """
    server = FakeChatServer()
    monkeypatch.setattr(settings, "ai_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(GroqReviewAnalyzer, "ENDPOINT", server.endpoint)
    monkeypatch.setattr(GroqResponseGenerator, "ENDPOINT", server.endpoint)
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def login_limiter() -> RateLimiter:
    """Provide the sign-in failure counter backed by an in-memory store.

    The production limiter talks to Redis, which is not available in the
    test environment.  The in-memory double keeps the real policy — five
    failed attempts per five minutes — so the lockout is exercised for real.

    Returns:
        A rate limiter instance using the production login policy.
    """
    return RateLimiter(
        max_requests=MAX_LOGIN_FAILURES,
        window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
        client=FakeRedis(),  # type: ignore[arg-type]
        fail_closed=True,
    )


@pytest.fixture
def regeneration_limiter() -> RateLimiter:
    """Provide the draft regeneration limiter backed by an in-memory store.

    Returns:
        A rate limiter instance using the production regeneration policy.
    """
    return RateLimiter(
        max_requests=MAX_DRAFT_REGENERATIONS,
        window_seconds=DRAFT_REGENERATION_WINDOW_SECONDS,
        client=FakeRedis(),  # type: ignore[arg-type]
    )


@pytest.fixture
def client(
    db_session: Session,
    login_limiter: RateLimiter,
    regeneration_limiter: RateLimiter,
) -> Generator[TestClient, None, None]:
    """Create a test client with a database session override.

    The review submission rate limit is disabled for tests, so each test
    function runs in complete isolation without accumulating request counts
    from previous test functions.  The sign-in failure counter keeps its
    real policy, but is backed by an in-memory store.

    Args:
        db_session: The session bound to the temporary test database.
        login_limiter: The sign-in failure counter used by the API.
        regeneration_limiter: The draft regeneration limiter used by the API.

    Yields:
        A configured ``TestClient`` instance.
    """

    def override_get_db() -> Generator[Session, None, None]:
        """Yield the shared test session instead of a production one."""
        yield db_session

    def override_rate_limit() -> None:
        """No-op override: bypasses rate limiting during tests."""
        return

    def override_login_limiter() -> RateLimiter:
        """Return the in-memory sign-in failure counter."""
        return login_limiter

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[rate_limit_review_submission] = override_rate_limit
    app.dependency_overrides[get_login_failure_limiter] = override_login_limiter
    app.dependency_overrides[get_draft_regeneration_limiter] = lambda: regeneration_limiter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def session_denylist(monkeypatch: pytest.MonkeyPatch) -> SessionDenylist:
    """Keep the signed-out sessions in memory instead of Redis.

    Returns:
        The denylist the authentication code uses during the test.
    """
    denylist = SessionDenylist(client=FakeRedis())  # type: ignore[arg-type]
    monkeypatch.setattr(session_store, "_denylist", denylist)
    return denylist


@pytest.fixture(autouse=True)
def mock_celery_enqueue() -> Generator[patch, None, None]:
    """Keep the Celery broker out of the test suite.

    The review endpoint enqueues the background analysis; in the tests the
    task is never dispatched, so the broker is mocked out entirely.

    Yields:
        The active patcher object.
    """
    with patch("app.api.reviews.analyze_review_task.apply_async") as apply_async:
        yield apply_async


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Create authenticated headers for protected endpoints.

    Args:
        client: The test client used to perform the login request.

    Returns:
        The ``Cookie`` header carrying the session and the CSRF cookie, plus
        the CSRF header that has to repeat it.

    Raises:
        RuntimeError: If the login request does not succeed.
    """
    response = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to authenticate test user: {response.status_code} {response.text}")

    token: str = response.cookies[SESSION_COOKIE_NAME]
    csrf: str = response.cookies[CSRF_COOKIE_NAME]
    return {
        "Cookie": f"{SESSION_COOKIE_NAME}={token}; {CSRF_COOKIE_NAME}={csrf}",
        CSRF_HEADER_NAME: csrf,
    }
