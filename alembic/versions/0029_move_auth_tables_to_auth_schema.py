"""Move auth tables into a dedicated auth schema (#580)

Revision ID: 0029
Revises: 0028
Create Date: 2026-11-25

biocirv_readonly gets no USAGE on the auth schema and no default privileges
there, so every table created in auth (now and in the future) is unreadable by
that role by design rather than by per-table revokes. scripts/
check_readonly_auth_grants.py enforces this in CI.

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: Union[str, Sequence[str], None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUTH_TABLES = ("api_user", "api_key")
APP_ROLE = "biocirv_user"
READONLY_ROLE = "biocirv_readonly"
# SQLModel prefixes index names with the table's schema.
INDEX_RENAMES = (
    ("ix_api_user_username", "ix_auth_api_user_username"),
    ("ix_api_key_api_user_id", "ix_auth_api_key_api_user_id"),
    ("ix_api_key_key_prefix", "ix_auth_api_key_key_prefix"),
)


def _ignore_missing_role(sql: str) -> str:
    return f"DO $$ BEGIN {sql} EXCEPTION WHEN undefined_object THEN NULL; END $$"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute("REVOKE ALL ON SCHEMA auth FROM PUBLIC")

    # Owned sequences, indexes, and constraints move with each table.
    for table in AUTH_TABLES:
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA auth")
    for old, new in INDEX_RENAMES:
        op.execute(f"ALTER INDEX auth.{old} RENAME TO {new}")

    # The app role (which may also be the migration role) needs full access to
    # current and future auth objects; owner-held rights make these no-ops.
    op.execute(
        _ignore_missing_role(
            f"GRANT USAGE, CREATE ON SCHEMA auth TO {APP_ROLE}; "
            f"GRANT ALL ON ALL TABLES IN SCHEMA auth TO {APP_ROLE}; "
            f"GRANT ALL ON ALL SEQUENCES IN SCHEMA auth TO {APP_ROLE}; "
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON TABLES TO {APP_ROLE}; "
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON SEQUENCES TO {APP_ROLE};"
        )
    )

    op.execute(
        _ignore_missing_role(
            f"REVOKE ALL ON SCHEMA auth FROM {READONLY_ROLE}; "
            f"REVOKE ALL ON ALL TABLES IN SCHEMA auth FROM {READONLY_ROLE}; "
            f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA auth FROM {READONLY_ROLE};"
        )
    )


def downgrade() -> None:
    # Table-level revokes from 0028 travel with the tables, so they stay
    # unreadable by the read-only role back in public.
    for old, new in INDEX_RENAMES:
        op.execute(f"ALTER INDEX auth.{new} RENAME TO {old}")
    for table in reversed(AUTH_TABLES):
        op.execute(f"ALTER TABLE auth.{table} SET SCHEMA public")

    op.execute(
        _ignore_missing_role(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA auth REVOKE ALL ON TABLES FROM {APP_ROLE}; "
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA auth REVOKE ALL ON SEQUENCES FROM {APP_ROLE};"
        )
    )
    op.execute("DROP SCHEMA auth")
