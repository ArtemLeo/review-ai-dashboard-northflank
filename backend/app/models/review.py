"""Database model and domain enumeration definitions for customer reviews."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.time import utcnow
from app.db.base_class import Base


class AnalysisStatus(str, Enum):
    """Review handling status managed manually by the support operator."""

    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"


class Rating(int, Enum):
    """Star rating for customer reviews (1-5 stars)."""

    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class Priority(str, Enum):
    """Urgency / business priority rating of a review."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ReviewCategory(str, Enum):
    """Categorization domain for feedback."""

    PRAISE = "Praise"
    FEATURE_REQUEST = "FeatureRequest"
    BUG = "Bug"
    PAYMENT_ISSUE = "PaymentIssue"
    SUPPORT = "Support"
    OTHER = "Other"


#: SQL condition of a review that still lacks its analysis or its draft.
UNANALYSED_CONDITION = "analyzed_at_utc IS NULL OR ai_draft_response IS NULL"


class Review(Base):
    """SQLAlchemy model representing a customer review and its AI analysis metadata."""

    __tablename__ = "reviews"

    __table_args__ = (
        # The admin list filters on the status and sorts by the creation
        # date, so the combination is covered by a dedicated composite index.
        Index("ix_reviews_status_created_at", "analysis_status", "created_at_utc"),
        # The sweep that requeues reviews without an analysis looks only at
        # the unfinished rows, so a partial index keeps it cheap.
        Index(
            "ix_reviews_unanalysed_created_at",
            "created_at_utc",
            postgresql_where=text(UNANALYSED_CONDITION),
            sqlite_where=text(UNANALYSED_CONDITION),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    author_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # The application fills the UTC time itself, so the value never depends
    # on the database server's time zone; the server default only covers
    # rows inserted by hand.
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    analysis_status: Mapped[str] = mapped_column(
        String(50),
        default=AnalysisStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    needs_urgent_response: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_analysis_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_analysis_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_draft_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_draft_response_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_draft_response_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    analyzed_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    #: How many times the background sweep has put this review back on the
    #: queue.  The sweep gives up after a few rounds, so a review that can
    #: never be analysed (a missing API key, a provider that always rejects
    #: it) does not burn quota forever.
    analysis_requeues: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    #: When the sweep last put this review back on the queue.  The next
    #: requeue waits a full stale period from here, so it never overlaps a
    #: run that is still being retried.
    last_requeued_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
