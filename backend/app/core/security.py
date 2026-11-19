"""Security and authentication utilities including JWT encoding and verification."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.session_store import get_session_denylist

#: Bearer authentication is optional: the browser sends the session cookie, and
#: the header is only a fallback for API clients.
security = HTTPBearer(auto_error=False)

#: Name of the httpOnly cookie that carries the administrator's access token.
#: Scripts cannot read it, so a cross-site scripting flaw cannot steal it.
SESSION_COOKIE_NAME: str = "access_token"

#: Cookie holding the CSRF token.  It is readable by page scripts on purpose:
#: the SPA copies it into :data:`CSRF_HEADER_NAME`, which a cross-site page
#: cannot do.  The names are the axios defaults, so no client code is needed.
CSRF_COOKIE_NAME: str = "XSRF-TOKEN"

#: Request header that has to repeat the CSRF cookie on unsafe requests.
CSRF_HEADER_NAME: str = "X-XSRF-TOKEN"

#: Methods that change state and therefore need the CSRF header.
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: Message returned when the CSRF header is missing or wrong.
_CSRF_FAILED: str = "The request could not be verified. Please reload the page"

#: Message returned for every authentication failure, so that responses never
#: disclose whether the token was missing, malformed, expired or forged.
_INVALID_CREDENTIALS: str = "Your session has expired. Please sign in again"


def create_access_token(data: dict[str, Any]) -> str:
    """Create a signed JWT access token with expiration time.

    The token carries the configured issuer and audience claims, so that a
    token minted for a different service is rejected during verification,
    and a unique ``jti`` that lets a sign-out revoke this one token.

    Args:
        data: Payload dictionary to encode into the token (e.g. {"sub": email}).

    Returns:
        Encoded JWT token string.
    """
    to_encode: dict[str, Any] = data.copy()
    expire: datetime = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiration_minutes)
    to_encode.update(
        {
            "exp": expire,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "jti": uuid.uuid4().hex,
        }
    )
    token: str = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_token_claims(token: str) -> dict[str, Any]:
    """Verify an access token and return its claims.

    Args:
        token: The encoded JWT taken from the session cookie or header.

    Returns:
        The verified claims, including ``sub``, ``exp`` and ``jti``.

    Raises:
        HTTPException: 401 if the signature, issuer, audience or expiry is
            wrong, or a required claim is missing.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "sub", "jti"]},
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS,
        ) from exc
    return payload


def decode_admin_token(token: str) -> str:
    """Validate an access token and return the administrator's login.

    Args:
        token: The encoded JWT token taken from the session cookie or header.

    Returns:
        Administrator login extracted from the token subject ("sub").

    Raises:
        HTTPException: If the token is expired, invalid, signed out, or
            missing the subject.
    """
    payload = decode_token_claims(token)

    subject: Any = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS,
        )

    # The token has to belong to the administrator account of this
    # deployment.  A token that was signed with the right key but carries a
    # different subject was not issued for this panel and is refused.
    if not secrets.compare_digest(
        subject.strip().lower().encode("utf-8"),
        settings.admin_email.strip().lower().encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS,
        )

    # A token whose session was signed out stays refused until it expires.
    if get_session_denylist().is_revoked(str(payload["jti"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS,
        )

    return subject


def verify_csrf(request: Request) -> None:
    """Require the CSRF header to repeat the CSRF cookie on unsafe requests.

    ``SameSite=Lax`` already keeps the session cookie away from cross-site
    form posts; this double-submit check is the second line of defence (for
    example against a compromised sibling subdomain).  Safe methods pass.

    Args:
        request: The incoming request.

    Raises:
        HTTPException: 403 when the header is missing or does not match.
    """
    if request.method not in _UNSAFE_METHODS:
        return
    cookie: str = request.cookies.get(CSRF_COOKIE_NAME, "")
    header: str = request.headers.get(CSRF_HEADER_NAME, "")
    if not cookie or not secrets.compare_digest(cookie.encode(), header.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_CSRF_FAILED)


def require_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Authenticate an administrator request from the session cookie or a Bearer header.

    The cookie is preferred, because the browser attaches it automatically.
    For the same reason a cookie-authenticated unsafe request must also pass
    the CSRF check; a Bearer header is never attached by the browser, so API
    clients using it are exempt.

    Args:
        request: The incoming request, which carries the cookies.
        credentials: The optional ``Authorization: Bearer`` credentials.

    Returns:
        The login of the authenticated administrator.

    Raises:
        HTTPException: 401 when no token is present or the token is rejected,
            403 when a cookie session fails the CSRF check.
    """
    token: str | None = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        verify_csrf(request)
    elif credentials is not None:
        token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS,
        )
    return decode_admin_token(token)
