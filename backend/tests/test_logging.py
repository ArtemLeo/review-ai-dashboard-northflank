"""Tests for the per-request access log emitted by the ASGI middleware."""

import logging
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def captured_logs() -> Generator[list[tuple[str, str, str]], None, None]:
    """Collect every record written to the root logger during a test.

    Yields:
        A list of ``(logger_name, level_name, message)`` tuples.  The list is
        filled in place while the test runs.
    """
    records: list[tuple[str, str, str]] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append((record.name, record.levelname, record.getMessage()))

    root = logging.getLogger()
    handler = _Collector()
    previous_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        yield records
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)


def _access_lines(records: list[tuple[str, str, str]]) -> list[str]:
    """Return only the application access-log messages.

    Args:
        records: The collected log records.

    Returns:
        The messages that look like an access-log line.
    """
    return [message for _name, _level, message in records if "->" in message]


def test_successful_request_is_logged(
    client: TestClient,
    captured_logs: list[tuple[str, str, str]],
) -> None:
    """A request that succeeds produces an access-log line with its status."""
    client.get("/openapi.json")

    messages = _access_lines(captured_logs)

    assert any("GET /openapi.json -> 200" in message for message in messages)


def test_validation_error_request_is_logged(
    client: TestClient,
    captured_logs: list[tuple[str, str, str]],
) -> None:
    """A rejected payload is logged as a normal request, not as a failure."""
    client.post("/api/reviews", json={"text": "x"})

    messages = _access_lines(captured_logs)

    assert any("POST /api/reviews -> 422" in message for message in messages)


def test_unhandled_exception_is_logged(
    captured_logs: list[tuple[str, str, str]],
) -> None:
    """A handler that raises still leaves an access-log line behind.

    The middleware must record the failure before the exception propagates,
    otherwise a 500 storm leaves the operators with no access log at all.
    """
    path = "/__test_boom__"

    @app.get(path)
    def _boom() -> dict[str, str]:
        raise RuntimeError("boom")

    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get(path)
    finally:
        app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != path]

    assert response.status_code == 500
    messages = _access_lines(captured_logs)
    assert any(f"GET {path} -> 500" in message for message in messages)
