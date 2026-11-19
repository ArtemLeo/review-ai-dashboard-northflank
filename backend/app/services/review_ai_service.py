"""Application service coordinating AI analysis and draft response generation for reviews."""

from sqlalchemy.orm import Session

from app.ai.analyzer import IAiReviewAnalyzer
from app.ai.response_generator import IAiResponseGenerator
from app.core.time import utcnow
from app.models.review import Review
from app.schemas.ai import AiResponseGenerationRequest, AiReviewAnalysisRequest
from app.schemas.review import AdminReviewDto


class ReviewAiService:
    """Service running the AI analysis and the draft reply and storing their results.

    It never changes the review status: that belongs to the support operator.
    """

    def __init__(
        self,
        db: Session,
        review_analyzer: IAiReviewAnalyzer,
        response_generator: IAiResponseGenerator,
    ) -> None:
        """Initialize ReviewAiService with database session and AI providers."""
        self.db = db
        self.review_analyzer = review_analyzer
        self.response_generator = response_generator

    async def analyze(self, id: str) -> AdminReviewDto | None:
        """Perform AI analysis on a review, updating rating, priority, and category.

        The analysis fills in the rating, the priority, the detected language
        and the provider metadata.  The status stays ``Pending`` — the review
        waits for a support operator to pick it up, exactly like a review
        added through a bulk script.  The operator then moves it to
        ``Processing`` while writing the reply.

        Args:
            id: Unique review UUID.

        Returns:
            Updated AdminReviewDto if review exists, otherwise None.

        Raises:
            Exception: Any error encountered during AI analysis.
        """
        review = self.db.get(Review, id)

        if not review:
            return None

        try:
            result = await self.review_analyzer.analyze(AiReviewAnalysisRequest(review_text=review.text))

            review.rating = int(result.rating.value)
            review.priority = result.priority.value
            review.category = result.category.value
            review.needs_urgent_response = result.needs_urgent_response
            review.language_code = result.language_code
            review.ai_analysis_provider = result.provider_name
            review.ai_analysis_model = result.model_name
            review.analyzed_at_utc = utcnow()

            self.db.commit()
            self.db.refresh(review)
            return self._map_to_admin_dto(review)
        except Exception:
            # Nothing was written yet, so rolling back is enough to leave
            # the review untouched and ready for another attempt.
            self.db.rollback()
            raise

    async def generate_draft_response(self, id: str) -> AdminReviewDto | None:
        """Generate an AI draft response for a review and save it to the database.

        Args:
            id: Unique review UUID.

        Returns:
            Updated AdminReviewDto if review exists, otherwise None.

        Raises:
            Exception: Any error encountered while generating the draft.
        """
        review = self.db.get(Review, id)

        if not review:
            return None

        try:
            result = await self.response_generator.generate(
                AiResponseGenerationRequest(review_text=review.text, language_code=review.language_code or "en")
            )

            review.ai_draft_response = result.draft_response
            review.ai_draft_response_provider = result.provider_name
            review.ai_draft_response_model = result.model_name

            self.db.commit()
            self.db.refresh(review)
            return self._map_to_admin_dto(review)
        except Exception:
            # The session may hold a half-finished transaction.  Rolling
            # back leaves the already stored analysis intact and releases the
            # connection for the next attempt.
            self.db.rollback()
            raise

    @staticmethod
    def _map_to_admin_dto(review: Review) -> AdminReviewDto:
        """Map a SQLAlchemy Review model to AdminReviewDto."""
        return AdminReviewDto.model_validate(review)
