"""Tests for the defensive parsing of raw AI provider responses."""

import pytest

from app.ai.parsing import (
    MAX_LANGUAGE_CODE_LENGTH,
    coerce_bool,
    coerce_category,
    coerce_language_code,
    coerce_priority,
    coerce_rating,
    parse_json_object,
    strip_code_fence,
)
from app.models.review import Priority, Rating, ReviewCategory


def test_strip_code_fence_removes_the_markers() -> None:
    """A fenced answer is unwrapped."""
    assert strip_code_fence("```json\n{}\n```") == "{}"


def test_strip_code_fence_keeps_plain_text() -> None:
    """Text without a fence is returned unchanged."""
    assert strip_code_fence("  plain  ") == "plain"


def test_parse_json_object_reads_the_payload() -> None:
    """The decoded object is returned."""
    assert parse_json_object('{"rating": 4}') == {"rating": 4}


def test_parse_json_object_rejects_a_list() -> None:
    """A JSON array is not an object."""
    with pytest.raises(ValueError, match="not a JSON object"):
        parse_json_object("[1, 2]")


def test_coerce_rating_clamps_into_the_range() -> None:
    """A rating outside the 1-5 range is clamped."""
    assert coerce_rating(9) == Rating.FIVE
    assert coerce_rating(0) == Rating.ONE
    assert coerce_rating("4") == Rating.FOUR


def test_coerce_rating_falls_back_for_garbage() -> None:
    """An unusable value becomes the default rating."""
    assert coerce_rating("not a number") == Rating.THREE
    assert coerce_rating(None) == Rating.THREE


def test_coerce_rating_falls_back_for_infinite_numbers() -> None:
    """JSON's Infinity or an overlong exponent cannot crash the parsing."""
    assert coerce_rating(float("inf")) == Rating.THREE
    assert coerce_rating("1e999") == Rating.THREE


def test_coerce_priority_matches_the_value_or_the_name() -> None:
    """Both spellings of a priority are accepted."""
    assert coerce_priority("High") == Priority.HIGH
    assert coerce_priority("high") == Priority.HIGH
    assert coerce_priority("HIGH") == Priority.HIGH


def test_coerce_priority_falls_back_for_garbage() -> None:
    """An unknown priority becomes the default one."""
    assert coerce_priority("whenever") == Priority.MEDIUM


def test_coerce_category_ignores_the_spaces() -> None:
    """A category written with a space is still recognised."""
    assert coerce_category("Feature Request") == ReviewCategory.FEATURE_REQUEST


def test_coerce_bool_reads_the_common_spellings() -> None:
    """The truthy spellings a model may use are recognised."""
    assert coerce_bool(True) is True
    assert coerce_bool("true") is True
    assert coerce_bool("Yes") is True
    assert coerce_bool(1) is True
    assert coerce_bool("false") is False
    assert coerce_bool(None) is False
    assert coerce_bool(0) is False


def test_coerce_language_code_keeps_a_valid_code() -> None:
    """A well-formed code is passed through."""
    assert coerce_language_code("uk") == "uk"
    assert coerce_language_code("en") == "en"


def test_coerce_language_code_keeps_a_region_suffix() -> None:
    """A code with a region or script suffix is accepted."""
    assert coerce_language_code("zh-Hans") == "zh-hans"


def test_coerce_language_code_accepts_upper_case() -> None:
    """An upper-case answer keeps its language instead of falling back."""
    assert coerce_language_code("DE") == "de"
    assert coerce_language_code(" Uk ") == "uk"


def test_coerce_language_code_shortens_an_overlong_value() -> None:
    """A long answer is cut to the length the column can store."""
    code = coerce_language_code("u" * 50)

    assert len(code) <= MAX_LANGUAGE_CODE_LENGTH


def test_coerce_language_code_falls_back_for_garbage() -> None:
    """A malformed code becomes the default one."""
    assert coerce_language_code("Ukrainian") == "en"
    assert coerce_language_code("") == "en"
    assert coerce_language_code(None) == "en"
    assert coerce_language_code(42) == "en"
