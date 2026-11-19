"""Groq review analyzer using its OpenAI-compatible chat completions API."""

from app.ai.openai_compatible import OpenAiCompatibleAnalyzer
from app.core.config import settings


class GroqReviewAnalyzer(OpenAiCompatibleAnalyzer):
    """Groq review analyzer using its OpenAI-compatible chat completions API."""

    PROVIDER_NAME = "Groq"
    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
    SUPPORTS_JSON_MODE = True

    def __init__(self) -> None:
        """Initialize the provider from the application settings."""
        super().__init__(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            instructions_file=settings.analysis_instructions_file,
        )
