"""Add ResidueFactor model and volume estimation materialized views

Revision ID: consolidated_base_residue
Revises: d2b6b2a7c9d1
Create Date: 2026-04-24 15:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'consolidated_base_residue'
down_revision: Union[str, Sequence[str], None] = 'd2b6b2a7c9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add residue_factor table and update resource_image constraints."""
    op.create_table('residue_factor',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('etl_run_id', sa.Integer(), nullable=True),
    sa.Column('lineage_group_id', sa.Integer(), nullable=True),
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('resource_name', sa.String(), nullable=True),
    sa.Column('data_source_id', sa.Integer(), nullable=True),
    sa.Column('factor_type', sa.String(), nullable=True),
    sa.Column('factor_min', sa.Numeric(), nullable=True),
    sa.Column('factor_max', sa.Numeric(), nullable=True),
    sa.Column('factor_mid', sa.Numeric(), nullable=True),
    sa.Column('prune_trim_yield', sa.Numeric(), nullable=True),
    sa.Column('prune_trim_yield_unit_id', sa.Integer(), nullable=True),
    sa.Column('notes', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['data_source_id'], ['data_source.id'], ),
    sa.ForeignKeyConstraint(['etl_run_id'], ['etl_run.id'], ),
    sa.ForeignKeyConstraint(['prune_trim_yield_unit_id'], ['unit.id'], ),
    sa.ForeignKeyConstraint(['resource_id'], ['resource.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('resource_id', 'factor_type', name='uq_residue_factor_resource_id_factor_type')
    )

    # Ensure resource_id is NOT NULL in resource_image
    op.alter_column('resource_image', 'resource_id',
               existing_type=sa.Integer(),
               nullable=False)

    # Update resource_image constraints
    op.drop_constraint('resource_image_resource_id_image_url_key', 'resource_image', type_='unique')
    op.create_unique_constraint('resource_image_name_url_sort_key', 'resource_image', ['resource_name', 'image_url', 'sort_order'])


def downgrade() -> None:
    """Downgrade schema: drop residue_factor table and restore resource_image constraints."""
    # Restore resource_id nullability
    op.alter_column('resource_image', 'resource_id',
               existing_type=sa.Integer(),
               nullable=True)

    op.drop_constraint('resource_image_name_url_sort_key', 'resource_image', type_='unique')
    op.create_unique_constraint('resource_image_resource_id_image_url_key', 'resource_image', ['resource_id', 'image_url'])
    op.drop_table('residue_factor')
