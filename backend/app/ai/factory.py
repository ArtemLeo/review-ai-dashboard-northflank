"""Factory for instantiating AI review analyzer and response generator providers."""

from collections.abc import Callable
from typing import TypeVar

from app.ai.analyzer import IAiReviewAnalyzer
from app.ai.gemini_analyzer import GeminiReviewAnalyzer
from app.ai.gemini_response_generator import GeminiResponseGenerator
from app.ai.groq_analyzer import GroqReviewAnalyzer
from app.ai.groq_response_generator import GroqResponseGenerator
from app.ai.response_generator import IAiResponseGenerator
from app.ai.stub_analyzer import StubAiReviewAnalyzer
from app.ai.stub_response_generator import StubAiResponseGenerator
from app.core.config import settings

_T = TypeVar("_T")

#: Provider identifiers accepted by the ``AI_PROVIDER`` setting.
_PROVIDER_STUB = "stub"
_PROVIDER_GROQ = "groq"
_PROVIDER_GEMINI = "gemini"
_PROVIDER_AUTO = "auto"


def _configured_provider() -> str:
    """Return the normalised provider identifier from the configuration.

    Returns:
        One of ``"stub"``, ``"groq"``, ``"gemini"`` or ``"auto"``.
    """
    provider: str = (settings.ai_provider or _PROVIDER_AUTO).strip().lower()
    if provider in {_PROVIDER_STUB, _PROVIDER_GROQ, _PROVIDER_GEMINI}:
        return provider
    return _PROVIDER_AUTO


def _resolve(
    provider: str,
    groq: Callable[[], _T],
    gemini: Callable[[], _T],
    stub: Callable[[], _T],
) -> _T:
    """Pick and instantiate the provider matching the resolved identifier.

    An explicitly configured provider without its API key falls back to the
    offline stub implementation.

    Args:
        provider: Normalised provider identifier.
        groq: Constructor for the Groq implementation.
        gemini: Constructor for the Gemini implementation.
        stub: Constructor for the offline stub.

    Returns:
        A configured provider instance.
    """
    if provider == _PROVIDER_GROQ and settings.groq_api_key:
        return groq()
    if provider == _PROVIDER_GEMINI and settings.gemini_api_key:
        return gemini()
    if provider == _PROVIDER_AUTO:
        if settings.groq_api_key:
            return groq()
        if settings.gemini_api_key:
            return gemini()
    return stub()


def _resolve_analyzer(provider: str) -> IAiReviewAnalyzer:
    """Instantiate the analyzer matching the resolved provider.

    Args:
        provider: Normalised provider identifier.

    Returns:
        A configured analyzer instance.
    """
    return _resolve(provider, GroqReviewAnalyzer, GeminiReviewAnalyzer, StubAiReviewAnalyzer)


def _resolve_response_generator(provider: str) -> IAiResponseGenerator:
    """Instantiate the response generator matching the resolved provider.

    Args:
        provider: Normalised provider identifier.

    Returns:
        A configured response generator instance.
    """
    return _resolve(provider, GroqResponseGenerator, GeminiResponseGenerator, StubAiResponseGenerator)


def get_review_analyzer() -> IAiReviewAnalyzer:
    """Return the review analyzer configured by ``AI_PROVIDER``.

    ``auto`` picks by the configured keys: Groq, then Gemini, then the offline
    stub.  A failing provider is never swapped for another one.

    Returns:
        Configured implementation of IAiReviewAnalyzer (Groq, Gemini, or Stub).
    """
    return _resolve_analyzer(_configured_provider())


def get_response_generator() -> IAiResponseGenerator:
    """Return the response generator configured by ``AI_PROVIDER``.

    ``auto`` picks by the configured keys: Groq, then Gemini, then the offline
    stub.

    Returns:
        Configured implementation of IAiResponseGenerator (Groq, Gemini, or Stub).
    """
    return _resolve_response_generator(_configured_provider())
