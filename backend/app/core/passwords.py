"""Password hashing with the standard library's scrypt.

The administrator password can be configured as a hash
(``ADMIN_PASSWORD_HASH``), so the plain text never has to live in the
environment.  Hashes use the format ``scrypt$n$r$p$<salt hex>$<key hex>``.
"""

import hashlib
import hmac
import secrets

#: Prefix of every hash produced by :func:`hash_password`.
SCHEME = "scrypt"

#: scrypt cost parameters (RFC 7914); n=2**14 keeps a check well under 100 ms.
_N, _R, _P = 2**14, 8, 1

#: Length of the random salt and of the derived key, in bytes.
_SALT_BYTES = 16
_KEY_BYTES = 32


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    """Derive the scrypt key of a password."""
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        maxmem=128 * n * r * p + 1024 * 1024,
        dklen=_KEY_BYTES,
    )


def hash_password(password: str) -> str:
    """Hash a password with a fresh random salt.

    Args:
        password: The plain-text password.

    Returns:
        The encoded hash, ready for ``ADMIN_PASSWORD_HASH``.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    key = _derive(password, salt, _N, _R, _P)
    return f"{SCHEME}${_N}${_R}${_P}${salt.hex()}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against an encoded hash in constant time.

    Args:
        password: The submitted plain-text password.
        encoded: A hash produced by :func:`hash_password`.

    Returns:
        ``True`` when the password matches; a malformed hash never matches.
    """
    try:
        scheme, n, r, p, salt_hex, key_hex = encoded.strip().split("$")
        if scheme != SCHEME:
            return False
        expected = bytes.fromhex(key_hex)
        actual = _derive(password, bytes.fromhex(salt_hex), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)


def is_valid_hash(encoded: str) -> bool:
    """Return whether a string has the shape of a :func:`hash_password` result."""
    parts = encoded.strip().split("$")
    if len(parts) != 6 or parts[0] != SCHEME:
        return False
    try:
        int(parts[1]), int(parts[2]), int(parts[3])
        bytes.fromhex(parts[4]), bytes.fromhex(parts[5])
    except ValueError:
        return False
    return True
