"""Authentication endpoints for administrator access."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import settings
from app.core.passwords import verify_password
from app.core.rate_limiter import (
    LOGIN_FAILURE_WINDOW_SECONDS,
    RateLimiter,
    get_client_ip,
    get_login_failure_limiter,
)
from app.core.security import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    create_access_token,
    decode_token_claims,
    require_admin,
    verify_csrf,
)
from app.core.session_store import get_session_denylist
from app.schemas.auth import AdminSession, LoginInput

router = APIRouter(prefix="/api/auth", tags=["auth"])

#: Message shown when the submitted credentials do not match.
_INVALID_CREDENTIALS: str = "Invalid login or password. Please try again"

#: Message shown when too many failed sign-in attempts were made.
_TOO_MANY_ATTEMPTS: str = "Too many failed sign-in attempts. Please wait a few minutes and try again"


def _set_session_cookie(response: Response, token: str) -> None:
    """Store the access token in an httpOnly cookie that lives as long as the token.

    ``SameSite=Lax`` keeps the cookie away from cross-site POST requests, the
    first CSRF defence of the admin API; the double-submit header check
    (:func:`app.core.security.verify_csrf`) is the second.

    Args:
        response: The response that will carry the ``Set-Cookie`` header.
        token: The signed access token.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expiration_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _set_csrf_cookie(response: Response) -> None:
    """Issue a fresh CSRF token in a cookie the SPA can read.

    It lives as long as the session cookie; the SPA echoes it in the
    ``X-XSRF-TOKEN`` header of every state-changing request.

    Args:
        response: The response that will carry the ``Set-Cookie`` header.
    """
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(32),
        max_age=settings.jwt_expiration_minutes * 60,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """Expire the session cookie.

    Args:
        response: The response that will carry the expiring ``Set-Cookie`` header.
    """
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


@router.post("/login", response_model=AdminSession)
def login(
    request: Request,
    response: Response,
    input_data: LoginInput,
    limiter: RateLimiter = Depends(get_login_failure_limiter),
) -> AdminSession:
    """Authenticate an administrator and start a session cookie.

    Credentials are compared in constant time to avoid leaking the secret
    through response timing.

    Every attempt is recorded *before* the credentials are checked, in the
    same atomic step that counts the window, so a burst of parallel guesses
    gets no more tries than a sequential one.  Once an address is locked out,
    even the right password is refused until the window frees up, so
    guessing reveals nothing.  A successful sign-in clears the counter, so in
    effect only the failed attempts count and a legitimate sign-in never
    pushes a real user towards the lockout.  The budget is per address, so
    the administrator signing in from another address is not affected.

    Args:
        request: The incoming request, used to resolve the client IP.
        response: The response that receives the session cookie.
        input_data: The submitted email and password.
        limiter: The counter of the failed sign-in attempts.

    Returns:
        The signed-in administrator.

    Raises:
        HTTPException: 429 Too Many Requests when the client made too many
            failed sign-in attempts, or 401 Unauthorized when the credentials
            do not match.
    """
    ip: str = get_client_ip(request)

    # The attempt is counted before the password is checked, so a locked-out
    # client cannot keep guessing and watch for the one answer that differs.
    if not limiter.register_attempt(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_TOO_MANY_ATTEMPTS,
            headers={"Retry-After": str(LOGIN_FAILURE_WINDOW_SECONDS)},
        )

    # ``compare_digest`` only accepts ASCII strings; comparing non-ASCII
    # text directly would raise a TypeError and turn the endpoint into a
    # 500.  Both operands are encoded to bytes first, which works for any
    # input and keeps the comparison constant-time.
    email_matches: bool = secrets.compare_digest(
        input_data.email.strip().lower().encode("utf-8"),
        settings.admin_email.strip().lower().encode("utf-8"),
    )
    password_matches: bool = (
        verify_password(input_data.password, settings.admin_password_hash)
        if settings.admin_password_hash
        else secrets.compare_digest(input_data.password.encode("utf-8"), settings.admin_password.encode("utf-8"))
    )

    if email_matches and password_matches:
        limiter.reset(ip)
        _set_session_cookie(response, create_access_token({"sub": settings.admin_email}))
        _set_csrf_cookie(response)
        return AdminSession(email=settings.admin_email)

    # The credentials are wrong; the attempt recorded above stays in the
    # window and counts as a failure.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_INVALID_CREDENTIALS,
    )


@router.get("/me", response_model=AdminSession)
def current_session(
    request: Request,
    response: Response,
    email: str = Depends(require_admin),
) -> AdminSession:
    """Return the administrator behind the session cookie.

    The single-page application calls this on start-up to learn whether the
    browser still holds a valid session.  A browser that lost the CSRF cookie
    gets a new one here, so the session keeps working without a new sign-in.

    Args:
        request: The incoming request, used to look for the CSRF cookie.
        response: The response that may receive a CSRF cookie.
        email: The authenticated administrator login, resolved by the guard.

    Returns:
        The signed-in administrator.
    """
    if not request.cookies.get(CSRF_COOKIE_NAME):
        _set_csrf_cookie(response)
    return AdminSession(email=email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    """End the session: revoke the token and expire the cookies.

    The token's ``jti`` goes on the Redis denylist until the token would have
    expired, so a copied token stops working too.  If Redis cannot store the
    revocation, the request fails with 503 and retains the cookies so the
    user can retry.  The revocation itself needs a valid CSRF header: a
    cross-site page may clear the browser cookies, but it cannot make the
    server act on the token.

    Args:
        request: The incoming request, which carries the session cookie.
        response: The response that carries the expiring ``Set-Cookie`` headers.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        try:
            verify_csrf(request)
            claims = decode_token_claims(token)
        except HTTPException:
            claims = {}
        if claims:
            get_session_denylist().revoke(str(claims["jti"]), float(claims["exp"]))
    _clear_session_cookie(response)
