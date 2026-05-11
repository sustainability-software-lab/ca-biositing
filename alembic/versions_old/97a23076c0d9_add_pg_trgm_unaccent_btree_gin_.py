"""add_pg_trgm_unaccent_btree_gin_extensions

Revision ID: 97a23076c0d9
Revises: 0002_grant_readonly_permissions
Create Date: 2026-02-23 14:48:29.663433

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '97a23076c0d9'
down_revision: Union[str, Sequence[str], None] = '0002_grant_readonly_permissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pg_trgm, unaccent, and btree_gin extensions."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")


def downgrade() -> None:
    """Remove pg_trgm, unaccent, and btree_gin extensions."""
    op.execute("DROP EXTENSION IF EXISTS btree_gin")
    op.execute("DROP EXTENSION IF EXISTS unaccent")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
