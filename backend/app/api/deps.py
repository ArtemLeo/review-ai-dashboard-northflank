"""Reusable FastAPI dependencies for API routers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai.factory import get_response_generator, get_review_analyzer
from app.db.session import get_db
from app.services.review_ai_service import ReviewAiService
from app.services.review_service import ReviewService


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    """Dependency provider for ReviewService."""
    return ReviewService(db)


def get_review_ai_service(db: Session = Depends(get_db)) -> ReviewAiService:
    """Dependency provider for ReviewAiService."""
    return ReviewAiService(
        db,
        get_review_analyzer(),
        get_response_generator(),
    )
