"""Application configuration loaded from environment variables.

All runtime settings are declared on a single :class:`Settings` model that
reads its values from the process environment and from optional ``.env``
files.  Every setting has a development-friendly default, so the application
starts without any configuration while deployments can override anything
through environment variables.
"""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.passwords import is_valid_hash

# Absolute path to the ``backend`` package root — used to resolve prompt
# templates independently of the current working directory.
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
PROMPTS_DIR = BACKEND_ROOT / "prompts"

#: Shortest JWT signing secret accepted in production (256 bits for HS256).
MIN_JWT_SECRET_BYTES = 32

#: Environments that may run with the public development defaults.
LENIENT_ENVIRONMENTS: frozenset[str] = frozenset({"development", "test"})


#: Fragments that mark an API key as a template placeholder, not a real key.
API_KEY_PLACEHOLDER_MARKERS: tuple[str, ...] = ("your-", "placeholder", "change-me", "example")

#: Fragments that mark a secret as a public placeholder.  Outside development
#: the application refuses to start with one of them in the JWT secret, the
#: administrator password or the database URL.  It is a constant rather than
#: a setting, so the environment cannot switch the check off.
INSECURE_SECRET_MARKERS: tuple[str, ...] = (
    "dev-only",
    "change-me",
    "changeme",
    "your-",
    "reviews_password",
    "example",
    "placeholder",
    "insecure",
    "secret-key-change",
)


