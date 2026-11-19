"""Review AI Dashboard FastAPI application entry point."""

import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from typing import Any, TypedDict

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api import admin_reviews, auth, health, reviews
from app.core.config import describe_settings, settings
from app.core.exceptions import AuthStoreUnavailableError
from app.core.logging_config import get_logger, setup_logging

# Configure logging before anything else so that all subsequent loggers inherit
# the root configuration.
setup_logging()

logger = get_logger(__name__)

#: Paths excluded from the per-request access log to keep it readable.
_QUIET_PATHS = frozenset({"/health", "/health/ready"})

#: Human-readable names of the request fields, used in validation messages.
_FIELD_LABELS: dict[str, str] = {
    "author_name": "Name",
    "email": "Email",
    "text": "Review",
    "password": "Password",
}

#: Prefixes FastAPI adds to the location of a validation error.
_LOCATION_PREFIXES = frozenset({"body", "query", "path", "header"})


class DocsUrls(TypedDict):
    """Documentation-related arguments accepted by :class:`fastapi.FastAPI`."""

    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None


def api_docs_urls(environment: str) -> DocsUrls:
    """Return the documentation URLs FastAPI should expose.

    The interactive documentation lists every endpoint, so it is switched off
    in production.  Other environments keep the usual ``/docs`` pages.

    Args:
        environment: The configured deployment environment name.

    Returns:
        Keyword arguments for :class:`fastapi.FastAPI`; ``None`` disables a page.
    """
    if environment.strip().lower() == "production":
        return DocsUrls(docs_url=None, redoc_url=None, openapi_url=None)
    # ReDoc is not proxied by Nginx, so only Swagger UI is published.
    return DocsUrls(docs_url="/docs", redoc_url=None, openapi_url="/openapi.json")


def _describe_validation_error(errors: Sequence[dict[str, Any]]) -> str:
    """Turn FastAPI validation errors into one human-readable sentence.

    The message names the offending field, so that the user knows what to
    correct instead of being told that "the input is invalid".

    Args:
        errors: The raw error list produced by Pydantic.

    Returns:
        A single sentence describing what has to be fixed.
    """
    messages: list[str] = []

    for error in errors:
        # A numeric part is a position in the raw JSON (a decoding error),
        # not a field name, so it is left out as well.
        location = [
            str(part)
            for part in error.get("loc") or ()
            if str(part) not in _LOCATION_PREFIXES and not str(part).isdigit()
        ]
        field: str = location[-1] if location else ""
        # An error without a field concerns the request body as a whole.
        label: str = _FIELD_LABELS.get(field, field.replace("_", " ").capitalize()) if field else "Request body"
        kind: str = str(error.get("type", ""))
        raw_message: str = str(error.get("msg", ""))
        context: dict[str, Any] = error.get("ctx") or {}

        if kind == "missing":
            messages.append(f"{label} is required")
        elif kind == "json_invalid":
            messages.append(f"{label} must be valid JSON")
        elif kind == "value_error":
            raw_input = error.get("input")
            # The schema drops NUL characters, so a field made of them is
            # blank as well.
            if isinstance(raw_input, str) and not raw_input.replace("\x00", "").strip():
                # An empty field is missing, not malformed.  The blank check
                # comes first, because the same "value_error" kind covers
                # both a blank field and a malformed one.
                messages.append(f"{label} is required")
            elif "email" in raw_message.lower():
                messages.append(f"{label} must be a valid email address")
            else:
                messages.append(f"{label}: {raw_message}")
        elif kind == "string_too_short":
            min_length: int = context.get("min_length", 1)
            if min_length <= 1:
                messages.append(f"{label} is required")
            else:
                messages.append(f"{label} must be at least {min_length} characters long")
        elif kind == "string_too_long":
            messages.append(f"{label} must be at most {context.get('max_length', '')} characters long")
        else:
            messages.append(f"{label}: {raw_message}")

    return ". ".join(messages) if messages else "The submitted data is invalid"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Execute startup and shutdown application tasks.

    The database schema is owned by Alembic (``alembic upgrade head``); the
    application never creates or mutates tables at runtime.

    Yields:
        ``None`` while the application is serving requests.
    """
    logger.info("Starting Review AI Dashboard API with %s", describe_settings())
    yield
    logger.info("Review AI Dashboard API stopped")


app = FastAPI(
    title="Review AI Dashboard API",
    description="FastAPI service for customer review management and AI analysis",
    version="1.0.0",
    lifespan=lifespan,
    **api_docs_urls(settings.environment),
)


@app.middleware("http")
async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log each incoming HTTP request with method, path, status code and duration.

    Args:
        request: The incoming Starlette request.
        call_next: The next middleware or route handler in the chain.

    Returns:
        The HTTP response produced by the downstream handler.
    """
    start: float = time.perf_counter()
    status_code: int = 500
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        # Also runs when the handler raised, so a failure still leaves an
        # access-log line (reported as 500) before the exception propagates.
        duration_ms: float = (time.perf_counter() - start) * 1000
        if request.url.path not in _QUIET_PATHS:
            logger.info(
                "%s %s -> %s (%.1f ms)",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )


app.include_router(reviews.router)
app.include_router(auth.router)
app.include_router(admin_reviews.router)
app.include_router(health.router)


@app.exception_handler(AuthStoreUnavailableError)
async def auth_store_unavailable_handler(
    request: Request,
    exc: AuthStoreUnavailableError,
) -> JSONResponse:
    """Report a Redis outage on an authenticated path as 503, honestly.

    Without it the fail-closed checks would answer "session expired" or
    "too many attempts", which sends the administrator in the wrong
    direction.

    Args:
        request: The incoming Starlette request.
        exc: The raised error.

    Returns:
        A 503 response with a readable message.
    """
    return JSONResponse(
        status_code=503,
        content={"detail": "Authentication is temporarily unavailable. Please try again in a minute."},
    )


@app.exception_handler(OperationalError)
async def database_unavailable_handler(
    request: Request,
    exc: OperationalError,
) -> JSONResponse:
    """Report a lost database connection as 503 with a readable message.

    Without it the client gets a bare plain-text 500, and the dashboard can
    only say "Server error".  Only the driver's error is logged: the full
    SQLAlchemy message would also carry the statement's parameters, such
    as a customer's email address.

    Args:
        request: The incoming Starlette request.
        exc: The raised error.

    Returns:
        A 503 response with a readable message.
    """
    logger.error("Database is unavailable: %s", exc.orig)
    return JSONResponse(
        status_code=503,
        content={"detail": "The database is temporarily unavailable. Please try again in a minute."},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a human-readable message for every rejected request payload.

    FastAPI answers with a raw list of Pydantic errors, which is useless for
    the end user.  The message is built here, so that the backend stays the
    single source of truth for the wording of every client error.

    Args:
        request: The incoming Starlette request.
        exc: The raised validation error.

    Returns:
        A 422 response carrying a single human-readable sentence.
    """
    return JSONResponse(
        status_code=422,
        content={"detail": _describe_validation_error(exc.errors())},
    )
