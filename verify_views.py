import sqlalchemy as sa
from sqlalchemy import inspect

# Connection string based on observed pixi commands
# POSTGRES_HOST=localhost is needed as seen in previous commands
db_url = "postgresql://biocirv_user:biocirv_dev_password@localhost:5432/biocirv_db"

engine = sa.create_engine(db_url)

try:
    with engine.connect() as conn:
        print("Connected to database.")

        # Check schema
        result = conn.execute(sa.text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'data_portal';"))
        schema = result.fetchone()
        if schema:
            print(f"Schema 'data_portal' exists.")
        else:
            print(f"Schema 'data_portal' DOES NOT exist.")

        # Check materialized views
        result = conn.execute(sa.text("SELECT matviewname FROM pg_matviews WHERE schemaname = 'data_portal';"))
        views = [row[0] for row in result.fetchall()]

        expected_views = [
            "mv_biomass_search",
            "mv_biomass_composition",
            "mv_biomass_county_production",
            "mv_biomass_availability",
            "mv_biomass_sample_stats",
            "mv_biomass_fermentation",
            "mv_biomass_gasification",
            "mv_biomass_pricing"
        ]

        print(f"Found {len(views)} materialized views in 'data_portal':")
        for v in views:
            print(f" - {v}")

        missing = set(expected_views) - set(views)
        if missing:
            print(f"MISSING views: {missing}")
        else:
            print("All expected views are present.")

        # Verify columns for mv_biomass_sample_stats
        print("\nVerifying columns for mv_biomass_sample_stats...")
        inspector = inspect(engine)
        columns = inspector.get_columns("mv_biomass_sample_stats", schema="data_portal")
        column_names = [c['name'] for c in columns]
        print(f"Columns: {column_names}")

        if "resource_name" in column_names:
            print("SUCCESS: resource_name column found!")
        else:
            print("FAILURE: resource_name column NOT found!")

except Exception as e:
    print(f"Error: {e}")
