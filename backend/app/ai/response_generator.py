"""Response generator contract interface."""

from abc import ABC, abstractmethod

from app.schemas.ai import AiResponseGenerationRequest, AiResponseGenerationResult


class IAiResponseGenerator(ABC):
    """Abstract base class defining interface for AI customer response generators."""

    @abstractmethod
    async def generate(self, request: AiResponseGenerationRequest) -> AiResponseGenerationResult:
        """Generate a draft customer support response based on review text.

        Args:
            request: The generation request containing the customer review text.

        Returns:
            Structured AI response result containing the draft response text.
        """
