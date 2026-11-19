"""Tests for the AI analysis service and the offline stub providers."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.analyzer import IAiReviewAnalyzer
from app.ai.stub_analyzer import StubAiReviewAnalyzer
from app.ai.stub_response_generator import StubAiResponseGenerator
from app.models.review import AnalysisStatus, Review
from app.schemas.ai import (
    AiReviewAnalysisRequest,
    AiReviewAnalysisResult,
)
from app.services.review_ai_service import ReviewAiService
from tests.factories import create_review


class FailingAnalyzer(IAiReviewAnalyzer):
    """Analyzer double that always fails, to exercise the error path."""

    PROVIDER_NAME = "Failing"

    async def analyze(self, request: AiReviewAnalysisRequest) -> AiReviewAnalysisResult:
        """Always raise, simulating an unreachable provider.

        Args:
            request: The review analysis request.

        Raises:
            RuntimeError: Always.
        """
        raise RuntimeError("provider is unreachable")


#: A review the stub analyser reads as a payment problem.
_PAYMENT_REVIEW = "My payment was charged twice, I need a refund."


@pytest.mark.asyncio
async def test_analysis_stores_the_result_and_keeps_the_review_pending(
    db_session: Session,
) -> None:
    """A successful analysis stores the result and keeps the review pending.

    The status belongs to the support operator, who moves the review to
    "Processing" while writing the reply.
    """
    review = create_review(db_session, _PAYMENT_REVIEW)
    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )

    dto = await service.analyze(review.id)

    assert dto is not None
    assert dto.analysis_status == AnalysisStatus.PENDING
    assert dto.rating is not None
    assert dto.priority is not None
    assert dto.category is not None
    assert dto.ai_analysis_provider == "Stub"
    assert dto.analyzed_at_utc is not None


@pytest.mark.asyncio
async def test_failed_analysis_keeps_the_status_pending(
    db_session: Session,
) -> None:
    """A failing provider leaves the review in the pending state."""
    review = create_review(db_session, _PAYMENT_REVIEW)
    service = ReviewAiService(
        db_session,
        FailingAnalyzer(),
        StubAiResponseGenerator(),
    )

    with pytest.raises(RuntimeError):
        await service.analyze(review.id)

    db_session.expire_all()
    stored = db_session.execute(select(Review).where(Review.id == review.id)).scalar_one()
    assert stored.analysis_status == AnalysisStatus.PENDING.value
    assert stored.rating is None
    assert stored.ai_analysis_provider is None


@pytest.mark.asyncio
async def test_analysis_of_a_missing_review_returns_none(
    db_session: Session,
) -> None:
    """Analysing an unknown review id is a no-op."""
    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )

    assert await service.analyze("does-not-exist") is None


@pytest.mark.asyncio
async def test_draft_response_is_stored(db_session: Session) -> None:
    """The generated draft response is persisted on the review."""
    review = create_review(db_session, _PAYMENT_REVIEW)
    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )

    dto = await service.generate_draft_response(review.id)

    assert dto is not None
    assert dto.ai_draft_response is not None
    assert dto.ai_draft_response_provider == "Stub"


@pytest.mark.asyncio
async def test_draft_response_of_a_missing_review_returns_none(
    db_session: Session,
) -> None:
    """Generating a draft for an unknown review id is a no-op."""
    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )

    assert await service.generate_draft_response("does-not-exist") is None


@pytest.mark.asyncio
async def test_stub_analyzer_detects_a_payment_issue(
    db_session: Session,
) -> None:
    """The stub analyzer classifies a payment complaint as a high priority."""
    review = create_review(db_session, _PAYMENT_REVIEW)
    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )

    dto = await service.analyze(review.id)

    assert dto is not None
    assert dto.category == "PaymentIssue"
    assert dto.priority == "High"
    assert dto.rating == 1


@pytest.mark.asyncio
async def test_stub_analyzer_detects_praise(db_session: Session) -> None:
    """The stub analyzer classifies a positive review as praise."""
    review = Review(
        author_name="Test User",
        email="test@example.com",
        text="Great product, thank you so much, I love it!",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )

    dto = await service.analyze(review.id)

    assert dto is not None
    assert dto.category == "Praise"
    assert dto.rating == 5


@pytest.mark.asyncio
async def test_stub_response_generator_follows_the_review_language(
    db_session: Session,
) -> None:
    """The stub generator answers in the language of the review."""
    review = Review(
        author_name="Test User",
        email="test@example.com",
        text="Дякую за чудовий сервіс!",
        language_code="uk",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    service = ReviewAiService(
        db_session,
        StubAiReviewAnalyzer(),
        StubAiResponseGenerator(),
    )

    dto = await service.generate_draft_response(review.id)

    assert dto is not None
    assert dto.ai_draft_response == StubAiResponseGenerator.DRAFT_RESPONSES["uk"]


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Great game! The new update improved matchmaking.", "en"),
        ("Чудова гра! Нове оновлення значно покращило матчмейкінг.", "uk"),
        ("Отличная игра! Новое обновление улучшило матчмейкинг.", "ru"),
        ("¡Excelente juego! La nueva actualización mejoró el emparejamiento.", "es"),
        ("Excellent jeu! La nouvelle mise à jour a amélioré le matchmaking.", "fr"),
        ("Tolles Spiel! Das neue Update hat das Matchmaking verbessert.", "de"),
        ("Ottimo gioco! Il nuovo aggiornamento ha migliorato il matchmaking.", "it"),
        ("Świetna gra! Nowa aktualizacja znacząco poprawiła matchmaking.", "pl"),
        ("很棒的游戏！新更新显著改善了匹配。", "zh"),
        ("素晴らしいゲーム！新しいアップデートでマッチメイキングが改善されました。", "ja"),
    ],
)
@pytest.mark.asyncio
async def test_stub_analyzer_detects_the_language(text: str, language: str) -> None:
    """The offline analyzer tells the ten demo languages apart."""
    result = await StubAiReviewAnalyzer().analyze(AiReviewAnalysisRequest(review_text=text))

    assert result.language_code == language
