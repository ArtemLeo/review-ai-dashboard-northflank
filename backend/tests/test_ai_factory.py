"""Tests for the AI provider factory and the provider selection rules."""

from app.ai.factory import (
    _configured_provider,
    _resolve_analyzer,
    _resolve_response_generator,
    get_response_generator,
    get_review_analyzer,
)
from app.ai.gemini_analyzer import GeminiReviewAnalyzer
from app.ai.groq_analyzer import GroqReviewAnalyzer
from app.ai.stub_analyzer import StubAiReviewAnalyzer
from app.ai.stub_response_generator import StubAiResponseGenerator
from app.core.config import settings


def test_configured_provider_normalises_case_and_whitespace() -> None:
    """The provider identifier is lower-cased and trimmed."""
    original = settings.ai_provider
    try:
        settings.ai_provider = "  GROQ  "
        assert _configured_provider() == "groq"

        settings.ai_provider = "Stub"
        assert _configured_provider() == "stub"
    finally:
        settings.ai_provider = original


def test_configured_provider_falls_back_to_auto() -> None:
    """An unknown provider identifier resolves to the automatic chain."""
    original = settings.ai_provider
    try:
        settings.ai_provider = "not-a-provider"
        assert _configured_provider() == "auto"

        settings.ai_provider = ""
        assert _configured_provider() == "auto"
    finally:
        settings.ai_provider = original


def test_auto_mode_without_keys_returns_the_stub() -> None:
    """Without any API key the offline stub implementation is used."""
    original_provider = settings.ai_provider
    original_groq = settings.groq_api_key
    original_gemini = settings.gemini_api_key
    try:
        settings.ai_provider = "auto"
        settings.groq_api_key = ""
        settings.gemini_api_key = ""

        assert isinstance(get_review_analyzer(), StubAiReviewAnalyzer)
        assert isinstance(get_response_generator(), StubAiResponseGenerator)
    finally:
        settings.ai_provider = original_provider
        settings.groq_api_key = original_groq
        settings.gemini_api_key = original_gemini


def test_auto_mode_prefers_groq_when_the_key_is_present() -> None:
    """In automatic mode the Groq provider wins when its key is configured."""
    original_provider = settings.ai_provider
    original_groq = settings.groq_api_key
    original_gemini = settings.gemini_api_key
    try:
        settings.ai_provider = "auto"
        settings.groq_api_key = "test-key"
        settings.gemini_api_key = "test-key"

        assert isinstance(get_review_analyzer(), GroqReviewAnalyzer)
        assert get_review_analyzer().PROVIDER_NAME == "Groq"
    finally:
        settings.ai_provider = original_provider
        settings.groq_api_key = original_groq
        settings.gemini_api_key = original_gemini


def test_explicit_groq_without_key_falls_back_to_the_stub() -> None:
    """An explicitly configured Groq without a key ends up at the stub."""
    original_provider = settings.ai_provider
    original_groq = settings.groq_api_key
    try:
        settings.ai_provider = "groq"
        settings.groq_api_key = ""

        assert isinstance(_resolve_analyzer("groq"), StubAiReviewAnalyzer)
        assert isinstance(_resolve_response_generator("groq"), StubAiResponseGenerator)
    finally:
        settings.ai_provider = original_provider
        settings.groq_api_key = original_groq


def test_explicit_groq_with_key_returns_groq() -> None:
    """An explicitly configured Groq with a key returns the Groq provider."""
    original_provider = settings.ai_provider
    original_groq = settings.groq_api_key
    try:
        settings.ai_provider = "groq"
        settings.groq_api_key = "test-key"

        analyzer = _resolve_analyzer("groq")
        assert isinstance(analyzer, GroqReviewAnalyzer)
        assert analyzer.api_key == "test-key"
    finally:
        settings.ai_provider = original_provider
        settings.groq_api_key = original_groq


def test_explicit_gemini_without_key_falls_back_to_the_stub() -> None:
    """An explicitly configured Gemini without a key ends up at the stub."""
    original_provider = settings.ai_provider
    original_gemini = settings.gemini_api_key
    try:
        settings.ai_provider = "gemini"
        settings.gemini_api_key = ""

        assert isinstance(_resolve_analyzer("gemini"), StubAiReviewAnalyzer)
        assert isinstance(_resolve_response_generator("gemini"), StubAiResponseGenerator)
    finally:
        settings.ai_provider = original_provider
        settings.gemini_api_key = original_gemini


def test_explicit_gemini_with_key_returns_gemini() -> None:
    """An explicitly configured Gemini with a key returns the Gemini provider."""
    original_provider = settings.ai_provider
    original_gemini = settings.gemini_api_key
    try:
        settings.ai_provider = "gemini"
        settings.gemini_api_key = "test-key"

        assert isinstance(_resolve_analyzer("gemini"), GeminiReviewAnalyzer)
    finally:
        settings.ai_provider = original_provider
        settings.gemini_api_key = original_gemini


def test_stub_provider_is_always_selectable() -> None:
    """The stub implementation is selected explicitly and never needs a key."""
    original_provider = settings.ai_provider
    try:
        settings.ai_provider = "stub"

        assert isinstance(get_review_analyzer(), StubAiReviewAnalyzer)
        assert isinstance(get_response_generator(), StubAiResponseGenerator)
    finally:
        settings.ai_provider = original_provider
