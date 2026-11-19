"""CSV rendering of the admin review list.

The export uses the standard library ``csv`` module only — no extra
dependency is needed.  The rows are written straight into the response
stream, so a large dataset never has to be buffered in memory.
"""

import csv
import io
from collections.abc import Iterable, Iterator
from enum import Enum
from typing import Any

from app.schemas.review import AdminReviewDto

#: Column headers of the exported file, in the order they are written.
CSV_HEADERS: tuple[str, ...] = (
    "id",
    "created_at_utc",
    "author_name",
    "email",
    "text",
    "language_code",
    "analysis_status",
    "rating",
    "priority",
    "category",
    "needs_urgent_response",
    "ai_draft_response_provider",
    "ai_draft_response_model",
    "ai_draft_response",
)

#: The UTF-8 byte order mark, so Excel opens the file with the right encoding.
UTF8_BOM = "﻿"

#: Characters that make a spreadsheet treat a cell as a formula.
#:
#: A review is written by an anonymous visitor, so the exported file may
#: contain text that a spreadsheet would execute instead of displaying.
#: Prefixing such a cell with an apostrophe turns it back into plain text.
#: The pipe also starts a DDE call in some spreadsheets.
_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "|", "\t", "\r")


def _cell(value: Any) -> str:
    """Render one field of a review as a CSV cell.

    Empty values become an empty cell, and a missing value never turns
    into the text "None" — which would be confusing in a spreadsheet.

    Enumerations are rendered by their value, not by their Python
    representation, so the file contains ``Pending`` instead of
    ``AnalysisStatus.PENDING``.

    A cell that starts with a character a spreadsheet would interpret as
    the beginning of a formula is prefixed with an apostrophe, which
    turns it into plain text.

    Args:
        value: The raw field value.

    Returns:
        The value as a string, ready to be written to the CSV.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, Enum):
        value = value.value
    text = str(value)
    # Some spreadsheets strip leading blanks before parsing, so " =1+1" is
    # a formula as well.
    if text.startswith(_FORMULA_PREFIXES) or text.lstrip(" \n").startswith(_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def review_to_row(review: AdminReviewDto) -> list[str]:
    """Convert a review into one CSV row.

    Args:
        review: The review to render.

    Returns:
        The row values, in the same order as :data:`CSV_HEADERS`.
    """
    return [
        _cell(review.id),
        _cell(review.created_at_utc),
        _cell(review.author_name),
        _cell(review.email),
        _cell(review.text),
        _cell(review.language_code),
        _cell(review.analysis_status),
        _cell(review.rating),
        _cell(review.priority),
        _cell(review.category),
        _cell(review.needs_urgent_response),
        _cell(review.ai_draft_response_provider),
        _cell(review.ai_draft_response_model),
        _cell(review.ai_draft_response),
    ]


def iter_reviews_csv(reviews: Iterable[AdminReviewDto]) -> Iterator[str]:
    """Render the reviews as CSV, one line at a time.

    Only the current row is held in memory, so the response can be streamed
    while the rows are still being fetched from the database.

    Args:
        reviews: The reviews to export.

    Yields:
        The UTF-8 byte order mark plus the header line first, then one line
        per review.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")

    def flush() -> str:
        """Return the buffered line and empty the buffer for the next one."""
        line = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return line

    writer.writerow(CSV_HEADERS)
    yield UTF8_BOM + flush()

    for review in reviews:
        writer.writerow(review_to_row(review))
        yield flush()
