"""Liveness and readiness probes for container orchestrators."""

from typing import Literal

import redis
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.redis_client import create_redis_client
from app.db.session import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["system"])

CheckResult = Literal["ok", "unavailable"]

_redis_client: redis.Redis | None = None


class ReadinessReport(BaseModel):
    """Result of the readiness probe, one entry per dependency."""

    status: Literal["ready", "degraded"] = Field(description="Overall readiness")
    database: CheckResult = Field(description="PostgreSQL connectivity")
    redis: CheckResult = Field(description="Redis (queue, rate limits) connectivity")


def ping_redis() -> bool:
    """Return whether Redis answers a PING (a seam for the tests)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client(settings.redis_url)
    try:
        return bool(_redis_client.ping())
    except redis.RedisError as exc:
        logger.warning("Readiness: Redis is unavailable: %s", exc)
        return False


def _database_ok(db: Session) -> bool:
    """Return whether the database answers a trivial query."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("Readiness: database is unavailable: %s", exc)
        return False


@router.get("")
def liveness() -> dict[str, str]:
    """Report that the process is up; checks no dependency, so it is cheap."""
    return {"status": "healthy"}


@router.get("/ready", response_model=ReadinessReport)
def readiness(
    response: Response,
    db: Session = Depends(get_db),
    redis_ok: bool = Depends(ping_redis),
) -> ReadinessReport:
    """Check the database and Redis; answer 503 when either is down.

    Args:
        response: The response whose status code is set to 503 on failure.
        db: A database session.
        redis_ok: Result of the Redis ping.

    Returns:
        The per-dependency report.
    """
    database_ok = _database_ok(db)
    ready = database_ok and redis_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessReport(
        status="ready" if ready else "degraded",
        database="ok" if database_ok else "unavailable",
        redis="ok" if redis_ok else "unavailable",
    )
