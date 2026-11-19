"""Tests for the production guard of the application settings."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.passwords import hash_password

_STRONG_SECRET = "k3Jx9vQ2mT7wZp5Rb8NdA1sLyH6uEf4G0cXoVi"
_STRONG_PASSWORD = "r8Qm2Zt5Xw9Lp3Vb7Nc1"
_REAL_DATABASE_URL = "postgresql+psycopg://reviews:k4Rt8Wq2Zp6Ls1Vn@postgres:5432/reviews_db"


def test_development_accepts_placeholder_secrets() -> None:
    """Outside production the placeholder defaults keep working."""
    settings = Settings(
        environment="development",
        jwt_secret_key="dev-only-secret-key-change-me-in-production",
        admin_password="dev-only-admin-password",
    )

    assert settings.environment == "development"


def test_production_rejects_a_placeholder_jwt_secret() -> None:
    """A production start with the default JWT secret fails fast."""
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            environment="production",
            jwt_secret_key="dev-only-secret-key-change-me-in-production",
            admin_password=_STRONG_PASSWORD,
        )


def test_staging_rejects_a_placeholder_jwt_secret() -> None:
    """Only development and test accept the public defaults."""
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            environment="staging",
            jwt_secret_key="dev-only-secret-key-change-me-in-production",
            admin_password=_STRONG_PASSWORD,
        )


def test_production_rejects_a_placeholder_admin_password() -> None:
    """A production start with the default admin password fails fast."""
    with pytest.raises(ValidationError, match="ADMIN_PASSWORD"):
        Settings(
            environment="production",
            jwt_secret_key=_STRONG_SECRET,
            admin_password="dev-only-admin-password",
        )


def test_production_rejects_a_short_jwt_secret() -> None:
    """A production start with a brute-forceable JWT secret fails fast."""
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(
            environment="production",
            jwt_secret_key="k3Jx9vQ2mT7w",
            admin_password=_STRONG_PASSWORD,
            database_url=_REAL_DATABASE_URL,
        )


def test_production_accepts_real_secrets() -> None:
    """Real secrets pass the production check."""
    settings = Settings(
        environment="Production",
        jwt_secret_key=_STRONG_SECRET,
        admin_password=_STRONG_PASSWORD,
        database_url=_REAL_DATABASE_URL,
    )

    assert settings.environment == "Production"


def test_production_rejects_the_default_database_password() -> None:
    """The default database password is public, so production refuses it."""
    with pytest.raises(ValidationError, match="POSTGRES_PASSWORD"):
        Settings(
            environment="production",
            jwt_secret_key=_STRONG_SECRET,
            admin_password=_STRONG_PASSWORD,
            database_url="postgresql+psycopg://reviews:reviews_password@postgres:5432/reviews_db",
        )


def test_a_malformed_password_hash_is_refused() -> None:
    """A broken hash fails fast instead of locking the admin out at login."""
    with pytest.raises(ValidationError, match="ADMIN_PASSWORD_HASH"):
        Settings(admin_password_hash="not-a-hash")


def test_production_accepts_a_hash_instead_of_the_password() -> None:
    """With a hash configured, the unused default password is not an error."""
    settings = Settings(
        environment="production",
        jwt_secret_key=_STRONG_SECRET,
        admin_password="dev-only-admin-password",
        admin_password_hash=hash_password(_STRONG_PASSWORD),
        database_url=_REAL_DATABASE_URL,
    )

    assert settings.admin_password_hash.startswith("scrypt$")


@pytest.mark.parametrize("placeholder", ["your-groq-api-key-here", "  your-gemini-api-key-here  "])
def test_a_placeholder_api_key_counts_as_no_key(placeholder: str) -> None:
    """A key copied unchanged from .env.example must not be sent to the provider."""
    settings = Settings(groq_api_key=placeholder, gemini_api_key=placeholder)

    assert settings.groq_api_key == ""
    assert settings.gemini_api_key == ""


def test_a_real_api_key_is_kept() -> None:
    """A real key passes through, without surrounding blanks."""
    settings = Settings(groq_api_key="  gsk_live_1234567890abcdef  ")

    assert settings.groq_api_key == "gsk_live_1234567890abcdef"


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_a_plain_postgres_url_uses_the_psycopg_driver(scheme: str) -> None:
    """A platform-issued URL is switched to the installed psycopg driver."""
    settings = Settings(database_url=f"{scheme}://user:pw@db:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:pw@db:5432/app"


def test_a_psycopg_url_is_kept() -> None:
    """A URL that already names the driver passes through unchanged."""
    settings = Settings(database_url=_REAL_DATABASE_URL)

    assert settings.database_url == _REAL_DATABASE_URL


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("rediss://:pw@cache:6379/0", "rediss://:pw@cache:6379/0?ssl_cert_reqs=required"),
        ("rediss://cache:6379/0?x=1", "rediss://cache:6379/0?x=1&ssl_cert_reqs=required"),
        ("rediss://cache:6379/0?ssl_cert_reqs=none", "rediss://cache:6379/0?ssl_cert_reqs=none"),
        ("redis://cache:6379/0", "redis://cache:6379/0"),
    ],
)
def test_a_tls_redis_url_states_its_certificate_check(url: str, expected: str) -> None:
    """Celery accepts a TLS broker URL only with ssl_cert_reqs set."""
    assert Settings(redis_url=url).redis_url == expected
