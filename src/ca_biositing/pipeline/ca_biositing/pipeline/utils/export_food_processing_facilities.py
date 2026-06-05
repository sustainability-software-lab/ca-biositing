"""
Food Processing Facilities CSV Exporter
---
Dumps the current contents of `infrastructure_food_processing_facilities`
to a stable CSV seed file.

Run this AFTER the ETL has populated / updated the table:

    pixi run python src/ca_biositing/pipeline/ca_biositing/pipeline/utils/export_food_processing_facilities.py

The output file is written to:

    src/ca_biositing/pipeline/ca_biositing/pipeline/utils/seed_food_processor_facilities.csv

That path is intentional — it sits next to the other seed files in utils/
and can be committed as a stable geocoded snapshot for use by future ETL runs.
"""

import os
import sys
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from ca_biositing.pipeline.utils.engine import get_engine

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TABLE_NAME = "infrastructure_food_processing_facilities"

# Output path: same utils/ directory as this script
_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_PATH = os.path.join(_UTILS_DIR, "seed_food_processor_facilities.csv")

# Columns to export (all model columns in declaration order).
# Keeping this explicit makes the seed file schema stable even if the DB
# gains new columns in the future.
EXPORT_COLUMNS = [
    "processing_facility_id",
    "name",
    "address",
    "city",
    "county",
    "zip",
    "state",
    "latitude",
    "longitude",
    "geom",
    "primary_ag_product",
    "process_type",
    "byproducts",
    "quantities",
    "processing_capacity_products",
    "processing_capacity_ton_hr",
    "general_source_info",
    "source_url",
    "CARB_facility_id",
    "air_district",
    "EPA_facility_id",
    "NAICS_code",
    "NAICS_code_description",
    "phone_number",
    "website",
    "excess_food_estimate_low",
    "excess_food_estimate_high",
    "etl_run_id",
    "lineage_group_id",
    "created_at",
    "updated_at",
    "geocode_status"
]


# ---------------------------------------------------------------------------
# Export function
# ---------------------------------------------------------------------------


def export_food_processing_facilities(
    output_path: str = DEFAULT_OUTPUT_PATH,
    engine=None,
) -> str:
    """
    Query ``infrastructure_food_processing_facilities`` and write a CSV.

    Args:
        output_path: Destination CSV path. Defaults to
            ``utils/seed_food_processor_facilities.csv``.
        engine: SQLAlchemy engine. Created automatically if not provided.

    Returns:
        The resolved output path on success.

    Raises:
        RuntimeError: If the table is empty or the query fails.
    """
    if engine is None:
        engine = get_engine()

    print(f"🔌 Connecting to database…")

    # Build a SELECT that only requests columns we know exist in the model.
    # Using explicit column list guards against schema drift.
    col_list = ", ".join(f'"{c}"' for c in EXPORT_COLUMNS)
    query = text(f'SELECT {col_list} FROM "{TABLE_NAME}" ORDER BY processing_facility_id')

    with engine.connect() as conn:
        print(f"📊 Querying {TABLE_NAME}…")
        result = conn.execute(query)
        rows = result.fetchall()
        columns = list(result.keys())

    if not rows:
        raise RuntimeError(
            f"❌ Table '{TABLE_NAME}' is empty — run the ETL first, then export."
        )

    df = pd.DataFrame(rows, columns=columns)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df.to_csv(output_path, index=False)

    print(f"✅ Exported {len(df):,} rows → {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow an optional positional argument to override the output path.
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT_PATH

    print(f"📁 Output path : {out}")
    print(f"🕐 Started at  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        result_path = export_food_processing_facilities(output_path=out)
        print()
        print(f"🎉 Done! Seed file written to:")
        print(f"   {result_path}")
    except Exception as exc:
        print(f"\n❌ Export failed: {exc}", file=sys.stderr)
        sys.exit(1)
