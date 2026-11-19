"""Pydantic schemas and DTOs for customer reviews."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.review import AnalysisStatus, Priority, Rating, ReviewCategory

#: Longest review text the API accepts.
#:
#: A review is a short piece of feedback, so a generous limit is enough for
#: a real customer.  The bound also keeps a single request from filling the
#: disk or from costing an enormous amount of AI tokens.
MAX_REVIEW_TEXT_LENGTH: int = 10_000


class CreateReviewRequest(BaseModel):
    """Payload for submitting a new customer review."""

    author_name: str = Field(min_length=1, max_length=150, description="Name of the review author")
    email: EmailStr = Field(description="Author contact email address")
    text: str = Field(
        min_length=1,
        max_length=MAX_REVIEW_TEXT_LENGTH,
        description="Content of the customer review",
    )

    @field_validator("author_name", "text", mode="before")
    @classmethod
    def _reject_blank_text(cls, value: Any) -> Any:
        """Drop NUL characters and reject a field that only consists of whitespace.

        PostgreSQL cannot store a NUL character in a text column, so it is
        removed here instead of failing the insert with a server error.  The
        length check alone would accept a string of spaces, and the stored
        value would then be empty.  Such a field carries no information and
        is treated as a missing one.

        Args:
            value: The raw field value.

        Returns:
            The value without NUL characters and surrounding whitespace.

        Raises:
            ValueError: If nothing but whitespace remains.
        """
        if isinstance(value, str):
            trimmed: str = value.replace("\x00", "").strip()
            if not trimmed:
                raise ValueError("must not be empty")
            return trimmed
        return value


class ReviewDto(BaseModel):
    """Public customer review DTO (excludes personal data like email)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique review UUID identifier")
    author_name: str = Field(description="Author name")
    text: str = Field(description="Review text")
    language_code: str | None = Field(default=None, description="Detected language code (ISO 639-1)")
    created_at_utc: datetime = Field(description="Creation timestamp in UTC")
    analysis_status: AnalysisStatus = Field(description="Current review handling status managed by the operator")
    rating: Rating | None = Field(default=None, description="Star rating (1-5)")
    priority: Priority | None = Field(default=None, description="Assigned priority rating")
    category: ReviewCategory | None = Field(default=None, description="Feedback category")
    needs_urgent_response: bool | None = Field(
        default=None,
        description="Whether an urgent response is required",
    )
    ai_analysis_provider: str | None = Field(default=None, description="AI provider used for analysis")
    ai_analysis_model: str | None = Field(default=None, description="AI model used for analysis")
    ai_draft_response: str | None = Field(default=None, description="AI-generated draft response")
    ai_draft_response_provider: str | None = Field(
        default=None,
        description="AI provider used for response draft",
    )
    ai_draft_response_model: str | None = Field(
        default=None,
        description="AI model used for response draft",
    )
    analyzed_at_utc: datetime | None = Field(
        default=None,
        description="Timestamp when AI analysis completed",
    )


class AdminReviewDto(ReviewDto):
    """Full customer review DTO for administrators, including contact email."""

    email: str = Field(description="Author contact email address")


class ReviewQuery(BaseModel):
    """Filter and sorting parameters for querying reviews in admin area."""

    status: AnalysisStatus | None = Field(default=None, description="Filter by review handling status")
    rating: int | None = Field(default=None, ge=1, le=5, description="Filter by rating (1-5)")
    priority: Priority | None = Field(default=None, description="Filter by priority")
    sort_by: str | None = Field(default=None, description="Column name to sort by")
    descending: bool = Field(default=True, description="Whether to sort descending")


class ReviewStatistics(BaseModel):
    """Statistics for review ratings distribution."""

    rating_1: int = Field(description="Number of reviews rated 1 star")
    rating_2: int = Field(description="Number of reviews rated 2 stars")
    rating_3: int = Field(description="Number of reviews rated 3 stars")
    rating_4: int = Field(description="Number of reviews rated 4 stars")
    rating_5: int = Field(description="Number of reviews rated 5 stars")
    total: int = Field(description="Total number of reviews")
    avg_rating: float = Field(
        default=0.0,
        description="Average star rating of the analysed reviews",
    )


class PaginatedResponse(BaseModel):
    """Pagination envelope returned by the admin review list endpoint."""

    items: list[AdminReviewDto] = Field(description="List of records for the current page")
    total: int = Field(ge=0, description="Total matching items count across all pages")
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, description="Number of items per page")
    total_pages: int = Field(ge=0, description="Total number of pages")


class UpdateReviewStatusRequest(BaseModel):
    """Payload for updating the operator-managed review handling status."""

    analysis_status: AnalysisStatus = Field(description="New review handling status")
