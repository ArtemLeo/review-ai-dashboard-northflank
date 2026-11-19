"""Helpers for parsing and normalizing raw AI provider responses.

Language models return loosely structured JSON.  This module centralises the
defensive parsing so that a single malformed field never aborts the whole
analysis: values are coerced into the valid domain instead of raising.
"""

import json
import re
from typing import Any

from app.ai.errors import AiProviderError
from app.core.constants import MAX_LANGUAGE_CODE_LENGTH
from app.models.review import Priority, Rating, ReviewCategory

#: Fallback rating used when the model returns something unusable.
_DEFAULT_RATING: Rating = Rating.THREE
_DEFAULT_PRIORITY: Priority = Priority.MEDIUM
_DEFAULT_CATEGORY: ReviewCategory = ReviewCategory.OTHER

#: Fallback language used when the model does not name a usable one.
_DEFAULT_LANGUAGE_CODE: str = "en"

#: Shape of a language code: two lowercase letters, optionally followed by a
#: region or a script suffix, e.g. ``uk`` or ``zh-Hans``.
_LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2}(-[A-Za-z]{2,4})?$")


def strip_code_fence(content: str) -> str:
    """Remove a surrounding Markdown code fence from an LLM response.

    Args:
        content: Raw message content returned by the provider.

    Returns:
        The content with the leading/trailing ```` ``` ```` markers removed.
    """
    text: str = content.strip()
    if not text.startswith("```"):
        return text

    lines: list[str] = text.splitlines()
    lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object out of an LLM response.

    Args:
        content: Raw message content, optionally wrapped in a code fence.

    Returns:
        The decoded JSON object.

    Raises:
        AiProviderError: If the content is not a JSON object.
    """
    try:
        payload: Any = json.loads(strip_code_fence(content))
    except json.JSONDecodeError as exc:
        raise AiProviderError("AI provider response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise AiProviderError("AI provider response is not a JSON object")
    return payload


def coerce_rating(value: Any) -> Rating:
    """Coerce an arbitrary model output into a valid :class:`Rating`.

    Values are clamped into the 1-5 range instead of raising, so a slightly
    out-of-range answer still produces a usable review.

    Args:
        value: The raw value returned by the model.

    Returns:
        A valid :class:`Rating` member.
    """
    try:
        numeric: int = int(float(value))
    except (TypeError, ValueError, OverflowError):
        # OverflowError: JSON allows Infinity and 1e999, which no int can hold.
        return _DEFAULT_RATING

    clamped: int = max(Rating.ONE.value, min(Rating.FIVE.value, numeric))
    return Rating(clamped)


def coerce_bool(value: Any) -> bool:
    """Coerce an arbitrary model output into a boolean value.

    Booleans are kept as-is, nonzero numbers are true, and the strings
    ``"true"``, ``"yes"``, ``"1"`` and ``"y"`` are accepted without regard
    to case.  Other values fall back to false instead of raising.

    Args:
        value: The raw value returned by the model.

    Returns:
        A valid bool member.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text: str = str(value).strip().lower()
    return text in {"true", "yes", "1", "y"}


def coerce_language_code(value: Any) -> str:
    """Coerce an arbitrary model output into a language code.

    Values are clamped to the column's length and shape, so a long or malformed
    answer cannot trigger a database error that would discard the whole
    analysis.  The default code ``en`` is returned when nothing usable is
    found.

    Args:
        value: The raw value returned by the model.

    Returns:
        A language code fitting :data:`MAX_LANGUAGE_CODE_LENGTH`.
    """
    if not isinstance(value, str):
        return _DEFAULT_LANGUAGE_CODE

    # Lower-cased before the check, so "DE" is read as German, not rejected.
    code: str = value.strip()[:MAX_LANGUAGE_CODE_LENGTH].lower()
    if not _LANGUAGE_CODE_PATTERN.match(code):
        return _DEFAULT_LANGUAGE_CODE
    return code


def coerce_priority(value: Any) -> Priority:
    """Coerce an arbitrary model output into a valid :class:`Priority`.

    Args:
        value: The raw value returned by the model.

    Returns:
        A valid :class:`Priority` member.
    """
    if isinstance(value, Priority):
        return value

    text: str = str(value).strip().lower()
    for member in Priority:
        if member.value.lower() == text or member.name.lower() == text:
            return member
    return _DEFAULT_PRIORITY


def coerce_category(value: Any) -> ReviewCategory:
    """Coerce an arbitrary model output into a valid :class:`ReviewCategory`.

    Args:
        value: The raw value returned by the model.

    Returns:
        A valid :class:`ReviewCategory` member.
    """
    if isinstance(value, ReviewCategory):
        return value

    text: str = str(value).strip().lower().replace(" ", "")
    for member in ReviewCategory:
        if member.value.lower() == text or member.name.lower() == text:
            return member
    return _DEFAULT_CATEGORY
