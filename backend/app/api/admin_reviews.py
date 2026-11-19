"""Protected administrator review management endpoints."""

import asyncio
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import status as http_status
from fastapi.responses import StreamingResponse
from pydantic import BeforeValidator

from app.ai.errors import AiProviderError
from app.api.deps import get_review_ai_service, get_review_service
from app.core.csv_export import iter_reviews_csv
from app.core.logging_config import get_logger
from app.core.rate_limiter import (
    DRAFT_REGENERATION_WINDOW_SECONDS,
    RateLimiter,
    get_client_ip,
    get_draft_regeneration_limiter,
)
from app.core.security import require_admin
from app.core.time import utcnow
from app.models.review import AnalysisStatus, Priority, Rating
from app.schemas.review import (
    AdminReviewDto,
    PaginatedResponse,
    ReviewQuery,
    ReviewStatistics,
    UpdateReviewStatusRequest,
)
from app.services.review_ai_service import ReviewAiService
from app.services.review_service import ReviewService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/admin/reviews",
    tags=["admin-reviews"],
    dependencies=[Depends(require_admin)],
)

#: Fields the admin list is allowed to sort by.
SortField = Literal["created_at_utc", "rating", "priority"]

#: Export formats the admin list is able to produce.
ExportFormat = Literal["csv"]

#: Message returned when the AI provider could not produce a draft.
_AI_PROVIDER_UNAVAILABLE: str = "The AI provider is unavailable right now. Please try again in a moment"


def _empty_to_none(value: Any) -> Any:
    """Treat an empty filter value as "no filter".

    The admin panel renders an "All ..." option in every filter dropdown.
    Browsers submit such an option as an empty string, which the enum
    validation would otherwise reject with HTTP 422 and leave the user
    staring at an empty table.

    Args:
        value: The raw filter value received from the query string.

    Returns:
        The value itself, or ``None`` when it is empty.
    """
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _empty_to_true(value: Any) -> Any:
    """Treat an empty boolean filter as "yes" (the default sort order).

    Args:
        value: The raw boolean value received from the query string.

    Returns:
        The value itself, or ``True`` when it is empty.
    """
    if isinstance(value, str) and not value.strip():
        return True
    return value


#: Filter parameters that accept an empty string as "no filter".
OptionalStatus = Annotated[
    AnalysisStatus | None,
    BeforeValidator(_empty_to_none),
    Query(description="Filter by review handling status"),
]
OptionalPriority = Annotated[
    Priority | None,
    BeforeValidator(_empty_to_none),
    Query(description="Filter by priority"),
]
OptionalRating = Annotated[
    Rating | None,
    BeforeValidator(_empty_to_none),
    Query(description="Filter by rating"),
]
OptionalSortField = Annotated[
    SortField | None,
    BeforeValidator(_empty_to_none),
    Query(description="Field to sort by"),
]
SortDescending = Annotated[
    bool,
    BeforeValidator(_empty_to_true),
    Query(description="Sort in descending order"),
]


def review_query(
    status: OptionalStatus = None,
    rating: OptionalRating = None,
    priority: OptionalPriority = None,
    sort_by: OptionalSortField = None,
    descending: SortDescending = True,
) -> ReviewQuery:
    """Read the filter and sort parameters shared by the list and the export.

    Both endpoints take their parameters from this one dependency, so the
    exported file always matches the list the admin sees.

    Args:
        status: Optional analysis status filter.
        rating: Optional star rating filter.
        priority: Optional priority filter.
        sort_by: Optional sort field.
        descending: Whether to sort in descending order.

    Returns:
        The query the review service runs.
    """
    return ReviewQuery(
        status=status,
        rating=rating,
        priority=priority,
        sort_by=sort_by,
        descending=descending,
    )


