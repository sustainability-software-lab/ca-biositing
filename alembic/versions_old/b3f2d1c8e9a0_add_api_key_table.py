"""Add api_key table

Revision ID: b3f2d1c8e9a0
Revises: 60b08397200f
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'b3f2d1c8e9a0'
down_revision: Union[str, Sequence[str], None] = '60b08397200f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add api_key table for per-client API key authentication."""
    op.create_table(
        'api_key',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('key_prefix', sqlmodel.sql.sqltypes.AutoString(length=8), nullable=False),
        sa.Column('key_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('rate_window_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rate_window_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['api_user_id'], ['api_user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )
    op.create_index(op.f('ix_api_key_api_user_id'), 'api_key', ['api_user_id'], unique=False)
    op.create_index(op.f('ix_api_key_key_prefix'), 'api_key', ['key_prefix'], unique=False)


def downgrade() -> None:
    """Drop api_key table."""
    op.drop_index(op.f('ix_api_key_key_prefix'), table_name='api_key')
    op.drop_index(op.f('ix_api_key_api_user_id'), table_name='api_key')
    op.drop_table('api_key')
