"""One way to connect to Redis for the rate limits, the sessions and the health check."""

import redis

#: Connection and socket timeouts, in seconds: during an outage a request
#: gets its answer quickly instead of holding a worker thread.
REDIS_TIMEOUT = 1.0


def create_redis_client(url: str) -> redis.Redis:
    """Create a Redis client with the timeouts every caller relies on.

    Creating the client opens no connection; the first command does.

    Args:
        url: Redis connection URL.

    Returns:
        A client that returns strings, not bytes.
    """
    return redis.Redis.from_url(
        url,
        socket_timeout=REDIS_TIMEOUT,
        socket_connect_timeout=REDIS_TIMEOUT,
        decode_responses=True,
    )
