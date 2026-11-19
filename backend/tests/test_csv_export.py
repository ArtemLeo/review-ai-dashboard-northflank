"""Tests for the CSV rendering of the admin review list."""

import csv
import io
from datetime import datetime

from app.core.csv_export import CSV_HEADERS, UTF8_BOM, iter_reviews_csv, review_to_row
from app.models.review import AnalysisStatus, Priority, Rating, ReviewCategory
from app.schemas.review import AdminReviewDto


def _review(**overrides: object) -> AdminReviewDto:
    """Build a review DTO with sensible defaults.

    Args:
        overrides: Fields that replace the default values.

    Returns:
        The review DTO to render.
    """
    data: dict[str, object] = {
        "id": "review-1",
        "author_name": "Test User",
        "email": "test@example.com",
        "text": "A perfectly ordinary review.",
        "language_code": "en",
        "created_at_utc": datetime(2026, 10, 22, 10, 0, 0),
        "analysis_status": AnalysisStatus.PENDING,
        "rating": Rating.FOUR,
        "priority": Priority.MEDIUM,
        "category": ReviewCategory.PRAISE,
    }
    data.update(overrides)
    return AdminReviewDto(**data)  # type: ignore[arg-type]


def test_enums_are_rendered_by_their_value() -> None:
    """The file shows the readable value, not the Python enum member."""
    row = review_to_row(_review())

    assert row[CSV_HEADERS.index("analysis_status")] == "Pending"
    assert row[CSV_HEADERS.index("rating")] == "4"
    assert row[CSV_HEADERS.index("priority")] == "Medium"
    assert row[CSV_HEADERS.index("category")] == "Praise"


def test_the_urgency_flag_is_rendered_as_yes_or_no() -> None:
    """The AI's urgency flag reads as plain words; an unanalysed review stays empty."""
    assert review_to_row(_review(needs_urgent_response=True))[CSV_HEADERS.index("needs_urgent_response")] == "yes"
    assert review_to_row(_review(needs_urgent_response=False))[CSV_HEADERS.index("needs_urgent_response")] == "no"
    assert review_to_row(_review(needs_urgent_response=None))[CSV_HEADERS.index("needs_urgent_response")] == ""


def test_missing_values_become_empty_cells() -> None:
    """An absent value is an empty cell, never the text "None"."""
    row = review_to_row(
        _review(
            language_code=None,
            rating=None,
            priority=None,
            category=None,
        )
    )

    assert row[CSV_HEADERS.index("language_code")] == ""
    assert row[CSV_HEADERS.index("rating")] == ""
    assert row[CSV_HEADERS.index("priority")] == ""
    assert row[CSV_HEADERS.index("category")] == ""


def test_a_formula_in_the_review_text_is_neutralised() -> None:
    """A cell that a spreadsheet would run is turned into plain text."""
    row = review_to_row(_review(text="=1+1"))

    assert row[CSV_HEADERS.index("text")] == "'=1+1"


def test_every_formula_prefix_is_neutralised() -> None:
    """Each character a spreadsheet treats as a formula start is escaped."""
    for prefix in ("=", "+", "-", "@", "|"):
        row = review_to_row(_review(text=f"{prefix}cmd"))

        assert row[CSV_HEADERS.index("text")] == f"'{prefix}cmd"


def test_a_formula_behind_leading_blanks_is_neutralised() -> None:
    """Spreadsheets that trim leading blanks must not run the formula either."""
    row = review_to_row(_review(text='  =HYPERLINK("http://x")'))

    assert row[CSV_HEADERS.index("text")].startswith("'")


def test_ordinary_text_is_left_alone() -> None:
    """A review without a formula prefix is exported unchanged."""
    row = review_to_row(_review(text="Great service, thanks!"))

    assert row[CSV_HEADERS.index("text")] == "Great service, thanks!"


def test_the_document_starts_with_the_header_row() -> None:
    """The first row names the columns."""
    document = "".join(iter_reviews_csv([_review()]))
    rows = list(csv.reader(io.StringIO(document.lstrip(UTF8_BOM))))

    assert rows[0] == list(CSV_HEADERS)
    assert len(rows) == 2


def test_the_document_starts_with_a_byte_order_mark() -> None:
    """Excel needs the mark to detect the encoding."""
    document = "".join(iter_reviews_csv([_review()]))

    assert document.startswith(UTF8_BOM)


def test_the_rows_are_streamed_one_line_at_a_time() -> None:
    """The header and every review arrive as separate chunks."""
    chunks = list(iter_reviews_csv([_review(), _review()]))

    assert len(chunks) == 3
    assert all(chunk.endswith("\r\n") for chunk in chunks)
