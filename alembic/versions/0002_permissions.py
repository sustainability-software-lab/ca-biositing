"""Permissions: Roles and Grants

Revision ID: 0002
Revises: 0001
Create Date: 2024-05-08 18:25:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure biocirv_readonly role exists
    op.execute(
        "DO $$ BEGIN"
        " CREATE ROLE biocirv_readonly WITH LOGIN;"
        " EXCEPTION WHEN duplicate_object THEN NULL;"
        " END $$"
    )

    # We apply default privileges for both the standard app user and postgres
    # to ensure coverage in both Cloud (biocirv_user) and local dev (often postgres).
    for schema in ["public", "ca_biositing", "data_portal"]:
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO biocirv_readonly")
        op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO biocirv_readonly")

        for owner in ["biocirv_user", "postgres"]:
            op.execute(
                f"DO $$ BEGIN "
                f"  EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON TABLES TO biocirv_readonly', '{owner}', '{schema}'); "
                f"EXCEPTION "
                f"  WHEN undefined_object THEN NULL; "
                f"  WHEN insufficient_privilege THEN "
                f"    RAISE NOTICE 'Skipping ALTER DEFAULT PRIVILEGES for role % due to insufficient privileges', '{owner}'; "
                f"END $$"
            )


def downgrade() -> None:
    for schema in ["public", "ca_biositing", "data_portal"]:
        for owner in ["biocirv_user", "postgres"]:
            op.execute(
                f"DO $$ BEGIN "
                f"  ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA {schema} "
                f"  REVOKE SELECT ON TABLES FROM biocirv_readonly; "
                f"EXCEPTION WHEN undefined_object THEN NULL; "
                f"END $$"
            )
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM biocirv_readonly")
        op.execute(f"REVOKE USAGE ON SCHEMA {schema} FROM biocirv_readonly")
