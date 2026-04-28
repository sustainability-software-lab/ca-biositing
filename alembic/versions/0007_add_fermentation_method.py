"""Add duration column to method table and genus/species/strain columns to strain table.

Revision ID: 0007a2cc5f91
Revises: d2b6b2a7c9d1
Create Date: 2026-04-27 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007a2cc5f91"
down_revision: Union[str, Sequence[str], None] = "d2b6b2a7c9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable duration field to method records and taxonomy columns to strain table."""
    op.add_column("method", sa.Column("duration", sa.Float(), nullable=True))
    op.add_column("strain", sa.Column("genus", sa.String(), nullable=True))
    op.add_column("strain", sa.Column("species", sa.String(), nullable=True))
    op.add_column("strain", sa.Column("strain", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove duration field from method records and taxonomy columns from strain table."""
    op.drop_column("method", "duration")
    # Use IF EXISTS so downgrade is safe even if columns were never applied
    # (e.g. when rolling back an in-place edit of this revision on an unmerged branch)
    op.execute("ALTER TABLE strain DROP COLUMN IF EXISTS genus")
    op.execute("ALTER TABLE strain DROP COLUMN IF EXISTS species")
    op.execute("ALTER TABLE strain DROP COLUMN IF EXISTS strain")
