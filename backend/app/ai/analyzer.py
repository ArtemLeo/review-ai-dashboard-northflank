"""Review analyzer contract interface."""

from abc import ABC, abstractmethod

from app.schemas.ai import AiReviewAnalysisRequest, AiReviewAnalysisResult


class IAiReviewAnalyzer(ABC):
    """Abstract base class defining interface for review analysis providers."""

    @abstractmethod
    async def analyze(self, request: AiReviewAnalysisRequest) -> AiReviewAnalysisResult:
        """Analyze review text and return structured analysis result.

        Args:
            request: The review analysis request containing raw text.

        Returns:
            Structured AI analysis result with rating, priority, and category.
        """
