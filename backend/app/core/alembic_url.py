"""Helpers for passing a database URL through Alembic's configuration parser.

Alembic's :class:`alembic.config.Config` wraps a :class:`configparser.
ConfigParser`, which treats ``%`` as the start of an interpolation expression.
A database password containing a percent sign therefore makes the parser
raise ``ValueError: invalid interpolation syntax`` before a single migration
runs, which leaves the container in a crash loop.

The helper here escapes the URL on the way in, and the parser gives the
original value back on the way out, so the URL that reaches SQLAlchemy is byte-for-byte the one
that was configured.
"""

#: Character that the configuration parser treats as an interpolation marker.
_INTERPOLATION_MARKER = "%"


def escape_interpolation(value: str) -> str:
    """Escape percent signs so a value survives the configuration parser.

    Args:
        value: The raw value to hand to the configuration parser.

    Returns:
        The value with every percent sign doubled.  Reading it back with
        interpolation enabled restores the original string.
    """
    return value.replace(_INTERPOLATION_MARKER, _INTERPOLATION_MARKER * 2)
