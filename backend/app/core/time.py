"""Time helpers shared across the application.

The database schema stores timestamps as naive UTC (``TIMESTAMP WITHOUT TIME
ZONE``).  Writing a timezone-aware value into such a column makes PostgreSQL
convert it using the *session* time zone, which silently shifts the stored
value on servers that are not configured for UTC.  This helper keeps every
timestamp explicitly naive-UTC.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime.

    Returns:
        The current UTC time without timezone information.
    """
    return datetime.now(UTC).replace(tzinfo=None)
