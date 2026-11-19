"""Tests for passing a database URL through Alembic's configuration parser."""

import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config

from app.core.alembic_url import escape_interpolation

#: A URL whose password contains a percent sign, which the configuration
#: parser would otherwise read as the start of an interpolation expression.
URL_WITH_PERCENT = "postgresql+psycopg://reviews:p%40ss@postgres:5432/reviews_db"


def test_escape_interpolation_doubles_the_percent_sign() -> None:
    """A percent sign is doubled so the parser accepts the value."""
    assert escape_interpolation(URL_WITH_PERCENT) == ("postgresql+psycopg://reviews:p%%40ss@postgres:5432/reviews_db")


def test_escape_interpolation_leaves_a_clean_url_untouched() -> None:
    """A URL without a percent sign is returned unchanged."""
    url = "postgresql+psycopg://reviews:secret@postgres:5432/reviews_db"

    assert escape_interpolation(url) == url


def test_alembic_config_accepts_a_url_with_a_percent_sign() -> None:
    """Setting the URL no longer raises an interpolation error.

    This was the crash that kept the container in a restart loop: the start
    script runs ``alembic upgrade head`` under ``set -e``.
    """
    config = Config("alembic.ini")

    config.set_main_option("sqlalchemy.url", escape_interpolation(URL_WITH_PERCENT))

    assert config.get_main_option("sqlalchemy.url") == URL_WITH_PERCENT


def test_alembic_section_returns_the_original_url() -> None:
    """The section rebuilt from the configuration keeps the real URL.

    The section is what the online migration path hands to SQLAlchemy, so it
    must carry the single percent sign rather than the escaped one.
    """
    config = Config("alembic.ini")

    config.set_main_option("sqlalchemy.url", escape_interpolation(URL_WITH_PERCENT))
    section = config.get_section(config.config_ini_section, {})

    assert section["sqlalchemy.url"] == URL_WITH_PERCENT


def test_alembic_config_accepts_a_url_without_a_percent_sign() -> None:
    """The common case keeps working unchanged."""
    config = Config("alembic.ini")
    url = "postgresql+psycopg://reviews:secret@postgres:5432/reviews_db"

    config.set_main_option("sqlalchemy.url", escape_interpolation(url))

    assert config.get_main_option("sqlalchemy.url") == url


def test_migrations_run_with_a_percent_sign_in_the_password() -> None:
    """The real env.py accepts such a URL (offline mode, no database needed).

    The helper above is only useful if env.py actually applies it.  The empty
    ``head:head`` range runs env.py completely without running a migration.
    """
    backend_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head:head", "--sql"],
        cwd=backend_root,
        env={**os.environ, "DATABASE_URL": URL_WITH_PERCENT},
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
