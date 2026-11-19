"""Convert reviews.rating column from String to Integer.

Reason: rating was stored as VARCHAR which caused lexicographic sorting
("2" > "10"). Changing to INTEGER ensures correct numeric ORDER BY.

Revision ID: 002_rating_string_to_integer
Revises: 001
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa

# Alembic revision identifiers.
revision: str = "002_rating_string_to_integer"
down_revision: str = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert rating column from VARCHAR to INTEGER.

    For SQLite (dev) we recreate the column via batch mode because SQLite
    does not support ALTER COLUMN TYPE directly.  For PostgreSQL (prod) the
    same batch approach works transparently.

    The conversion is skipped when the column is already an integer, which
    is the case for databases that were created from the current model
    definition before Alembic took over the schema.
    """
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("reviews"):
        return

    columns = {column["name"]: column for column in inspector.get_columns("reviews")}
    rating_column = columns.get("rating")
    if rating_column is None:
        return

    existing_type = rating_column["type"]
    if isinstance(existing_type, sa.Integer):
        return

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column(
            "rating",
            existing_type=sa.String(50),
            type_=sa.Integer(),
            existing_nullable=True,
            # Cast existing string values ("1"–"5") to integer.
            postgresql_using="rating::integer",
        )


def downgrade() -> None:
    """Revert rating column from INTEGER back to VARCHAR(50)."""
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("reviews"):
        return

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column(
            "rating",
            existing_type=sa.Integer(),
            type_=sa.String(50),
            existing_nullable=True,
            postgresql_using="rating::varchar",
        )

