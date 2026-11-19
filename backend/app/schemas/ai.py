"""Pydantic schemas for AI analysis and response generation contracts."""

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import MAX_LANGUAGE_CODE_LENGTH
from app.models.review import Priority, Rating, ReviewCategory


class AiReviewAnalysisRequest(BaseModel):
    """Input payload to request AI analysis of a review."""

    review_text: str = Field(description="Raw text of the review to analyze")


class AiReviewAnalysisResult(BaseModel):
    """Structured result returned by an AI review analyzer."""

    model_config = ConfigDict(protected_namespaces=())

    rating: Rating = Field(description="Star rating (1-5)")
    priority: Priority = Field(description="Calculated urgency/priority level")
    category: ReviewCategory = Field(description="Categorization of the review topic")
    needs_urgent_response: bool = Field(description="Whether the review requires prompt team response")
    language_code: str = Field(
        default="en",
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        description="Detected language code (ISO 639-1)",
    )
    provider_name: str = Field(description="Name of the AI provider (e.g. Groq, Gemini, Stub)")
    model_name: str = Field(description="Specific model identifier used for analysis")


class AiResponseGenerationRequest(BaseModel):
    """Input payload to request AI draft response generation."""

    review_text: str = Field(description="Raw text of the review to respond to")
    language_code: str = Field(
        default="en",
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        description="Language code for the response (ISO 639-1)",
    )


class AiResponseGenerationResult(BaseModel):
    """Structured result containing AI-generated draft response."""

    model_config = ConfigDict(protected_namespaces=())

    draft_response: str = Field(description="Generated draft response text")
    provider_name: str = Field(description="Name of the AI provider (e.g. Groq, Gemini, Stub)")
    model_name: str = Field(description="Specific model identifier used for generation")
