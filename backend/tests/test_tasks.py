"""Tests for the Celery background analysis task."""

import asyncio
from unittest.mock import patch

import httpx
import pytest
from celery.exceptions import SoftTimeLimitExceeded
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.review import AnalysisStatus, Priority, Review
from app.tasks.review_tasks import (
    MAX_REQUEUES,
    MAX_RETRIES,
    STALE_AFTER,
    _run_pipeline,
    analyze_review_task,
    is_transient,
    requeue_stale_reviews_task,
    retry_delay,
)
from tests.doubles import FAKE_DRAFT, FakeChatServer
from tests.factories import create_review


def test_task_is_registered_with_the_expected_name() -> None:
    """The task carries the name the worker subscribes to."""
    assert analyze_review_task.name == "reviews.analyze"


def test_pipeline_fills_the_analysis_and_keeps_the_review_pending(
    db_session: Session,
) -> None:
    """The pipeline analyses the review and leaves it pending.

    The review waits for a support operator to pick it up, exactly like a
    review added through a bulk script.
    """
    review = create_review(db_session)

    with patch("app.tasks.review_tasks.SessionLocal", return_value=db_session):
        result = asyncio.run(_run_pipeline(review.id))

    assert result == review.id

    db_session.expire_all()
    stored = db_session.execute(select(Review).where(Review.id == review.id)).scalar_one()
    assert stored.analysis_status == AnalysisStatus.PENDING.value
    assert stored.rating is not None
    assert stored.ai_draft_response is not None


def test_pipeline_skips_a_missing_review(db_session: Session) -> None:
    """Running the pipeline for an unknown review is a no-op."""
    with patch("app.tasks.review_tasks.SessionLocal", return_value=db_session):
        result = asyncio.run(_run_pipeline("does-not-exist"))

    assert result is None


def test_reviews_are_analysed_one_after_another(db_session: Session, fake_groq: FakeChatServer) -> None:
    """Every review gets its analysis and draft, not only the first one.

    The worker runs its tasks one after another, each in a fresh event loop,
    and the provider is reached over a real socket, as in production.
    """
    review_ids = [create_review(db_session).id for _ in range(3)]

    with patch("app.tasks.review_tasks.SessionLocal", return_value=db_session):
        results = [asyncio.run(_run_pipeline(review_id)) for review_id in review_ids]

    assert results == review_ids
    for review_id in review_ids:
        stored = db_session.get(Review, review_id)
        assert stored is not None
        assert stored.priority == Priority.HIGH.value
        assert stored.needs_urgent_response is True
        assert stored.ai_draft_response == FAKE_DRAFT


def _status_error(code: int) -> httpx.HTTPStatusError:
    """Build the error httpx raises for a provider answer with ``code``."""
    request = httpx.Request("POST", "https://provider.test/chat/completions")
    return httpx.HTTPStatusError("provider error", request=request, response=httpx.Response(code, request=request))


@pytest.mark.parametrize("code", [429, 500, 503])
def test_rate_limits_and_server_errors_are_transient(code: int) -> None:
    """The provider will likely answer later, so these are retried."""
    assert is_transient(_status_error(code)) is True


def test_network_and_database_outages_are_transient() -> None:
    """Lost connections clear up on their own."""
    assert is_transient(httpx.ConnectTimeout("timeout")) is True
    assert is_transient(OperationalError("SELECT 1", {}, Exception("down"))) is True


@pytest.mark.parametrize(
    "exc",
    [_status_error(401), _status_error(400), ValueError("Groq API key not configured"), KeyError("choices")],
)
def test_configuration_and_answer_errors_are_permanent(exc: Exception) -> None:
    """Retrying these would fail the same way and only burn provider quota."""
    assert is_transient(exc) is False


def test_retry_delay_grows_exponentially() -> None:
    """Each retry waits about twice as long as the previous one."""
    for retries, base in enumerate([15, 30, 60, 120]):
        assert base <= retry_delay(retries) <= base + base // 3