class Settings(BaseSettings):
    """Centralized application settings.

    Values are resolved from (in order of precedence) the process environment,
    ``backend/.env``, the project-root ``.env`` and the field defaults
    declared below.
    """

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Runtime environment ────────────────────────────────────────────────
    environment: str = Field(
        default="development",
        description="Deployment environment. 'production' refuses placeholder secrets at startup.",
    )

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+psycopg://reviews:reviews_password@postgres:5432/reviews_db",
        description="SQLAlchemy database URL (PostgreSQL with the psycopg driver).",
    )

    # ── JWT security ───────────────────────────────────────────────────────
    jwt_secret_key: str = Field(
        default="dev-only-secret-key-change-me-in-production",
        description="Signing secret for access tokens. Must be overridden in production.",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    jwt_issuer: str = Field(default="review-ai-dashboard", description="Expected token issuer.")
    jwt_audience: str = Field(default="review-ai-dashboard", description="Expected token audience.")
    jwt_expiration_minutes: int = Field(default=30, ge=1, description="Access token lifetime in minutes.")

    # ── Administrator credentials ──────────────────────────────────────────
    # The defaults are the local development account.  The real values come
    # from the environment (the hosting platform's variables or an untracked
    # local ``.env``), which always wins over these defaults.
    # Non-development environments reject the public default password at
    # startup; configure a real password or password hash before deploying.
    admin_email: str = Field(default="admin@example.com", description="Administrator login.")
    admin_password: str = Field(default="dev-only-admin-password", description="Administrator password.")
    admin_password_hash: str = Field(
        default="",
        description=(
            "scrypt hash of the administrator password (scripts/hash_password.py). "
            "When set, it replaces ADMIN_PASSWORD."
        ),
    )

    # ── Redis / Celery ─────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL used by the Celery broker, rate limits, and session denylist.",
    )

    # ── AI providers ───────────────────────────────────────────────────────
    ai_provider: str = Field(
        default="auto",
        description="AI provider to use: 'groq', 'gemini', 'stub' or 'auto' to pick by the configured keys.",
    )
    groq_api_key: str = Field(default="", description="Groq API key. Empty disables the provider.")
    groq_model: str = Field(default="openai/gpt-oss-120b", description="Groq model identifier.")
    gemini_api_key: str = Field(default="", description="Google Gemini API key. Empty disables the provider.")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Google Gemini model identifier.")

    # ── Prompt templates ───────────────────────────────────────────────────
    analysis_instructions_file: str = Field(
        default=str(PROMPTS_DIR / "review_analysis.md"),
        description="System prompt used for review analysis by every AI provider.",
    )
    response_instructions_file: str = Field(
        default=str(PROMPTS_DIR / "response_generation.md"),
        description="System prompt used for draft response generation by every AI provider.",
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def _use_the_psycopg_driver(cls, value: str) -> str:
        """Point a plain PostgreSQL URL at the psycopg driver.

        Hosting platforms hand out ``postgres://`` or ``postgresql://`` URLs,
        which SQLAlchemy would resolve to the psycopg2 driver that is not
        installed.

        Args:
            value: The configured database URL.

        Returns:
            The URL with the ``postgresql+psycopg`` scheme.
        """
        for scheme in ("postgres://", "postgresql://"):
            if value.startswith(scheme):
                return "postgresql+psycopg://" + value[len(scheme) :]
        return value

    @field_validator("redis_url", mode="after")
    @classmethod
    def _verify_tls_certificates(cls, value: str) -> str:
        """Make a TLS Redis URL state how its certificate is checked.

        Celery refuses a ``rediss://`` broker URL without ``ssl_cert_reqs``.

        Args:
            value: The configured Redis URL.

        Returns:
            The URL, with ``ssl_cert_reqs=required`` added to a TLS URL that lacks it.
        """
        if value.startswith("rediss://") and "ssl_cert_reqs=" not in value:
            separator = "&" if "?" in value else "?"
            return f"{value}{separator}ssl_cert_reqs=required"
        return value

    @field_validator("groq_api_key", "gemini_api_key", mode="after")
    @classmethod
    def _ignore_placeholder_api_keys(cls, value: str) -> str:
        """Treat a key copied unchanged from ``.env.example`` as no key at all.

        A placeholder such as ``your-groq-api-key-here`` would otherwise make
        the "auto" provider call Groq with an invalid key, so every new review
        would fail its analysis.  An empty key selects the next provider and,
        in the end, the offline stub.

        Args:
            value: The configured API key.

        Returns:
            The key, or an empty string when it is a placeholder.
        """
        key = value.strip()
        lowered = key.lower()
        if any(marker in lowered for marker in API_KEY_PLACEHOLDER_MARKERS):
            return ""
        return key

    @model_validator(mode="after")
    def _reject_placeholder_secrets_in_production(self) -> "Settings":
        """Validate the password hash and refuse placeholder secrets outside development.

        The development defaults keep the application usable without any
        configuration, but they are public.  Only ``development`` and ``test``
        accept them; any other environment (production, staging, ...) refuses
        to start with a placeholder secret.

        Returns:
            The validated settings.

        Raises:
            ValueError: If the password hash is malformed, or if
                a non-development environment still uses a placeholder secret.
        """
        if self.admin_password_hash and not is_valid_hash(self.admin_password_hash):
            raise ValueError("ADMIN_PASSWORD_HASH is malformed; generate it with scripts/hash_password.py")

        if self.environment.strip().lower() in LENIENT_ENVIRONMENTS:
            return self

        secrets_to_check: list[tuple[str, str]] = [("JWT_SECRET_KEY", self.jwt_secret_key)]
        # A configured hash replaces the plain password, so the unused
        # default no longer matters.
        if not self.admin_password_hash:
            secrets_to_check.append(("ADMIN_PASSWORD", self.admin_password))
        # The default database password is public: it ships in this file.
        secrets_to_check.append(("POSTGRES_PASSWORD (DATABASE_URL)", self.database_url))

        for name, value in secrets_to_check:
            lowered = value.lower()
            if any(marker in lowered for marker in INSECURE_SECRET_MARKERS):
                raise ValueError(f"{name} is a placeholder value; set a real secret for {self.environment}")

        # RFC 7518 §3.2: an HMAC key must be at least as long as the hash
        # output, so a short secret could be brute-forced offline.
        if len(self.jwt_secret_key.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
            raise ValueError(f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_BYTES} bytes long in {self.environment}")
        return self

    @property
    def session_cookie_secure(self) -> bool:
        """Return whether the administrator session cookie is limited to HTTPS.

        Production is served over HTTPS, so the cookie is marked ``Secure``
        there only.  Local development runs on plain HTTP, where a ``Secure``
        cookie would never be stored by the browser.

        Returns:
            ``True`` when ``ENVIRONMENT=production``, otherwise ``False``.
        """
        return self.environment.strip().lower() == "production"


settings = Settings()


def describe_settings() -> dict[str, Any]:
    """Return a log-safe summary of the active configuration.

    Secrets are never included — only their presence is reported.

    Returns:
        A mapping with non-sensitive configuration details.
    """
    return {
        # Only the dialect is logged; the URL itself carries the password.
        "database": settings.database_url.split(":", 1)[0].split("+", 1)[0],
        "ai_provider": settings.ai_provider,
        "groq_key_present": bool(settings.groq_api_key),
        "gemini_key_present": bool(settings.gemini_api_key),
        "admin_password_hashed": bool(settings.admin_password_hash),
        "jwt_secret_is_default": settings.jwt_secret_key.startswith("dev-only-"),
    }
