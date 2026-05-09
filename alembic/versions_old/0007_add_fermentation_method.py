"""Add duration column to method table and genus/species/strain columns to strain table.

Revision ID: 0007a2cc5f91
Revises: consolidated_views_volume
Create Date: 2026-04-27 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007a2cc5f91"
down_revision: Union[str, Sequence[str], None] = "consolidated_views_volume"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add bioconversion_method table and updated strain/fermentation columns."""
    op.add_column("method", sa.Column("duration", sa.Float(), nullable=True))
    op.add_column("strain", sa.Column("genus", sa.String(), nullable=True))
    op.add_column("strain", sa.Column("species", sa.String(), nullable=True))
    op.add_column("strain", sa.Column("strain", sa.String(), nullable=True))
    op.add_column("strain", sa.Column("note", sa.String(), nullable=True))

    op.create_table(
        "bioconversion_method",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("etl_run_id", sa.Integer(), nullable=True),
        sa.Column("lineage_group_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("strain_id", sa.Integer(), nullable=True),
        sa.Column("strain_name", sa.String(), nullable=True),
        sa.Column("inoculum_volume_L", sa.Float(), nullable=True),
        sa.Column("reaction_volume_L", sa.Float(), nullable=True),
        sa.Column("temperature_C", sa.Float(), nullable=True),
        sa.Column("time_h", sa.Float(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("protocol_url", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["etl_run_id"], ["etl_run.id"]),
        sa.ForeignKeyConstraint(["strain_id"], ["strain.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.add_column(
        "fermentation_record",
        sa.Column("bioconversion_method_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fermentation_record_bioconversion_method_id_fkey",
        "fermentation_record",
        "bioconversion_method",
        ["bioconversion_method_id"],
        ["id"],
    )


def downgrade() -> None:
    """Remove bioconversion_method table and revert strain/fermentation changes."""
    op.execute(
        "ALTER TABLE fermentation_record DROP CONSTRAINT IF EXISTS fermentation_record_bioconversion_method_id_fkey"
    )
    op.execute("ALTER TABLE fermentation_record DROP COLUMN IF EXISTS bioconversion_method_id")
    op.execute("DROP TABLE IF EXISTS bioconversion_method")
    op.execute("ALTER TABLE strain DROP COLUMN IF EXISTS note")

    op.execute("ALTER TABLE method DROP COLUMN IF EXISTS duration")
    # Use IF EXISTS so downgrade is safe even if columns were never applied
    op.execute("ALTER TABLE strain DROP COLUMN IF EXISTS genus")
    op.execute("ALTER TABLE strain DROP COLUMN IF EXISTS species")
    op.execute("ALTER TABLE strain DROP COLUMN IF EXISTS strain")
