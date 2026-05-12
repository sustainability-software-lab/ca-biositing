"""Create PostgreSQL extensions

Revision ID: 0001_create_extensions
Revises:
Create Date: 2026-02-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001_create_extensions'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable required PostgreSQL extensions."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    """Disable PostgreSQL extensions."""
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
