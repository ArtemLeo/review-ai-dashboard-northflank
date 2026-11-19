"""Builders of the database rows the backend tests start from."""

from sqlalchemy.orm import Session

from app.models.review import Review


def create_review(db: Session, text: str = "Great product, thank you so much!") -> Review:
    """Persist a review in the pending state and return it.

    Args:
        db: The test database session.
        text: The review text, which decides what the stub analyser finds.

    Returns:
        The persisted review row.
    """
    review = Review(author_name="Test User", email="test@example.com", text=text)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
