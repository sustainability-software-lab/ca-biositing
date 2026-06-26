import os
from sqlalchemy import text
from ca_biositing.datamodels.database import get_engine

def get_schema_details():
    os.environ["POSTGRES_HOST"] = "localhost"
    engine = get_engine()
    with engine.connect() as conn:
        # Get all views in data_portal schema
        views_result = conn.execute(text("""
            SELECT matviewname as table_name
            FROM pg_matviews
            WHERE schemaname = 'data_portal'
            ORDER BY matviewname;
        """))

        views = [row.table_name for row in views_result]

        print("# Data Dictionary: Materialized Views\n")
        print("This document outlines the schema for the core materialized views in the `data_portal` schema. These views are optimized for read performance and are the primary data source for the web service and data portal.\n")

        for view in views:
            print(f"## {view}")

            # Try to get view description from pg_description
            desc_result = conn.execute(text(f"""
                SELECT obj_description(c.oid)
                FROM pg_class c
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = 'data_portal' AND c.relname = '{view}';
            """)).scalar()

            if desc_result:
                print(f"{desc_result}\n")

            print("| Column Name | Data Type | Description |")
            print("| :--- | :--- | :--- |")

            columns_result = conn.execute(text(f"""
                SELECT a.attname as column_name,
                       pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                       col_description(a.attrelid, a.attnum) as column_comment
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
                JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = 'data_portal'
                  AND c.relname = '{view}'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY a.attnum;
            """))

            for col in columns_result:
                desc = col.column_comment if col.column_comment else ""
                print(f"| `{col.column_name}` | {col.data_type} | {desc} |")
            print("\n")

if __name__ == "__main__":
    get_schema_details()
