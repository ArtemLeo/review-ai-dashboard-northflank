"""Groq draft response generator using its OpenAI-compatible chat completions API."""

from app.ai.openai_compatible import OpenAiCompatibleResponseGenerator
from app.core.config import settings


class GroqResponseGenerator(OpenAiCompatibleResponseGenerator):
    """Groq draft response generator using its OpenAI-compatible chat completions API."""

    PROVIDER_NAME = "Groq"
    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self) -> None:
        """Initialize the provider from the application settings."""
        super().__init__(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            instructions_file=settings.response_instructions_file,
        )
