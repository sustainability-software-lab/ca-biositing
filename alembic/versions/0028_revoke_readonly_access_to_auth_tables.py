"""Revoke biocirv_readonly access to auth tables (CBS-SEC-003)

Revision ID: 0028
Revises: 0027
Create Date: 2026-11-25

0002 grants biocirv_readonly SELECT on every table in public, plus default
privileges for future tables. Auth tables must stay unreadable by that role.
New auth tables need to be added to AUTH_TABLES in their own migration;
scripts/check_readonly_auth_grants.py fails CI if one is missed.

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0028"
down_revision: Union[str, Sequence[str], None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUTH_TABLES = ("api_user", "api_key")


def upgrade() -> None:
    for table in AUTH_TABLES:
        op.execute(
            f"DO $$ "
            f"DECLARE seq TEXT; "
            f"BEGIN "
            f"  REVOKE ALL ON TABLE public.{table} FROM biocirv_readonly; "
            f"  FOR seq IN SELECT pg_get_serial_sequence('public.{table}', a.attname) "
            f"    FROM pg_attribute a "
            f"    WHERE a.attrelid = 'public.{table}'::regclass AND a.attnum > 0 AND NOT a.attisdropped "
            f"      AND pg_get_serial_sequence('public.{table}', a.attname) IS NOT NULL "
            f"  LOOP "
            f"    EXECUTE format('REVOKE ALL ON SEQUENCE %s FROM biocirv_readonly', seq); "
            f"  END LOOP; "
            f"EXCEPTION WHEN undefined_object THEN NULL; "
            f"END $$"
        )


def downgrade() -> None:
    # Restores the table-level SELECT that 0002 granted; 0002 never granted sequences.
    for table in AUTH_TABLES:
        op.execute(
            f"DO $$ BEGIN "
            f"  GRANT SELECT ON TABLE public.{table} TO biocirv_readonly; "
            f"EXCEPTION WHEN undefined_object THEN NULL; "
            f"END $$"
        )
