"""Deterministic stub implementation of review analyzer for offline testing."""

import re

from app.ai.analyzer import IAiReviewAnalyzer
from app.models.review import Priority, Rating, ReviewCategory
from app.schemas.ai import AiReviewAnalysisRequest, AiReviewAnalysisResult

#: Frequent short words that tell the Latin-script languages apart.  Words
#: shared by several of them ("la", "con", "non") are left out on purpose.
_LATIN_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset({"the", "and", "is", "it", "to", "of", "with", "but", "very"}),
    "es": frozenset({"el", "los", "las", "que", "es", "y", "pero", "muy", "del"}),
    "fr": frozenset({"le", "les", "des", "est", "et", "avec", "mais", "très", "une"}),
    "de": frozenset({"der", "die", "das", "und", "ist", "mit", "aber", "sehr", "nicht"}),
    "it": frozenset({"il", "gli", "della", "che", "è", "e", "ma", "molto", "sono"}),
    "pl": frozenset({"jest", "się", "nie", "ale", "bardzo", "w", "z", "na", "to"}),
}

#: Letters that only one of those languages uses; each one weighs like a word.
_LATIN_LETTERS: dict[str, str] = {
    "es": "ñ¿¡",
    "fr": "çœâêîôûëïÿ",
    "de": "ßäö",
    "it": "ìò",
    "pl": "ąćęłńśźż",
}

_WORD = re.compile(r"[^\W\d_]+")


class StubAiReviewAnalyzer(IAiReviewAnalyzer):
    """Deterministic analyzer using keyword matching without external API calls."""

    PROVIDER_NAME = "Stub"
    MODEL_NAME = "deterministic-v1"

    async def analyze(self, request: AiReviewAnalysisRequest) -> AiReviewAnalysisResult:
        """Analyze review text using rule-based keyword matching.

        Args:
            request: The review analysis request containing raw text.

        Returns:
            Deterministic analysis result with determined rating, priority, and category.
        """
        normalized_text = request.review_text.strip().lower()

        is_payment_issue = self._contains_any(
            normalized_text,
            [
                "payment",
                "refund",
                "invoice",
                "charge",
                "deposit",
                "withdraw",
                "trade offer",
                "оплат",
                "повернен",
                "депозит",
                "вивід",
                "вывод",
            ],
        )
        is_bug = self._contains_any(normalized_text, ["bug", "error", "broken", "crash", "помил", "не працю"])
        is_support = self._contains_any(normalized_text, ["support", "help", "підтрим", "допомог"])
        is_feature_request = self._contains_any(
            normalized_text, ["feature", "request", "would like", "хотілося", "додайте"]
        )
        is_urgent = self._contains_any(normalized_text, ["urgent", "immediately", "asap", "терміново", "негайно"])
        is_negative = (
            is_payment_issue
            or is_bug
            or self._contains_any(normalized_text, ["bad", "terrible", "disappointed", "погано", "жахливо"])
        )
        is_positive = self._contains_any(normalized_text, ["great", "excellent", "thank", "love", "чудово", "дякую"])

        # Simple language detection for stub
        language_code = self._detect_language(normalized_text)

        # Determine category
        if is_payment_issue:
            category = ReviewCategory.PAYMENT_ISSUE
        elif is_bug:
            category = ReviewCategory.BUG
        elif is_support:
            category = ReviewCategory.SUPPORT
        elif is_feature_request:
            category = ReviewCategory.FEATURE_REQUEST
        elif is_positive:
            category = ReviewCategory.PRAISE
        else:
            category = ReviewCategory.OTHER

        # Determine priority
        needs_attention = is_urgent or is_payment_issue or is_bug or is_negative
        priority = Priority.HIGH if needs_attention else Priority.MEDIUM

        # Determine rating (1-5 stars)
        if is_negative:
            rating = Rating.ONE
        elif is_positive:
            rating = Rating.FIVE
        else:
            rating = Rating.THREE

        return AiReviewAnalysisResult(
            rating=rating,
            priority=priority,
            category=category,
            needs_urgent_response=is_urgent,
            language_code=language_code,
            provider_name=self.PROVIDER_NAME,
            model_name=self.MODEL_NAME,
        )

    def _contains_any(self, text: str, terms: list[str]) -> bool:
        """Check if any term in the provided list is a substring of text."""
        return any(term in text for term in terms)

    def _detect_language(self, text: str) -> str:
        """Simple rule-based language detection for stub analyzer.

        Scripts are told apart by their characters.  Within Cyrillic, the
        letters only Ukrainian uses decide between Ukrainian and Russian.  The
        Latin-script languages are scored by their frequent short words and
        their own letters; a text without any clue is taken as English.

        Args:
            text: Normalized review text.

        Returns:
            ISO 639-1 language code.
        """
        # Japanese mixes kana into its kanji, so it is checked before Chinese.
        if any("\u3040" <= char <= "\u30ff" for char in text):
            return "ja"
        if any("\u4e00" <= char <= "\u9fff" for char in text):
            return "zh"
        if any("\u0400" <= char <= "\u04ff" for char in text):
            return "uk" if any(char in text for char in "іїєґ") else "ru"

        words = _WORD.findall(text)
        scores = {
            language: sum(word in stopwords for word in words)
            + sum(char in _LATIN_LETTERS.get(language, "") for char in text)
            for language, stopwords in _LATIN_STOPWORDS.items()
        }
        best = max(scores, key=lambda language: scores[language])
        return best if scores[best] > 0 else "en"
