"""Logging configuration for the Review AI Dashboard.

Logs are emitted to ``stdout`` by default (the hosting platform shows them in
its Logs tab) and a rotating file handler is added only when an explicit
``LOG_FILE`` environment variable is provided.  Rotating at 5 MiB with 3
backups keeps the filesystem footprint bounded.
"""

import logging
import os
import sys
from logging.config import dictConfig
from typing import Any

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_LEVEL_ENV = "LOG_LEVEL"
_LOG_FILE_ENV = "LOG_FILE"
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB
_DEFAULT_BACKUP_COUNT = 3


def _resolve_level() -> int:
    """Return the numeric log level from the ``LOG_LEVEL`` env var.

    Returns:
        The resolved :mod:`logging` level, defaulting to ``INFO``.
    """
    level_name = os.getenv(_LOG_LEVEL_ENV, "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def _build_handlers() -> dict[str, dict[str, Any]]:
    """Build the handler definitions for the root logger.

    A ``stdout`` handler is always present.  A rotating file handler is added
    only when ``LOG_FILE`` is set.  The path is not checked here: when it is
    not writable, :func:`setup_logging` raises and the process does not start.

    Returns:
        A mapping of handler names to :func:`dictConfig` handler definitions.
    """
    handlers: dict[str, dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "default",
        }
    }

    log_file = os.getenv(_LOG_FILE_ENV, "").strip()
    if log_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "maxBytes": _DEFAULT_MAX_BYTES,
            "backupCount": _DEFAULT_BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "default",
        }

    return handlers


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


def setup_logging() -> None:
    """Configure the root logger.

    Safe to call more than once — :func:`dictConfig` replaces the previous
    handler set, so no duplicate or dangling handlers are left behind.
    """
    handlers = _build_handlers()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": LOG_FORMAT}},
            "handlers": handlers,
            "root": {
                "handlers": list(handlers),
                "level": _resolve_level(),
            },
        }
    )
