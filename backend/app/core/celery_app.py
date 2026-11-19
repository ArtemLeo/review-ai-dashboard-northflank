"""Celery application used to run the AI analysis pipeline in the background.

The submission endpoint enqueues a task and returns without calling the AI
provider.  A Celery worker picks the task up, performs the analysis and writes
the result back to the database.  Explicit draft regeneration in the admin
API calls the provider synchronously instead.

Redis is the message broker, and no task result is stored (see
``task_ignore_result``), so a single Redis addon covers the whole queue
infrastructure; the worker runs as its own service from the same image.
"""

from celery import Celery

from app.core.config import settings

#: Name of the queue the review analysis tasks are routed to.
REVIEW_QUEUE = "reviews"

celery_app = Celery(
    "review_ai_dashboard",
    broker=settings.redis_url,
    include=["app.tasks.review_tasks"],
)

#: How often the sweep for reviews without an analysis runs, in seconds.
REQUEUE_INTERVAL_SECONDS = 300

celery_app.conf.update(
    # The worker runs with an embedded beat scheduler (``--beat``) that
    # periodically puts reviews which lost their analysis back on the queue.
    beat_schedule={
        "requeue-stale-reviews": {
            "task": "reviews.requeue_stale",
            "schedule": REQUEUE_INTERVAL_SECONDS,
        },
    },
    # Serialise the payloads as JSON so the broker stays readable.
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # A redelivered task preserves the stored analysis and regenerates the
    # draft, so it can safely be acknowledged after it finishes.  A worker
    # killed mid-task (OOM, SIGKILL, hard time limit) hands it back to the
    # queue instead of losing it.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue=REVIEW_QUEUE,
    # Hard limit: a hung provider call must not block the worker forever.
    task_time_limit=120,
    task_soft_time_limit=100,
    # The API never waits for a task result — it only enqueues the work and
    # returns the stored review — so no result backend is configured, and
    # this setting keeps the results off even if one is added later.
    task_ignore_result=True,
    # A broker outage must not block the HTTP request that enqueues the
    # task.  Without these settings the Kombu transport retries the
    # connection twenty times with a growing backoff, which held the
    # submission endpoint for almost twenty seconds and exhausted the
    # request thread pool, and Celery's own publish retry adds three more
    # attempts (about five seconds).  The task is now published at most
    # once and gives up after a second, so the review is stored and the
    # client gets its answer right away; the requeue sweep picks it up later.
    task_publish_retry=False,
    broker_transport_options={
        "max_retries": 0,
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
    },
    # After a connection is established, the worker waits out Redis restarts
    # with unlimited reconnect attempts.  Its initial connection fails fast,
    # so the hosting platform can restart a worker whose broker is not ready.
    broker_connection_max_retries=None,
    broker_connection_retry_on_startup=False,
)
