"""Track the sweep's requeues and index the unanalysed reviews.

The periodic sweep puts reviews without an AI analysis back on the queue.
``analysis_requeues`` lets it give up on a review that can never be
analysed, and a partial index keeps its query cheap on a large table.

Revision ID: 004_add_requeue_tracking
Revises: 003_add_review_indexes
Create Date: 2026-10-28
"""

from alembic import op
import sqlalchemy as sa

# Alembic revision identifiers.
revision: str = "004_add_requeue_tracking"
down_revision: str = "003_add_review_indexes"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_reviews_unanalysed_created_at"
_CONDITION = sa.text("analyzed_at_utc IS NULL OR ai_draft_response IS NULL")


def upgrade() -> None:
    """Add the requeue counter and the partial index of unfinished reviews."""
    columns: set[str] = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("reviews")}
    if "analysis_requeues" not in columns:
        op.add_column(
            "reviews",
            sa.Column("analysis_requeues", sa.Integer(), nullable=False, server_default="0"),
        )

    indexes: set[str] = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("reviews")}
    if _INDEX_NAME not in indexes:
        op.create_index(
            _INDEX_NAME,
            "reviews",
            ["created_at_utc"],
            unique=False,
            postgresql_where=_CONDITION,
            sqlite_where=_CONDITION,
        )


def downgrade() -> None:
    """Drop the partial index and the requeue counter."""
    inspector = sa.inspect(op.get_bind())
    if _INDEX_NAME in {index["name"] for index in inspector.get_indexes("reviews")}:
        op.drop_index(_INDEX_NAME, table_name="reviews")
    if "analysis_requeues" in {column["name"] for column in inspector.get_columns("reviews")}:
        # batch mode rebuilds the table on SQLite, which cannot drop columns
        # in place on older versions; on Postgres it is a plain ALTER.
        with op.batch_alter_table("reviews") as batch:
            batch.drop_column("analysis_requeues")
