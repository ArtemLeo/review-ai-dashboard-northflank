"""Google Gemini review analyzer using its OpenAI-compatible endpoint."""

from app.ai.openai_compatible import OpenAiCompatibleAnalyzer
from app.core.config import settings


class GeminiReviewAnalyzer(OpenAiCompatibleAnalyzer):
    """Google Gemini review analyzer using its OpenAI-compatible endpoint."""

    PROVIDER_NAME = "Gemini"
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    SUPPORTS_JSON_MODE = False

    def __init__(self) -> None:
        """Initialize the provider from the application settings."""
        super().__init__(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            instructions_file=settings.analysis_instructions_file,
        )
