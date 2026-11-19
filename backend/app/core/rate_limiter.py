"""Redis-backed sliding-window rate limiter for the API endpoints.

The counter lives in Redis, so the limit is enforced consistently across
every API replica and every worker process — an in-memory counter would give
each replica its own budget and let a client multiply its allowance by the
number of replicas.

Redis holds one sorted set per client IP.  Every request is a member of the
set scored by its timestamp; members older than the window are removed, and
the request is allowed when fewer than *max_requests* members remain.

When Redis is unreachable the review-submission limiter fails **open**:
rejecting customer feedback because of a cache outage would be worse than the
risk it prevents.  The draft-regeneration limiter fails open as well.  The
sign-in failure limiter fails **closed** instead, so an
outage never turns into an unlimited password-guessing window: it raises
:class:`AuthStoreUnavailableError`, which the API answers with a 503.
"""

import time
from threading import Lock
from uuid import uuid4

import redis
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.exceptions import AuthStoreUnavailableError
from app.core.redis_client import create_redis_client

#: Prefix of the Redis keys holding the per-client submission windows.
_KEY_PREFIX = "ratelimit:reviews:"

#: Prefix of the Redis keys holding the per-client sign-in failure windows.
_LOGIN_KEY_PREFIX = "ratelimit:login:"

#: Prefix of the Redis keys holding the per-client draft regeneration windows.
_REGENERATION_KEY_PREFIX = "ratelimit:regenerate:"

#: Maximum number of allowed review submissions per client and window.
MAX_SUBMISSIONS = 10

#: Length of the review submission window in seconds.
SUBMISSION_WINDOW_SECONDS = 60

#: Maximum number of failed sign-in attempts per client and window.
MAX_LOGIN_FAILURES = 5

#: Length of the sign-in failure window in seconds.
LOGIN_FAILURE_WINDOW_SECONDS = 300

#: Draft regenerations allowed per client within one window.
MAX_DRAFT_REGENERATIONS = 10

#: Length of the draft regeneration window in seconds.
DRAFT_REGENERATION_WINDOW_SECONDS = 60

#: How long a client key is kept in Redis after its last request.  It must
#: cover the longest window, the five-minute sign-in window.
_KEY_TTL_SECONDS = 300


