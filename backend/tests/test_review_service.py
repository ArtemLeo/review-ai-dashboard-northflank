"""Tests for the ReviewService domain service."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.review import AnalysisStatus, Priority, Review
from app.schemas.review import CreateReviewRequest, ReviewQuery
from app.services.review_service import ReviewService


def _seed_review(
    db: Session,
    *,
    author_name: str = "Test User",
    email: str = "test@example.com",
    text: str = "Great product!",
    rating: int | None = None,
    priority: str | None = None,
    status: str = AnalysisStatus.PENDING.value,
    created_at_offset_hours: int = 0,
) -> Review:
    """Insert a review row and return the persisted instance."""
    review = Review(
        author_name=author_name,
        email=email,
        text=text,
        rating=rating,
        priority=priority,
        analysis_status=status,
        created_at_utc=datetime.now(UTC) + timedelta(hours=created_at_offset_hours),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


# -- create ------------------------------------------------------------------


def test_create_persists_review(db_session: Session) -> None:
    """A created review is stored in the database with PENDING status."""
    svc = ReviewService(db_session)
    dto = svc.create(CreateReviewRequest(author_name="Alice", email="a@b.com", text="Nice"))

    assert dto.author_name == "Alice"
    assert dto.text == "Nice"
    assert dto.analysis_status == AnalysisStatus.PENDING


def test_create_strips_whitespace(db_session: Session) -> None:
    """Leading and trailing whitespace is removed from all text fields."""
    svc = ReviewService(db_session)
    dto = svc.create(CreateReviewRequest(author_name="  Bob  ", email="b@b.com", text="  Good  "))

    assert dto.author_name == "Bob"
    assert dto.text == "Good"


# -- get_by_id ---------------------------------------------------------------


def test_get_by_id_found(db_session: Session) -> None:
    """An existing review is returned by its UUID."""
    review = _seed_review(db_session)
    svc = ReviewService(db_session)

    result = svc.get_by_id(review.id)
    assert result is not None
    assert result.id == review.id
    assert result.email == review.email


def test_get_by_id_not_found(db_session: Session) -> None:
    """A missing UUID returns None instead of raising."""
    svc = ReviewService(db_session)
    assert svc.get_by_id("00000000-0000-0000-0000-000000000000") is None


# -- get_all_paginated -------------------------------------------------------


def test_paginated_empty(db_session: Session) -> None:
    """An empty table returns zero items and zero pages."""
    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery())

    assert result.total == 0
    assert result.total_pages == 0
    assert result.items == []


def test_paginated_single_page(db_session: Session) -> None:
    """All items fit in a single page."""
    for i in range(3):
        _seed_review(db_session, author_name=f"User {i}", email=f"u{i}@x.com")

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(), page=1, page_size=10)

    assert result.total == 3
    assert result.total_pages == 1
    assert len(result.items) == 3


def test_paginated_multiple_pages(db_session: Session) -> None:
    """Items are split correctly across pages."""
    for i in range(5):
        _seed_review(db_session, author_name=f"User {i}", email=f"u{i}@x.com")

    svc = ReviewService(db_session)

    page1 = svc.get_all_paginated(ReviewQuery(), page=1, page_size=2)
    assert len(page1.items) == 2
    assert page1.total == 5
    assert page1.total_pages == 3

    page3 = svc.get_all_paginated(ReviewQuery(), page=3, page_size=2)
    assert len(page3.items) == 1


def test_paginated_beyond_last_page(db_session: Session) -> None:
    """Requesting a page past the end returns an empty list."""
    _seed_review(db_session)
    svc = ReviewService(db_session)

    result = svc.get_all_paginated(ReviewQuery(), page=99, page_size=10)
    assert result.items == []
    assert result.total == 1


# -- filtering ---------------------------------------------------------------


def test_filter_by_status(db_session: Session) -> None:
    """Only reviews matching the requested status are returned."""
    _seed_review(db_session, status=AnalysisStatus.PENDING.value)
    _seed_review(db_session, email="c@x.com", status=AnalysisStatus.COMPLETED.value)

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(status=AnalysisStatus.COMPLETED))

    assert result.total == 1
    assert result.items[0].analysis_status == AnalysisStatus.COMPLETED


def test_filter_by_priority(db_session: Session) -> None:
    """Only reviews matching the requested priority are returned."""
    _seed_review(db_session, priority=Priority.HIGH.value)
    _seed_review(db_session, email="lo@x.com", priority=Priority.LOW.value)

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(priority=Priority.HIGH))

    assert result.total == 1
    assert result.items[0].priority == Priority.HIGH


def test_filter_by_rating(db_session: Session) -> None:
    """Only reviews matching the requested star rating are returned."""
    _seed_review(db_session, rating=5)
    _seed_review(db_session, email="r2@x.com", rating=2)

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(rating=5))

    assert result.total == 1
    assert result.items[0].rating == 5


# -- sorting -----------------------------------------------------------------


def test_sort_by_date_descending(db_session: Session) -> None:
    """Default sort returns newest reviews first."""
    old = _seed_review(db_session, author_name="Old", created_at_offset_hours=-10)
    new = _seed_review(db_session, author_name="New", email="n@x.com", created_at_offset_hours=0)

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(descending=True))

    assert result.items[0].id == new.id
    assert result.items[1].id == old.id


def test_sort_by_date_ascending(db_session: Session) -> None:
    """Ascending date sort returns oldest reviews first."""
    old = _seed_review(db_session, author_name="Old", created_at_offset_hours=-10)
    new = _seed_review(db_session, author_name="New", email="n@x.com", created_at_offset_hours=0)

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(descending=False))

    assert result.items[0].id == old.id
    assert result.items[1].id == new.id


def test_sort_by_rating(db_session: Session) -> None:
    """Sorting by rating orders rows by the numeric star value."""
    _seed_review(db_session, rating=1, author_name="Low")
    _seed_review(db_session, email="h@x.com", rating=5, author_name="High")

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(sort_by="rating", descending=True))

    assert result.items[0].rating == 5
    assert result.items[1].rating == 1


def test_sort_by_priority(db_session: Session) -> None:
    """Sorting by priority uses the custom urgency weight, not alphabetical order."""
    _seed_review(db_session, priority=Priority.LOW.value, author_name="Lo")
    _seed_review(db_session, email="hi@x.com", priority=Priority.HIGH.value, author_name="Hi")

    svc = ReviewService(db_session)
    result = svc.get_all_paginated(ReviewQuery(sort_by="priority", descending=True))

    assert result.items[0].priority == Priority.HIGH
    assert result.items[1].priority == Priority.LOW


# -- update_status -----------------------------------------------------------


def test_update_status(db_session: Session) -> None:
    """The analysis status of an existing review is updated."""
    review = _seed_review(db_session)
    svc = ReviewService(db_session)

    updated = svc.update_status(review.id, AnalysisStatus.COMPLETED)
    assert updated is not None
    assert updated.analysis_status == AnalysisStatus.COMPLETED


def test_update_status_not_found(db_session: Session) -> None:
    """Updating a non-existent review returns None."""
    svc = ReviewService(db_session)
    assert svc.update_status("missing-id", AnalysisStatus.COMPLETED) is None


# -- statistics --------------------------------------------------------------


def test_statistics_empty(db_session: Session) -> None:
    """Statistics on an empty table return all zeroes."""
    svc = ReviewService(db_session)
    stats = svc.get_statistics()

    assert stats.total == 0
    assert stats.avg_rating == 0.0
    assert stats.rating_1 == 0


def test_statistics_with_data(db_session: Session) -> None:
    """Statistics reflect the correct rating distribution and average."""
    _seed_review(db_session, rating=5, author_name="A")
    _seed_review(db_session, rating=5, email="b@x.com", author_name="B")
    _seed_review(db_session, rating=3, email="c@x.com", author_name="C")
    _seed_review(db_session, rating=1, email="d@x.com", author_name="D")

    svc = ReviewService(db_session)
    stats = svc.get_statistics()

    assert stats.total == 4
    assert stats.rating_5 == 2
    assert stats.rating_3 == 1
    assert stats.rating_1 == 1
    assert stats.rating_2 == 0
    assert stats.rating_4 == 0
    assert stats.avg_rating == 3.5


# -- stream_all --------------------------------------------------------------


def test_stream_all_empty(db_session: Session) -> None:
    """Streaming an empty table yields nothing."""
    svc = ReviewService(db_session)
    assert list(svc.stream_all(ReviewQuery())) == []


def test_stream_all_returns_all_rows(db_session: Session) -> None:
    """Every matching row is yielded exactly once."""
    for i in range(4):
        _seed_review(db_session, author_name=f"User {i}", email=f"u{i}@x.com")

    svc = ReviewService(db_session)
    rows = list(svc.stream_all(ReviewQuery()))

    assert len(rows) == 4


def test_stream_all_respects_filter(db_session: Session) -> None:
    """The stream applies the same filters as the paginated query."""
    _seed_review(db_session, rating=5)
    _seed_review(db_session, email="o@x.com", rating=2)

    svc = ReviewService(db_session)
    rows = list(svc.stream_all(ReviewQuery(rating=5)))

    assert len(rows) == 1
    assert rows[0].rating == 5