@router.get("", response_model=PaginatedResponse)
def get_all_reviews(
    query: ReviewQuery = Depends(review_query),
    page: int = Query(1, ge=1, le=10_000, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    service: ReviewService = Depends(get_review_service),
) -> PaginatedResponse:
    """Retrieve all reviews with optional filtering, sorting, and pagination.

    Args:
        query: The filters and the sort order.
        page: Current page number (1-based).
        page_size: Maximum number of items per page.
        service: Review service providing the data.

    Returns:
        A page of reviews together with the pagination metadata.
    """
    return service.get_all_paginated(query, page=page, page_size=page_size)


@router.get("/statistics", response_model=ReviewStatistics)
def get_statistics(
    service: ReviewService = Depends(get_review_service),
) -> ReviewStatistics:
    """Get aggregate statistics over the whole review dataset.

    Args:
        service: Review service providing the data.

    Returns:
        The review counts per star rating, the overall total and the average
        rating.
    """
    return service.get_statistics()


@router.get("/export")
def export_reviews(
    format: ExportFormat = Query("csv", description="Export format"),
    query: ReviewQuery = Depends(review_query),
    service: ReviewService = Depends(get_review_service),
) -> StreamingResponse:
    """Export the reviews as a CSV file.

    The same filters as the list endpoint apply, so the file contains
    exactly the reviews the admin currently sees.  The response is
    streamed, so exporting a large dataset does not block the server.

    Args:
        format: The export format. Only ``csv`` is supported.
        query: The filters and the sort order, shared with the list.
        service: Review service providing the data.

    Returns:
        A streaming response with the CSV file attached.
    """
    filename = f"reviews-{utcnow().strftime('%Y%m%d-%H%M%S')}.csv"

    return StreamingResponse(
        iter_reviews_csv(service.stream_all(query)),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{id}", response_model=AdminReviewDto)
def get_review_by_id(
    id: str,
    service: ReviewService = Depends(get_review_service),
) -> AdminReviewDto:
    """Retrieve full details of a specific review by ID."""
    review = service.get_by_id(id)
    if not review:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return review


@router.patch("/{id}/status", response_model=AdminReviewDto)
def update_review_status(
    id: str,
    request: UpdateReviewStatusRequest,
    service: ReviewService = Depends(get_review_service),
) -> AdminReviewDto:
    """Update the operator-managed handling status of a review."""
    review = service.update_status(id, request.analysis_status)
    if not review:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return review


@router.post("/{id}/regenerate-draft", response_model=AdminReviewDto)
def regenerate_draft_response(
    id: str,
    request: Request,
    service: ReviewAiService = Depends(get_review_ai_service),
    limiter: RateLimiter = Depends(get_draft_regeneration_limiter),
) -> AdminReviewDto:
    """Regenerate the AI draft response for a review.

    The operator can keep clicking until they are happy with the generated
    reply, since each call produces a fresh draft for the same review text.

    A failing AI provider (timeout, quota, malformed answer) is reported as
    502 Bad Gateway with a readable message instead of a bare 500; the
    previously stored draft stays untouched.

    The endpoint is synchronous on purpose: the service talks to the
    database through a blocking session, so FastAPI runs it in the thread
    pool, and the provider round-trip gets its own event loop there.  An
    ``async`` endpoint would block the server's event loop on every query.
    """
    # Each call is a paid provider round-trip, so a looping client is capped.
    if not limiter.is_allowed(get_client_ip(request)):
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many draft regenerations. Please wait a minute and try again.",
            headers={"Retry-After": str(DRAFT_REGENERATION_WINDOW_SECONDS)},
        )

    try:
        review = asyncio.run(service.generate_draft_response(id))
    # Only provider failures become a 502; any other exception is a bug and
    # surfaces as a 500 instead of hiding behind "AI provider unavailable".
    except (httpx.HTTPError, AiProviderError) as exc:
        logger.error("Draft regeneration failed for review %s: %r", id, exc)
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=_AI_PROVIDER_UNAVAILABLE,
        ) from exc
    if not review:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return review
