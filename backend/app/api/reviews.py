"""Public customer review endpoints."""

from fastapi import APIRouter, Depends, status
from kombu.exceptions import OperationalError as KombuOperationalError

from app.api.deps import get_review_service
from app.core.celery_app import REVIEW_QUEUE
from app.core.logging_config import get_logger
from app.core.rate_limiter import rate_limit_review_submission
from app.schemas.review import CreateReviewRequest, ReviewDto
from app.services.review_service import ReviewService
from app.tasks.review_tasks import analyze_review_task

logger = get_logger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post(
    "",
    response_model=ReviewDto,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_review_submission)],
)
def create_review(
    body: CreateReviewRequest,
    service: ReviewService = Depends(get_review_service),
) -> ReviewDto:
    """Accept a new customer review and schedule the AI analysis pipeline.

    The review is stored immediately and returned with a ``Pending`` analysis
    status — exactly like a review that was inserted by a bulk script.  The AI
    analysis and the draft response generation are executed by a background
    worker, so the client is never blocked by the provider round-trip.  The
    status only changes when a support operator picks the review up.

    Args:
        body: The submitted review payload.
        service: Service handling review persistence.

    Returns:
        The freshly created review.
    """
    review = service.create(body)
    logger.info("Review created: id=%s", review.id)

    # Enqueue the background analysis.  A broker outage must not lose the
    # review itself, so the failure is logged and the review is stored
    # without its analysis; the periodic requeue sweep puts it back on the
    # queue later.  Only broker failures are caught: a programming error
    # must surface.
    try:
        analyze_review_task.apply_async(args=[review.id], queue=REVIEW_QUEUE)
    except (KombuOperationalError, OSError) as exc:
        logger.error("Could not enqueue AI analysis for review %s: %s", review.id, exc)

    return review
