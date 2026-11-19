"""Celery tasks performing the background AI analysis of a review.

The task opens its own database session — it runs long after the HTTP
request that scheduled it has been closed.  A retry preserves an existing
analysis and generates a new draft response.
"""

import asyncio
import random
from datetime import timedelta

import httpx
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import OperationalError

from app.ai.factory import get_response_generator, get_review_analyzer
from app.core.celery_app import REVIEW_QUEUE, celery_app
from app.core.logging_config import get_logger
from app.core.time import utcnow
from app.db.session import SessionLocal
from app.models.review import Review
from app.services.review_ai_service import ReviewAiService

logger = get_logger(__name__)


async def _run_pipeline(review_id: str) -> str | None:
    """Run the analysis and draft response generation for one review.

    The analysis is skipped when an earlier attempt already stored it, so a
    retry only redoes the step that failed.

    Args:
        review_id: Unique review UUID to process.

    Returns:
        The review identifier, or ``None`` when the review does not exist.
    """
    session = SessionLocal()
    try:
        service = ReviewAiService(
            session,
            get_review_analyzer(),
            get_response_generator(),
        )
        stored = session.get(Review, review_id)
        if stored is None:
            logger.warning("Review %s no longer exists — task skipped", review_id)
            return None

        # A retry after a failed draft must not analyse the review again:
        # that would spend provider quota and could change the rating.
        if stored.analyzed_at_utc is None:
            await service.analyze(review_id)

        await service.generate_draft_response(review_id)
        logger.info("AI pipeline finished for review %s", review_id)
        return review_id
    finally:
        session.close()


#: Delay of the first retry, in seconds; every next one doubles it.
RETRY_BASE_DELAY_SECONDS = 15

#: Retries after the first attempt (15 s, 30 s, 60 s, 120 s).
MAX_RETRIES = 4

#: Provider answers worth retrying: rate limiting and server-side failures.
_TRANSIENT_STATUS_CODES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def is_transient(exc: BaseException) -> bool:
    """Tell a temporary failure from a permanent one.

    Network problems, a provider that hangs past the soft time limit,
    provider rate limits, provider outages and a lost database connection
    clear up on their own, so they are retried.  A
    missing API key, a malformed answer or any other 4xx would fail the
    same way again, so retrying it only wastes quota.

    Args:
        exc: The exception raised by the pipeline.

    Returns:
        ``True`` when a retry has a chance to succeed.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_STATUS_CODES
    return isinstance(exc, (httpx.TransportError, OperationalError, SoftTimeLimitExceeded))


def retry_delay(retries: int) -> int:
    """Return the exponential back-off delay, with jitter, for a retry.

    Args:
        retries: How many retries were already made.

    Returns:
        Seconds to wait; the jitter spreads simultaneous retries apart.
    """
    base: int = RETRY_BASE_DELAY_SECONDS * 2**retries
    return base + random.randint(0, base // 3)  # noqa: S311 - jitter, not a secret


@celery_app.task(name="reviews.analyze", bind=True, max_retries=MAX_RETRIES)  # type: ignore[untyped-decorator]  # Celery ships no types
def analyze_review_task(self: Task, review_id: str) -> str | None:
    """Analyse a review and generate a draft response for it.

    The AI provider round-trip is executed in a fresh event loop, because
    the Celery worker is a synchronous process.  Temporary failures are
    retried with exponential back-off; permanent ones are logged, and the
    review stays without its analysis until the periodic requeue sweep
    tries it again (see :func:`requeue_stale_reviews_task`).

    Args:
        self: The bound task instance (injected by Celery).
        review_id: Unique review UUID to process.

    Returns:
        The review identifier on success, ``None`` when the review is gone
        or the failure is permanent.
    """
    try:
        return asyncio.run(_run_pipeline(review_id))
    except Exception as exc:
        if not is_transient(exc):
            logger.exception("AI pipeline failed permanently for review %s", review_id)
            return None
        if self.request.retries >= MAX_RETRIES:
            # No retry is left: the task fails with this error, exactly as
            # Celery's own retry() would end it, and the requeue sweep takes
            # over the review later.
            logger.error(
                "AI pipeline failed for review %s (%r); giving up after %d retries",
                review_id,
                exc,
                MAX_RETRIES,
            )
            raise
        delay = retry_delay(self.request.retries)
        logger.warning(
            "AI pipeline failed for review %s (%r); retry %d/%d in %d s",
            review_id,
            exc,
            self.request.retries + 1,
            MAX_RETRIES,
            delay,
        )
        raise self.retry(exc=exc, countdown=delay) from exc


#: A review without an analysis or a draft whose last run started this long
#: ago — its submission or its last requeue — is considered lost.  The worst
#: case of the analysis task is about 13 minutes: back-off pauses of
#: 15+30+60+120 s plus up to a third of jitter, and five attempts that may
#: each run until the 100 s soft time limit.  Twenty minutes stays clear of
#: it, so a review that is still being retried is never queued twice.
STALE_AFTER = timedelta(minutes=20)

#: Upper bound of reviews put back on the queue by one sweep.
REQUEUE_BATCH = 50

#: The sweep gives up on a review after this many requeues: one that can
#: never be analysed must not burn provider quota forever or crowd out the
#: newer reviews of the batch.
MAX_REQUEUES = 3


@celery_app.task(name="reviews.requeue_stale")  # type: ignore[untyped-decorator]  # Celery ships no types
def requeue_stale_reviews_task() -> int:
    """Put reviews that never got their AI analysis back on the queue.

    A review can miss its analysis when the broker was down at submission
    time, when Redis restarted and lost its queue, or when every retry
    failed.  The beat scheduler runs this sweep every few minutes, so such a
    review is picked up again instead of staying pending without a draft.
    Each successful publication is counted and timed: the next one waits a
    full :data:`STALE_AFTER` period, and a review that still fails after
    :data:`MAX_REQUEUES` rounds is left for the support operator.  A broker
    failure consumes no requeue allowance.

    Returns:
        The number of reviews put back on the queue.
    """
    session = SessionLocal()
    eligible = (
        or_(Review.analyzed_at_utc.is_(None), Review.ai_draft_response.is_(None)),
        func.coalesce(Review.last_requeued_at_utc, Review.created_at_utc) < utcnow() - STALE_AFTER,
        Review.analysis_requeues < MAX_REQUEUES,
    )
    published = 0
    try:
        candidate_ids: list[str] = list(
            session.scalars(
                select(Review.id).where(*eligible).order_by(Review.created_at_utc, Review.id).limit(REQUEUE_BATCH)
            )
        )
        session.rollback()

        for review_id in candidate_ids:
            # Recheck and lock just this row: overlapping sweeps skip a row
            # already claimed by another one, and no other row stays locked
            # during the bounded broker round-trip.
            review = session.scalar(
                select(Review).where(Review.id == review_id, *eligible).with_for_update(skip_locked=True)
            )
            if review is None:
                session.rollback()
                continue
            try:
                analyze_review_task.apply_async(args=[review_id], queue=REVIEW_QUEUE)
            except (KombuOperationalError, OSError) as exc:
                session.rollback()
                logger.error("Could not requeue AI analysis for review %s: %s", review_id, exc)
                continue
            review.analysis_requeues += 1
            review.last_requeued_at_utc = utcnow()
            session.commit()
            published += 1
    finally:
        session.close()

    if published:
        logger.info("Requeued %d review(s) without an AI analysis", published)
    return published
