"""Deterministic stub customer response generator for offline testing."""

from typing import ClassVar

from app.ai.response_generator import IAiResponseGenerator
from app.schemas.ai import AiResponseGenerationRequest, AiResponseGenerationResult


class StubAiResponseGenerator(IAiResponseGenerator):
    """Deterministic response generator returning fixed polite customer support replies."""

    PROVIDER_NAME = "Stub"
    MODEL_NAME = "deterministic-v1"

    # One fixed reply per language, used while no AI key is configured.
    DRAFT_RESPONSES: ClassVar[dict[str, str]] = {
        "en": "Thank you for your feedback! We appreciate your input and will look into this matter.",
        "es": "Gracias por sus comentarios. Apreciamos su opinión y investigaremos este asunto.",
        "de": "Vielen Dank für Ihr Feedback. Wir schätzen Ihre Meinung und werden uns diesem Thema widmen.",
        "fr": "Merci pour vos commentaires. Nous apprécions votre avis et examinerons cette question.",
        "ru": "Спасибо за ваш отзыв! Мы ценим ваше мнение и рассмотрим этот вопрос.",
        "ja": "フィードバックありがとうございます。ご意見を感謝し、この問題を調査します。",
        "zh": "感谢您的反馈！我们感谢您的意见并将调查此事。",
        "it": "Grazie per il tuo feedback. Apprezziamo il tuo parere ed esamineremo questa questione.",
        "pl": "Dziękujemy za opinię. Doceniamy Twój głos i zbadamy tę sprawę.",
        "uk": "Дякуємо за ваш відгук! Ми цінуємо вашу думку і розглянемо це питання.",
    }

    async def generate(self, request: AiResponseGenerationRequest) -> AiResponseGenerationResult:
        """Generate a deterministic customer response draft.

        Args:
            request: The generation request containing the review text and language code.

        Returns:
            Pre-defined polite customer response result in the appropriate language.
        """
        language_code = request.language_code or "en"
        draft = self.DRAFT_RESPONSES.get(language_code, self.DRAFT_RESPONSES["en"])

        return AiResponseGenerationResult(
            draft_response=draft,
            provider_name=self.PROVIDER_NAME,
            model_name=self.MODEL_NAME,
        )
