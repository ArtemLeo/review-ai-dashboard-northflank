"""Initial create

Revision ID: 001
Revises:
Create Date: 2026-10-17 16:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the ``reviews`` table, or adopt it when it already exists.

    Databases created by an older version of the application (which built the
    schema at runtime with ``create_all``) already contain the table but have
    no Alembic revision recorded.  Creating it a second time would abort the
    upgrade, so the table is adopted as-is and the following migrations bring
    it up to the current schema.
    """
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("reviews"):
        return

    op.create_table(
        'reviews',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('author_name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('created_at_utc', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('analysis_status', sa.String(length=50), nullable=False),
        sa.Column('rating', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('needs_urgent_response', sa.Boolean(), nullable=True),
        sa.Column('ai_analysis_provider', sa.String(length=100), nullable=True),
        sa.Column('ai_analysis_model', sa.String(length=100), nullable=True),
        sa.Column('ai_draft_response', sa.Text(), nullable=True),
        sa.Column('ai_draft_response_provider', sa.String(length=100), nullable=True),
        sa.Column('ai_draft_response_model', sa.String(length=100), nullable=True),
        sa.Column('analyzed_at_utc', sa.DateTime(), nullable=True),
        sa.Index('ix_reviews_created_at_utc', 'created_at_utc')
    )


def downgrade() -> None:
    """Drop the ``reviews`` table."""
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("reviews"):
        return
    op.drop_table('reviews')
