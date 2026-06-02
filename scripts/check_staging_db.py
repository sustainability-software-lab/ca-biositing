
import os
from sqlalchemy import text
from ca_biositing.datamodels.database import get_engine

# Force staging env if not set (just for this check)
os.environ["DATABASE_URL"] = "postgresql://postgres:GPmWCFk6zsFIj2FdO7DzzLOddjNrQJhR@localhost:5434/biocirv-staging"

engine = get_engine()
with engine.connect() as conn:
    print("--- Schemas and Owners ---")
    result = conn.execute(text("SELECT nspname as schema_name, rolname as owner FROM pg_namespace n JOIN pg_roles r ON n.nspowner = r.oid WHERE nspname NOT LIKE 'pg_%%' AND nspname != 'information_schema';"))
    for row in result:
        print(f"{row[0]}: {row[1]}")

    print("\n--- Tables in data_portal ---")
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'data_portal';"))
    for row in result:
        print(row[0])

    print("\n--- Index Owner (idx_mv_biomass_search_id) ---")
    sql = """
    SELECT u.rolname as owner
    FROM pg_class i
    JOIN pg_roles u ON u.oid = i.relowner
    JOIN pg_namespace n ON n.oid = i.relnamespace
    WHERE n.nspname = 'data_portal' AND i.relname = 'idx_mv_biomass_search_id';
    """
    result = conn.execute(text(sql))
    row = result.fetchone()
    if row:
        print(f"Owner: {row[0]}")
    else:
        print("Index not found.")
