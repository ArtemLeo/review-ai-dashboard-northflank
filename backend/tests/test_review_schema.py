"""Tests for the validation of the public review submission payload."""

import pytest
from pydantic import ValidationError

from app.schemas.review import MAX_REVIEW_TEXT_LENGTH, CreateReviewRequest


def _payload(**overrides: object) -> dict[str, object]:
    """Build a valid submission payload.

    Args:
        overrides: Fields that replace the default values.

    Returns:
        The payload as a dictionary.
    """
    data: dict[str, object] = {
        "author_name": "Test User",
        "email": "test@example.com",
        "text": "A perfectly ordinary review.",
    }
    data.update(overrides)
    return data


def test_a_valid_payload_is_accepted() -> None:
    """A normal review passes the validation."""
    request = CreateReviewRequest(**_payload())

    assert request.author_name == "Test User"
    assert request.text == "A perfectly ordinary review."


def test_the_text_is_trimmed() -> None:
    """The surrounding whitespace is removed."""
    request = CreateReviewRequest(**_payload(text="  A review.  "))

    assert request.text == "A review."


def test_a_blank_text_is_rejected() -> None:
    """A text of only spaces is treated as a missing one."""
    with pytest.raises(ValidationError):
        CreateReviewRequest(**_payload(text="   "))


def test_an_empty_text_is_rejected() -> None:
    """An empty text is rejected."""
    with pytest.raises(ValidationError):
        CreateReviewRequest(**_payload(text=""))


def test_a_blank_author_name_is_rejected() -> None:
    """A name of only spaces is treated as a missing one."""
    with pytest.raises(ValidationError):
        CreateReviewRequest(**_payload(author_name="   "))


def test_an_overlong_text_is_rejected() -> None:
    """A text longer than the limit is rejected."""
    with pytest.raises(ValidationError):
        CreateReviewRequest(**_payload(text="x" * (MAX_REVIEW_TEXT_LENGTH + 1)))


def test_a_text_of_the_limit_length_is_accepted() -> None:
    """A text of exactly the limit is still accepted."""
    request = CreateReviewRequest(**_payload(text="x" * MAX_REVIEW_TEXT_LENGTH))

    assert len(request.text) == MAX_REVIEW_TEXT_LENGTH


def test_an_overlong_author_name_is_rejected() -> None:
    """A name longer than the column can store is rejected."""
    with pytest.raises(ValidationError):
        CreateReviewRequest(**_payload(author_name="x" * 151))