class RateLimiter:
    """Sliding-window rate limiter backed by Redis sorted sets.

    Args:
        max_requests: Maximum number of allowed requests per window.
        window_seconds: Length of the sliding window in seconds.
        redis_url: Redis connection URL.
        client: An existing Redis client. When given, it is used as-is
            instead of creating one — this keeps the limiter testable.
        key_prefix: Prefix of the Redis keys holding the windows. Every
            policy needs its own prefix, so that two counters never share a
            budget.
        fail_closed: Whether :meth:`register_attempt` raises on a Redis
            outage instead of allowing the attempt.  :meth:`is_allowed`
            always fails open.
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        redis_url: str | None = None,
        client: redis.Redis | None = None,
        key_prefix: str = _KEY_PREFIX,
        fail_closed: bool = False,
    ) -> None:
        """Initialise the rate limiter with the given policy parameters.

        Args:
            max_requests: Maximum number of allowed requests per window.
            window_seconds: Length of the sliding window in seconds.
            redis_url: Redis connection URL. Defaults to the configured one.
            client: An existing Redis client. When given, it is used as-is
                instead of creating one — this keeps the limiter testable.
            key_prefix: Prefix of the Redis keys holding the windows. Every
                policy needs its own prefix, so that two counters never
                share a budget.
            fail_closed: Whether :meth:`register_attempt` raises on a Redis
                outage instead of allowing the attempt; :meth:`is_allowed`
                always fails open.  Submissions fail open; sign-in failures
                fail closed, so an outage never opens an unlimited
                password-guessing window.
        """
        self.max_requests: int = max_requests
        self.window_seconds: int = window_seconds
        self._redis_url: str = redis_url or settings.redis_url
        self._client: redis.Redis | None = client
        self._key_prefix: str = key_prefix
        self._fail_closed: bool = fail_closed
        self._lock: Lock = Lock()

    @property
    def client(self) -> redis.Redis:
        """Return the Redis client, created on first use and reused afterwards.

        Returns:
            The :class:`redis.Redis` client; it connects on its first command.
        """
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = create_redis_client(self._redis_url)
        return self._client

    def is_allowed(self, ip: str) -> bool:
        """Check whether the given IP address is within the rate limit.

        An allowed request consumes one unit of the client's budget; a
        rejected one does not, so a client that keeps retrying regains
        access as soon as its oldest request leaves the window.

        Args:
            ip: The client's IP address string.

        Returns:
            ``True`` if the request is within the allowed rate, ``False``
            otherwise.  A Redis outage results in ``True`` (fail open).
        """
        key: str = self._key(ip)
        now: float = self._now()
        cutoff: float = now - self.window_seconds

        try:
            client = self.client
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.zcard(key)
            _removed, count = pipe.execute()
            if count >= self.max_requests:
                return False

            # Two concurrent requests may both pass the check above; the
            # submission limit tolerates that small overshoot.
            pipe = client.pipeline()
            pipe.zadd(key, {f"{now}:{uuid4().hex}": now})
            pipe.expire(key, _KEY_TTL_SECONDS)
            pipe.execute()
            return True
        except redis.RedisError:
            # Fail open: a cache outage must not take the whole API down.
            return True

    def register_attempt(self, ip: str) -> bool:
        """Record one attempt and report whether it is within the budget.

        The window is pruned, the attempt is added and the window is counted
        in a single MULTI/EXEC pipeline, so a burst of parallel attempts
        cannot all pass: each one counts the attempts recorded before it.  An
        attempt over the limit is taken out of the window again, so a client
        that keeps knocking while locked out does not prolong its lockout.

        Args:
            ip: The client's IP address string.

        Returns:
            ``True`` while the window, this attempt included, holds no more
            than *max_requests* attempts.  A Redis outage returns ``True`` for
            a limiter that fails open.

        Raises:
            AuthStoreUnavailableError: On a Redis outage, when the limiter
                fails closed.
        """
        key: str = self._key(ip)
        now: float = self._now()
        cutoff: float = now - self.window_seconds
        # The member must be unique, otherwise two attempts made within the
        # same microsecond would collapse into a single entry and the client
        # would never reach the limit.
        member: str = f"{now}:{uuid4().hex}"

        try:
            pipe = self.client.pipeline()
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, _KEY_TTL_SECONDS)
            _removed, _added, count, _expired = pipe.execute()
            if count <= self.max_requests:
                return True
            self.client.zrem(key, member)
            return False
        except redis.RedisError:
            if self._fail_closed:
                raise AuthStoreUnavailableError from None
            return True

    def reset(self, ip: str) -> None:
        """Give the client its full budget back.

        Args:
            ip: The client's IP address string.
        """
        key: str = self._key(ip)

        try:
            self.client.delete(key)
        except redis.RedisError:
            return

    def _key(self, ip: str) -> str:
        """Build the Redis key holding the window of one client.

        Args:
            ip: The client's IP address string.

        Returns:
            The full Redis key.
        """
        return f"{self._key_prefix}{ip}"

    @staticmethod
    def _now() -> float:
        """Return the current timestamp used for the window scoring."""
        return time.time()


# Module-level singleton used by the FastAPI dependency below.
_review_submission_limiter = RateLimiter(
    max_requests=MAX_SUBMISSIONS,
    window_seconds=SUBMISSION_WINDOW_SECONDS,
)

#: Module-level singleton holding the failed sign-in attempts per client.
_login_failure_limiter = RateLimiter(
    max_requests=MAX_LOGIN_FAILURES,
    window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
    key_prefix=_LOGIN_KEY_PREFIX,
    fail_closed=True,
)


#: Module-level singleton capping the paid AI calls of the draft regeneration.
_draft_regeneration_limiter = RateLimiter(
    max_requests=MAX_DRAFT_REGENERATIONS,
    window_seconds=DRAFT_REGENERATION_WINDOW_SECONDS,
    key_prefix=_REGENERATION_KEY_PREFIX,
)


def get_draft_regeneration_limiter() -> RateLimiter:
    """Return the limiter of the AI draft regeneration.

    Every regeneration is a paid, synchronous provider call, so a stuck
    client or a stolen session must not burn the quota in a loop.

    Returns:
        The shared rate limiter instance.
    """
    return _draft_regeneration_limiter


def get_login_failure_limiter() -> RateLimiter:
    """Return the counter of the sign-in attempts.

    Every attempt is recorded, and a successful sign-in clears the window, so
    in effect only the failed attempts count against the budget.

    Returns:
        The shared rate limiter instance.
    """
    return _login_failure_limiter


def get_client_ip(request: Request) -> str:
    """Extract the real client IP from the request.

    uvicorn listens on 127.0.0.1 inside the container, so every request
    arrives through nginx.  nginx passes the ``X-Forwarded-For`` header of the
    platform's load balancer on unchanged and sets it to the peer address only
    when it is absent.  The balancer appends the address of the visitor, so
    the last entry is the only trustworthy one: earlier entries are supplied
    by the client and would allow it to mint a fresh rate-limit budget on
    every request.

    Args:
        request: The incoming FastAPI/Starlette request object.

    Returns:
        A string containing the client IP address.
    """
    forwarded_for: str | None = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        entries: list[str] = [entry.strip() for entry in forwarded_for.split(",") if entry.strip()]
        if entries:
            # The balancer appends the address of the visitor it received
            # the request from, so the last entry is the real client.
            return entries[-1]

    # Fallback for a request without the header: nginx sets X-Real-IP to the
    # peer address, overwriting any value the client sent, and uvicorn is
    # reachable only through nginx, so the header cannot be forged.
    real_ip: str | None = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    if request.client:
        host: str = request.client.host
        return host
    return "unknown"


def rate_limit_review_submission(request: Request) -> None:
    """FastAPI dependency that enforces the review-submission rate limit.

    Args:
        request: The incoming request.

    Raises:
        HTTPException: 429 Too Many Requests when the client IP has exceeded
            the allowed number of requests in the current window.
    """
    ip: str = get_client_ip(request)
    if not _review_submission_limiter.is_allowed(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait before submitting another review.",
            # The whole window is the longest the client may have to wait.
            headers={"Retry-After": str(SUBMISSION_WINDOW_SECONDS)},
        )
