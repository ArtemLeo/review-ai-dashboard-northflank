"""Tests for the scrypt password hashing helpers."""

from app.core.passwords import hash_password, is_valid_hash, verify_password


def test_the_right_password_matches_its_hash() -> None:
    """A hash verifies the password it was created from."""
    encoded = hash_password("correct horse battery staple")

    assert is_valid_hash(encoded)
    assert verify_password("correct horse battery staple", encoded) is True


def test_a_wrong_password_does_not_match() -> None:
    """Any other password, including a non-ASCII one, is refused."""
    encoded = hash_password("correct horse battery staple")

    assert verify_password("Correct horse battery staple", encoded) is False
    assert verify_password("пароль", encoded) is False


def test_every_hash_gets_its_own_salt() -> None:
    """Two hashes of the same password differ."""
    assert hash_password("same") != hash_password("same")


def test_a_malformed_hash_never_matches() -> None:
    """Garbage in the setting is a refusal, not a crash."""
    assert verify_password("x", "scrypt$1$2") is False
    assert verify_password("x", "bcrypt$1$2$3$aa$bb") is False
    assert verify_password("x", "scrypt$a$b$c$zz$yy") is False
    assert is_valid_hash("scrypt$a$b$c$zz$yy") is False
