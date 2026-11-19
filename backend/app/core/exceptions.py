"""Application-level exceptions shared by several modules."""


class AuthStoreUnavailableError(Exception):
    """Redis, which holds the sign-in counters and the session denylist, is down.

    The authentication checks fail closed during such an outage.  The API
    answers 503 Service Unavailable with an honest message instead of a
    misleading "session expired" or "too many attempts".
    """
