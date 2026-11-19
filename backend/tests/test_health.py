"""Tests for the liveness and readiness probes."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.health import ping_redis
from app.core.config import settings
from app.db.session import get_db
from main import app


def test_liveness_needs_no_dependency(client: TestClient) -> None:
    """The liveness probe answers without touching the database or Redis."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_reports_ready(client: TestClient) -> None:
    """With the database and Redis reachable the service is ready."""
    app.dependency_overrides[ping_redis] = lambda: True
    try:
        response = client.get("/health/ready")
    finally:
        del app.dependency_overrides[ping_redis]

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok", "redis": "ok"}


def test_readiness_fails_without_redis(client: TestClient) -> None:
    """A Redis outage makes the probe answer 503."""
    app.dependency_overrides[ping_redis] = lambda: False
    try:
        response = client.get("/health/ready")
    finally:
        del app.dependency_overrides[ping_redis]

    assert response.status_code == 503
    assert response.json()["redis"] == "unavailable"


def test_readiness_fails_without_the_database(client: TestClient) -> None:
    """A database outage makes the probe answer 503."""
    broken = MagicMock()
    broken.execute.side_effect = OperationalError("SELECT 1", {}, Exception("down"))
    app.dependency_overrides[ping_redis] = lambda: True
    app.dependency_overrides[get_db] = lambda: broken
    try:
        response = client.get("/health/ready")
    finally:
        del app.dependency_overrides[ping_redis]
        del app.dependency_overrides[get_db]

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable", "redis": "ok"}


def test_ping_redis_reports_an_unreachable_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unreachable Redis is a False, never an exception."""
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")

    assert ping_redis() is False
