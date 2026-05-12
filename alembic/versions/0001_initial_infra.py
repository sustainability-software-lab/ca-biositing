"""Initial Infrastructure: Extensions and Schemas

Revision ID: 0001
Revises:
Create Date: 2024-05-08 18:24:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")

    # Schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS ca_biositing")
    op.execute("CREATE SCHEMA IF NOT EXISTS data_portal")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS data_portal CASCADE")
    op.execute("DROP SCHEMA IF EXISTS ca_biositing CASCADE")

    op.execute("DROP EXTENSION IF EXISTS btree_gin")
    op.execute("DROP EXTENSION IF EXISTS unaccent")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
