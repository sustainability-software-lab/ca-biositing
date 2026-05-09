"""grant data_portal readonly permissions

Revision ID: 60b08397200f
Revises: 63c0fedd3446
Create Date: 2026-04-01 16:47:36.887796

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '60b08397200f'
down_revision: Union[str, Sequence[str], None] = '63c0fedd3446'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Grant SELECT privileges to biocirv_readonly on data_portal schema."""
    # Ensure the role exists (mirrors behavior from 0002 migration).
    op.execute(
        "DO $$ BEGIN"
        " CREATE ROLE biocirv_readonly WITH LOGIN;"
        " EXCEPTION WHEN duplicate_object THEN NULL;"
        " END $$"
    )

    op.execute("GRANT USAGE ON SCHEMA data_portal TO biocirv_readonly")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA data_portal TO biocirv_readonly")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE biocirv_user IN SCHEMA data_portal"
        " GRANT SELECT ON TABLES TO biocirv_readonly"
    )


def downgrade() -> None:
    """Revoke SELECT privileges from biocirv_readonly on data_portal schema."""
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE biocirv_user IN SCHEMA data_portal"
        " REVOKE SELECT ON TABLES FROM biocirv_readonly"
    )
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA data_portal FROM biocirv_readonly")
    op.execute("REVOKE USAGE ON SCHEMA data_portal FROM biocirv_readonly")
