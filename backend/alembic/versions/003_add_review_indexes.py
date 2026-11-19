"""Add indexes for admin list filtering and sorting.

The admin review list filters on ``analysis_status``, ``rating`` and
``priority`` and sorts by ``created_at_utc``.  Without indexes every page
request triggered a sequential scan of the whole table.

Revision ID: 003_add_review_indexes
Revises: 002_rating_string_to_integer
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa

# Alembic revision identifiers.
revision: str = "003_add_review_indexes"
down_revision: str = "002_rating_string_to_integer"
branch_labels = None
depends_on = None

#: Indexes created by this migration, as ``(name, columns)`` pairs.  The
#: ``created_at_utc`` index belongs to migration 001, so the downgrade of
#: this one leaves it in place.
_INDEXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ix_reviews_analysis_status", ("analysis_status",)),
    ("ix_reviews_rating", ("rating",)),
    ("ix_reviews_priority", ("priority",)),
    ("ix_reviews_status_created_at", ("analysis_status", "created_at_utc")),
)


def upgrade() -> None:
    """Create the filtering/sorting indexes on the reviews table.

    Indexes that already exist are skipped, so the migration is safe to
    re-run against a database that was created with ``create_all``.
    """
    existing: set[str] = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("reviews")
    }
    for name, columns in _INDEXES:
        if name in existing:
            continue
        op.create_index(name, "reviews", list(columns), unique=False)


def downgrade() -> None:
    """Drop the indexes created by :func:`upgrade`."""
    existing: set[str] = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("reviews")
    }
    for name, _columns in reversed(_INDEXES):
        if name in existing:
            op.drop_index(name, table_name="reviews")
