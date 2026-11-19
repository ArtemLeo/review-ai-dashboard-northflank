"""Remember when the sweep last put a review back on the queue.

The sweep waits a full stale period after each requeue, not only after the
submission, so a requeued run that is still retrying is never queued again.

Revision ID: 005_add_last_requeued_at
Revises: 004_add_requeue_tracking
Create Date: 2026-10-29
"""

from alembic import op
import sqlalchemy as sa

# Alembic revision identifiers.
revision: str = "005_add_last_requeued_at"
down_revision: str = "004_add_requeue_tracking"
branch_labels = None
depends_on = None

_COLUMN = "last_requeued_at_utc"


def upgrade() -> None:
    """Add the time of the last requeue."""
    columns: set[str] = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("reviews")}
    if _COLUMN not in columns:
        op.add_column("reviews", sa.Column(_COLUMN, sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Drop the time of the last requeue."""
    columns: set[str] = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("reviews")}
    if _COLUMN in columns:
        # batch mode rebuilds the table on SQLite, which cannot drop columns
        # in place on older versions; on Postgres it is a plain ALTER.
        with op.batch_alter_table("reviews") as batch:
            batch.drop_column(_COLUMN)
