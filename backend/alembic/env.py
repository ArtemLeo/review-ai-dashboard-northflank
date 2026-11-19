"""Alembic migration environment configuration.

This module configures the database connection and metadata for running
schema migrations both offline (generating SQL scripts) and online (applying
changes directly to the target database).
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure project root is in sys.path to import application modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.alembic_url import escape_interpolation
from app.core.config import settings
from app.db.base_class import Base
from app.models.review import Review  # noqa: F401  # registers the model metadata

# Alembic Config object provides access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the application settings database URL.  The
# config parser treats "%" as interpolation, so a password containing one
# would crash every migration unless it is escaped here.
config.set_main_option("sqlalchemy.url", escape_interpolation(settings.database_url))

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine,
    generating SQL execution scripts without connecting to a live database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context
    to apply migrations directly to the database.
    """
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