def test_a_permanent_failure_is_not_retried() -> None:
    """A missing API key ends the task without scheduling a retry."""
    with (
        patch(
            "app.tasks.review_tasks._run_pipeline",
            side_effect=ValueError("Groq API key not configured"),
        ),
        patch.object(analyze_review_task, "retry") as retry,
    ):
        result = analyze_review_task.apply(args=["any-id"]).get()

    assert result is None
    retry.assert_not_called()


def test_a_transient_failure_is_retried_with_backoff() -> None:
    """A provider outage schedules a retry with the back-off delay."""
    with (
        patch("app.tasks.review_tasks._run_pipeline", side_effect=_status_error(503)),
        patch.object(analyze_review_task, "retry", side_effect=RuntimeError("retry")) as retry,
    ):
        analyze_review_task.apply(args=["any-id"])

    retry.assert_called_once()
    assert 15 <= retry.call_args.kwargs["countdown"] <= 20


def test_the_last_transient_failure_ends_the_task_without_a_retry() -> None:
    """With no retry left the task fails with the error and logs that it gave up."""
    error = _status_error(503)
    with (
        patch("app.tasks.review_tasks._run_pipeline", side_effect=error),
        patch.object(analyze_review_task, "retry") as retry,
        patch("app.tasks.review_tasks.logger") as logger,
    ):
        result = analyze_review_task.apply(args=["any-id"], retries=MAX_RETRIES)

    retry.assert_not_called()
    # The eager result carries a rebuilt copy of the error, not the object.
    assert result.failed()
    assert isinstance(result.result, httpx.HTTPError)
    logger.warning.assert_not_called()
    assert "giving up" in logger.error.call_args.args[0]


def test_a_provider_hanging_past_the_soft_limit_is_transient() -> None:
    """A hung provider call is cut by the soft time limit and retried."""
    assert is_transient(SoftTimeLimitExceeded()) is True


def test_a_retry_does_not_analyse_the_review_again(db_session: Session) -> None:
    """Only the failed draft step is redone; the stored analysis is kept."""
    review = create_review(db_session)
    review.analyzed_at_utc = review.created_at_utc
    review.rating = 2
    db_session.commit()

    with (
        patch("app.tasks.review_tasks.SessionLocal", return_value=db_session),
        patch("app.services.review_ai_service.ReviewAiService.analyze") as analyze,
    ):
        result = asyncio.run(_run_pipeline(review.id))

    assert result == review.id
    analyze.assert_not_called()
    db_session.expire_all()
    stored = db_session.get(Review, review.id)
    assert stored is not None
    assert stored.rating == 2
    assert stored.ai_draft_response is not None


def test_the_sweep_requeues_only_old_reviews_without_an_analysis(db_session: Session) -> None:
    """A lost review goes back on the queue; fresh and finished ones do not."""
    lost = create_review(db_session)
    lost.created_at_utc = utcnow() - STALE_AFTER * 2
    fresh = create_review(db_session)
    done = create_review(db_session)
    done.created_at_utc = utcnow() - STALE_AFTER * 2
    done.analyzed_at_utc = utcnow()
    done.ai_draft_response = "Thanks!"
    db_session.commit()
    lost_id = lost.id
    assert fresh.id != lost_id

    with (
        patch("app.tasks.review_tasks.SessionLocal", return_value=db_session),
        patch.object(analyze_review_task, "apply_async") as enqueue,
    ):
        assert requeue_stale_reviews_task.run() == 1

    enqueue.assert_called_once()
    assert enqueue.call_args.kwargs["args"] == [lost_id]


def _let_the_requeued_run_time_out(db_session: Session, review_id: str) -> None:
    """Move the last requeue of a review one stale period further into the past.

    Args:
        db_session: The test database session.
        review_id: The review whose requeued run should count as finished.
    """
    stored = db_session.get(Review, review_id)
    assert stored is not None
    stored.last_requeued_at_utc = utcnow() - STALE_AFTER * 2
    db_session.commit()


