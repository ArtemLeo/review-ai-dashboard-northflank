"""Redis-backed denylist of signed-out administrator sessions.

Access tokens are stateless JWTs, so signing out cannot "delete" one.
Instead the token's unique ``jti`` claim is stored in Redis until the token
would have expired anyway; a listed token is refused even though its
signature is still valid.

When Redis is unreachable the check fails **closed**: a signed-out token
must never work again just because Redis is down.  The outage is reported as
:class:`AuthStoreUnavailableError`, which the API turns into a 503.
"""

import time
from threading import Lock

import redis

from app.core.config import settings
from app.core.exceptions import AuthStoreUnavailableError
from app.core.logging_config import get_logger
from app.core.redis_client import create_redis_client

logger = get_logger(__name__)

#: Prefix of the Redis keys marking a revoked token.
_KEY_PREFIX = "session:revoked:"


class SessionDenylist:
    """Set of revoked token identifiers with automatic expiry.

    Args:
        redis_url: Redis connection URL. Defaults to the configured one.
        client: An existing Redis client, used as-is (keeps the store testable).
    """

    def __init__(
        self,
        redis_url: str | None = None,
        client: redis.Redis | None = None,
    ) -> None:
        """Initialise the store; the Redis client is created on first use."""
        self._redis_url: str = redis_url or settings.redis_url
        self._client: redis.Redis | None = client
        self._lock: Lock = Lock()

    @property
    def client(self) -> redis.Redis:
        """Return the lazily created Redis client."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = create_redis_client(self._redis_url)
        return self._client

    def revoke(self, jti: str, expires_at: float) -> None:
        """Mark a token as signed out until its own expiry.

        Args:
            jti: The token's unique identifier.
            expires_at: The token's ``exp`` claim as a Unix timestamp.

        Raises:
            AuthStoreUnavailableError: When Redis cannot store the revocation.
        """
        ttl = int(expires_at - time.time()) + 1
        if ttl <= 0:
            return
        try:
            self.client.set(f"{_KEY_PREFIX}{jti}", "1", ex=ttl)
        except redis.RedisError as exc:
            logger.warning("Could not revoke session %s: %s", jti, exc)
            raise AuthStoreUnavailableError from exc

    def is_revoked(self, jti: str) -> bool:
        """Return whether a token was signed out.

        Args:
            jti: The token's unique identifier.

        Returns:
            ``True`` for a revoked token.

        Raises:
            AuthStoreUnavailableError: When Redis is unreachable.  The check
                fails closed, so a signed-out token never works again just
                because Redis is down.
        """
        try:
            return bool(self.client.exists(f"{_KEY_PREFIX}{jti}"))
        except redis.RedisError as exc:
            logger.warning("Could not check session %s: %s", jti, exc)
            raise AuthStoreUnavailableError from exc


#: Module-level singleton used by the authentication code.
_denylist = SessionDenylist()


def get_session_denylist() -> SessionDenylist:
    """Return the process-wide denylist (a seam for the tests)."""
    return _denylist
