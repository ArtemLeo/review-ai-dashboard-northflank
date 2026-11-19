"""Tests for the Redis denylist of signed-out sessions."""

import time

import pytest

from app.core.exceptions import AuthStoreUnavailableError
from app.core.session_store import SessionDenylist
from tests.doubles import FakeRedis


def test_a_revoked_token_is_reported() -> None:
    """A revoked id is listed; any other id is not."""
    denylist = SessionDenylist(client=FakeRedis())  # type: ignore[arg-type]

    denylist.revoke("abc", time.time() + 60)

    assert denylist.is_revoked("abc") is True
    assert denylist.is_revoked("other") is False


def test_an_already_expired_token_is_not_stored() -> None:
    """There is nothing to revoke once the token expired on its own."""
    fake = FakeRedis()
    denylist = SessionDenylist(client=fake)  # type: ignore[arg-type]

    denylist.revoke("abc", time.time() - 5)

    assert fake.values == {}


def test_a_redis_outage_fails_closed() -> None:
    """A Redis outage never lets a signed-out token back in."""
    fake = FakeRedis()
    fake.fail = True
    denylist = SessionDenylist(client=fake)  # type: ignore[arg-type]

    with pytest.raises(AuthStoreUnavailableError):
        denylist.revoke("abc", time.time() + 60)

    with pytest.raises(AuthStoreUnavailableError):
        denylist.is_revoked("abc")
