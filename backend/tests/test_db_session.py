"""Tests for the request-scoped database session dependency."""

from unittest.mock import MagicMock, patch

import pytest

from app.db.session import get_db


def test_the_session_is_closed_after_a_successful_request() -> None:
    """The session is returned to the pool without a rollback."""
    session = MagicMock()

    with patch("app.db.session.SessionLocal", return_value=session):
        generator = get_db()
        assert next(generator) is session
        with pytest.raises(StopIteration):
            next(generator)

    session.rollback.assert_not_called()
    session.close.assert_called_once()


def test_a_failed_request_rolls_the_transaction_back() -> None:
    """An exception raised by the handler never leaves a dirty session behind."""
    session = MagicMock()

    with patch("app.db.session.SessionLocal", return_value=session):
        generator = get_db()
        next(generator)
        with pytest.raises(RuntimeError):
            generator.throw(RuntimeError("boom"))

    session.rollback.assert_called_once()
    session.close.assert_called_once()
