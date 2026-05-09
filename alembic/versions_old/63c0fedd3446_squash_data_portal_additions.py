"""squash_data_portal_additions

Revision ID: 63c0fedd3446
Revises: 9c4731d7e6f5
Create Date: 2026-03-26 16:36:15.776754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '63c0fedd3446'
down_revision: Union[str, Sequence[str], None] = '9c4731d7e6f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add uri to resource
    op.add_column('resource', sa.Column('uri', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # Create data_portal schema
    op.execute("CREATE SCHEMA IF NOT EXISTS data_portal")

    # Note: Materialized views are created in later migrations after all required tables exist


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA IF EXISTS data_portal CASCADE")
    op.drop_column('resource', 'uri')
