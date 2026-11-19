"""Tests for the UTC time helpers."""

from datetime import UTC, datetime, timedelta

from app.core.time import utcnow


def test_utcnow_is_naive_and_close_to_the_real_utc_time() -> None:
    """The helper returns a naive datetime that is expressed in UTC."""
    value = utcnow()

    assert value.tzinfo is None
    assert abs(value - datetime.now(UTC).replace(tzinfo=None)) < timedelta(seconds=5)