def test_the_sweep_gives_up_on_a_review_that_keeps_failing(db_session: Session) -> None:
    """A review that never gets analysed is requeued a few times, then left alone."""
    hopeless = create_review(db_session)
    hopeless.created_at_utc = utcnow() - STALE_AFTER * 2
    db_session.commit()
    hopeless_id = hopeless.id

    rounds: list[int] = []
    with (
        patch("app.tasks.review_tasks.SessionLocal", return_value=db_session),
        patch.object(analyze_review_task, "apply_async") as enqueue,
    ):
        for _ in range(MAX_REQUEUES + 2):
            rounds.append(requeue_stale_reviews_task.run())
            _let_the_requeued_run_time_out(db_session, hopeless_id)

    assert rounds == [1] * MAX_REQUEUES + [0, 0]
    assert enqueue.call_count == MAX_REQUEUES
    stored = db_session.get(Review, hopeless_id)
    assert stored is not None
    assert stored.analysis_requeues == MAX_REQUEUES


def test_the_sweep_waits_for_the_requeued_run(db_session: Session) -> None:
    """An old review is not queued again while its requeued run may still be retrying."""
    old = create_review(db_session)
    old.created_at_utc = utcnow() - STALE_AFTER * 6
    db_session.commit()

    with (
        patch("app.tasks.review_tasks.SessionLocal", return_value=db_session),
        patch.object(analyze_review_task, "apply_async") as enqueue,
    ):
        rounds = [requeue_stale_reviews_task.run() for _ in range(3)]

    assert rounds == [1, 0, 0]
    enqueue.assert_called_once()


@pytest.mark.parametrize("error", [KombuOperationalError("broker down"), OSError("socket closed")])
def test_broker_outages_do_not_spend_the_sweeps_retry_budget(db_session: Session, error: Exception) -> None:
    """A broker outage lasting several sweeps leaves every review recoverable."""
    review_ids = [create_review(db_session).id for _ in range(2)]
    for review_id in review_ids:
        review = db_session.get(Review, review_id)
        assert review is not None
        review.created_at_utc = utcnow() - STALE_AFTER * 2
    db_session.commit()

    with (
        patch("app.tasks.review_tasks.SessionLocal", return_value=db_session),
        patch.object(analyze_review_task, "apply_async", side_effect=error) as enqueue,
    ):
        for _ in range(MAX_REQUEUES + 1):
            assert requeue_stale_reviews_task.run() == 0

    assert enqueue.call_count == len(review_ids) * (MAX_REQUEUES + 1)
    for review_id in review_ids:
        review = db_session.get(Review, review_id)
        assert review is not None
        assert review.analysis_requeues == 0
        assert review.last_requeued_at_utc is None

    with (
        patch("app.tasks.review_tasks.SessionLocal", return_value=db_session),
        patch.object(analyze_review_task, "apply_async") as recovered_enqueue,
    ):
        assert requeue_stale_reviews_task.run() == len(review_ids)

    assert {call.kwargs["args"][0] for call in recovered_enqueue.call_args_list} == set(review_ids)
    for review_id in review_ids:
        review = db_session.get(Review, review_id)
        assert review is not None
        assert review.analysis_requeues == 1
        assert review.last_requeued_at_utc is not None


def test_a_failed_publication_does_not_lose_the_rest_of_the_sweep_batch(db_session: Session) -> None:
    """Only successfully published reviews spend a requeue allowance."""
    review_ids = [create_review(db_session).id for _ in range(2)]
    for review_id in review_ids:
        review = db_session.get(Review, review_id)
        assert review is not None
        review.created_at_utc = utcnow() - STALE_AFTER * 2
    db_session.commit()

    with (
        patch("app.tasks.review_tasks.SessionLocal", return_value=db_session),
        patch.object(
            analyze_review_task, "apply_async", side_effect=[KombuOperationalError("broker down"), None]
        ) as enqueue,
    ):
        assert requeue_stale_reviews_task.run() == 1

    failed_id, published_id = [call.kwargs["args"][0] for call in enqueue.call_args_list]
    failed = db_session.get(Review, failed_id)
    published = db_session.get(Review, published_id)
    assert failed is not None
    assert published is not None
    assert failed.analysis_requeues == 0
    assert failed.last_requeued_at_utc is None
    assert published.analysis_requeues == 1
    assert published.last_requeued_at_utc is not None
