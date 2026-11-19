"""Tests for the demo reviews that SEED_DEMO_DATA loads into an empty database."""

from collections import Counter

from scripts.seed_database import DEMO_PROFILES, DEMO_REPLIES, demo_reviews


def _primary(language_code: str) -> str:
    """Return the language of a code such as ``en-us``, without the region."""
    return language_code.split("-")[0]


def test_the_demo_has_a_hundred_different_reviews() -> None:
    """No text repeats, so the list never looks generated."""
    texts = [text for text, _language, _profile in demo_reviews()]

    assert len(texts) == 100
    assert len(set(texts)) == 100


def test_english_leads_and_every_language_is_present() -> None:
    """English leads, Ukrainian follows, and seven other languages have 5 to 7 each."""
    shares = Counter(_primary(language) for _text, language, _profile in demo_reviews())
    others = {language: count for language, count in shares.items() if language not in {"en", "uk"}}

    assert (shares["en"], shares["uk"]) == (31, 29)
    assert "ru" not in shares
    assert sorted(others) == ["de", "es", "fr", "it", "ja", "pl", "zh"]
    assert set(others.values()) <= {5, 6, 7}


def test_the_ratings_spread_like_real_feedback() -> None:
    """Mostly happy players, a fifth complaining, and no suspiciously round numbers."""
    stars = Counter(profile.rating for _text, _language, profile in demo_reviews())

    assert stars == Counter({5: 42, 4: 21, 3: 17, 2: 11, 1: 9})


def test_only_the_complaints_are_high_priority_and_urgent() -> None:
    """High priority and the urgency flag go together, and only with 1 or 2 stars."""
    for profile in DEMO_PROFILES.values():
        assert profile.needs_urgent_response == (profile.priority == "High")
        assert (profile.priority == "High") == (profile.rating <= 2)


def test_every_review_has_a_draft_in_its_language() -> None:
    """The draft reply exists in the language of every demo review."""
    for _text, language, profile in demo_reviews():
        assert DEMO_REPLIES[profile.reply][_primary(language)]
