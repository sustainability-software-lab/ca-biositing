"""Grant readonly permissions to biocirv_readonly

Revision ID: 0002_grant_readonly_permissions
Revises: 923d39b6c4da
Create Date: 2026-02-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002_grant_readonly_permissions'
down_revision: Union[str, Sequence[str], None] = '923d39b6c4da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Grant SELECT privileges to the biocirv_readonly role on ca_biositing and public schemas."""
    # Ensure biocirv_readonly role exists (may not exist in local dev).
    # PostgreSQL has no CREATE ROLE IF NOT EXISTS, so use exception handler.
    op.execute(
        "DO $$ BEGIN"
        " CREATE ROLE biocirv_readonly WITH LOGIN;"
        " EXCEPTION WHEN duplicate_object THEN NULL;"
        " END $$"
    )

    # ca_biositing schema
    op.execute("GRANT USAGE ON SCHEMA ca_biositing TO biocirv_readonly")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA ca_biositing TO biocirv_readonly")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE biocirv_user IN SCHEMA ca_biositing"
        " GRANT SELECT ON TABLES TO biocirv_readonly"
    )

    # public schema
    op.execute("GRANT USAGE ON SCHEMA public TO biocirv_readonly")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO biocirv_readonly")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE biocirv_user IN SCHEMA public"
        " GRANT SELECT ON TABLES TO biocirv_readonly"
    )


def downgrade() -> None:
    """Revoke SELECT privileges from biocirv_readonly."""
    # ca_biositing schema
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE biocirv_user IN SCHEMA ca_biositing"
        " REVOKE SELECT ON TABLES FROM biocirv_readonly"
    )
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA ca_biositing FROM biocirv_readonly")
    op.execute("REVOKE USAGE ON SCHEMA ca_biositing FROM biocirv_readonly")

    # public schema
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE biocirv_user IN SCHEMA public"
        " REVOKE SELECT ON TABLES FROM biocirv_readonly"
    )
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM biocirv_readonly")
    op.execute("REVOKE USAGE ON SCHEMA public FROM biocirv_readonly")
