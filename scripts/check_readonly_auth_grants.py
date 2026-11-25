"""Fail if the biocirv_readonly role can read any auth table (CBS-SEC-003).

Auth tables are every SQLModel table registered by
``ca_biositing.datamodels.models.auth``, so new auth models are checked
automatically. Their owned sequences are checked too, as is the dedicated
auth schema itself (no USAGE, no default privileges for the role).

Usage:
    DATABASE_URL=postgresql+psycopg2://... python scripts/check_readonly_auth_grants.py
"""

from __future__ import annotations

import os
import sys

import sqlalchemy as sa

READONLY_ROLE = "biocirv_readonly"


def auth_table_names() -> list[str]:
    from sqlmodel import SQLModel

    from ca_biositing.datamodels.models import auth

    auth_modules = {
        getattr(auth, name).__module__
        for name in dir(auth)
        if isinstance(getattr(auth, name), type)
        and issubclass(getattr(auth, name), SQLModel)
    }
    names = set()
    for mapper in SQLModel._sa_registry.mappers:
        if mapper.class_.__module__ in auth_modules:
            table = mapper.local_table
            names.add(f"{table.schema or 'public'}.{table.name}")
    return sorted(names)


def find_schema_violations(conn: sa.Connection, schemas: set[str]) -> list[str]:
    """Dedicated auth schemas must grant the role no USAGE and no default privileges."""
    violations = []
    for schema in sorted(schemas - {"public"}):
        if conn.execute(
            sa.text("SELECT has_schema_privilege(:role, :s, 'USAGE')"),
            {"role": READONLY_ROLE, "s": schema},
        ).scalar():
            violations.append(f"schema {schema} (USAGE)")
        if conn.execute(
            sa.text(
                "SELECT 1 FROM pg_default_acl d, aclexplode(d.defaclacl) a "
                "WHERE d.defaclnamespace = CAST(:s AS regnamespace) "
                "AND a.grantee = CAST(:role AS regrole)"
            ),
            {"role": READONLY_ROLE, "s": schema},
        ).first():
            violations.append(f"schema {schema} (default privileges)")
    return violations


def find_violations(conn: sa.Connection, tables: list[str]) -> list[str]:
    violations = find_schema_violations(conn, {t.split(".", 1)[0] for t in tables})
    for qualified in tables:
        if conn.execute(
            sa.text("SELECT has_table_privilege(:role, :t, 'SELECT')"),
            {"role": READONLY_ROLE, "t": qualified},
        ).scalar():
            violations.append(f"table {qualified}")
        schema, table = qualified.split(".", 1)
        sequences = conn.execute(
            sa.text(
                "SELECT s.relnamespace::regnamespace::text || '.' || s.relname "
                "FROM pg_class s "
                "JOIN pg_depend d ON d.objid = s.oid AND d.deptype IN ('a', 'i') "
                "JOIN pg_class t ON t.oid = d.refobjid "
                "WHERE s.relkind = 'S' AND t.relname = :table "
                "AND t.relnamespace = CAST(:schema AS regnamespace)"
            ),
            {"table": table, "schema": schema},
        ).scalars()
        for seq in sequences:
            if conn.execute(
                sa.text(
                    "SELECT has_sequence_privilege(:role, :s, 'SELECT') "
                    "OR has_sequence_privilege(:role, :s, 'USAGE')"
                ),
                {"role": READONLY_ROLE, "s": seq},
            ).scalar():
                violations.append(f"sequence {seq}")
    return violations


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    tables = auth_table_names()
    if not tables:
        print("No auth tables found in ca_biositing.datamodels.models.auth", file=sys.stderr)
        return 2

    engine = sa.create_engine(url)
    with engine.connect() as conn:
        role_exists = conn.execute(
            sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"),
            {"role": READONLY_ROLE},
        ).scalar()
        if not role_exists:
            print(f"Role {READONLY_ROLE} does not exist; nothing was verified", file=sys.stderr)
            return 2
        violations = find_violations(conn, tables)

    if violations:
        print(f"{READONLY_ROLE} can read auth objects:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print(f"OK: {READONLY_ROLE} cannot read auth tables: {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
