"""
USDA Commodity Mapping Seeder
---
This module seeds the usda_commodity and resource_usda_commodity_map tables
using the CSV mapping file. It assumes that the primary_ag_product and resource
tables are already populated by previous flows.

api_name values come from reviewed_api_mappings.py (OFFICIAL_API_MAPPINGS),
which covers all ~400 NASS commodity codes. Run --apply-api-names after seeding
to backfill any rows that were inserted before the mapping dict was complete.
"""

import os
import pandas as pd
from sqlalchemy import text
from ca_biositing.pipeline.utils.engine import get_engine

# reviewed_api_mappings.py lives in the same utils directory.
# Use a relative import when loaded as part of the package (normal pipeline
# operation) and fall back to a direct import when the module is run as a
# standalone script (e.g. python seed_commodity_mappings.py).
try:
    from .reviewed_api_mappings import get_api_name as _get_api_name
except ImportError:
    try:
        from reviewed_api_mappings import get_api_name as _get_api_name  # type: ignore[import]
    except ImportError as e:
        raise ImportError(
            "Unable to import 'get_api_name' from 'reviewed_api_mappings'. "
            "This module is required as the source of truth for api_name values."
        ) from e


def seed_commodity_mappings_from_csv(csv_path: str = None, engine=None) -> bool:
    """
    Seed usda_commodity and resource_usda_commodity_map tables from CSV mapping file.

    Args:
        csv_path: Path to CSV mapping file (defaults to pipeline utils directory)
        engine: SQLAlchemy engine (optional, will create if None)

    Returns:
        bool: True if seeding succeeded, False otherwise
    """

    try:
        if engine is None:
            engine = get_engine()

        # Default CSV path (name-based format)
        if csv_path is None:
            current_dir = os.path.dirname(__file__)
            csv_path = os.path.join(current_dir, "commodity_mappings.csv")

        if not os.path.exists(csv_path):
            print(f"❌ Mapping CSV file not found: {csv_path}")
            return False

        # Read CSV mapping file
        print(f"📊 Reading mapping file: {csv_path}")
        df = pd.read_csv(csv_path)

        # Normalize key mapping columns for stable joins and API-facing output
        for col in ["commodity_name", "api_name", "resource_name"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.lower()

        # astype(str) converts pd.NaN to the literal string 'nan' — restore as None
        # so we never write the string 'nan' into the database.
        for col in ["commodity_name", "api_name"]:
            if col in df.columns:
                df[col] = df[col].where(df[col] != 'nan', other=None)

        # Filter out unmapped entries
        mapped_df = df[df['match_tier'] != 'UNMAPPED'].copy()
        print(f"📊 Found {len(mapped_df)} mapped commodities (excluding {len(df) - len(mapped_df)} unmapped)")

        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                # 1. Seed usda_commodity table (unique commodities only)
                print("🌱 Seeding usda_commodity table...")
                # Exclude NO_MATCH rows whose commodity_name is None/NaN.
                # Compute api_name from reviewed_api_mappings.py — that is the
                # authoritative source; the CSV api_name column is advisory only.
                valid_df = mapped_df[mapped_df['commodity_name'].notna()]
                unique_commodities = (
                    valid_df
                    .drop_duplicates('commodity_name')[['commodity_name', 'usda_code']]
                    .copy()
                )
                # Use a list comprehension so Python None (DISABLED entries) is
                # stored as a proper None object, not NaN, for safe SQL binding.
                unique_commodities['api_name'] = [
                    _get_api_name(n)
                    for n in unique_commodities['commodity_name'].str.upper()
                ]

                # Constant metadata for all NASS-sourced commodities
                NASS_URI = (
                    "https://www.nass.usda.gov/Data_and_Statistics/"
                    "County_Data_Files/Frequently_Asked_Questions/commcodes.php"
                )
                NASS_SOURCE = "NASS_WEB"

                for _, row in unique_commodities.iterrows():
                    # First check if commodity already exists
                    existing_result = conn.execute(text(
                        "SELECT id FROM usda_commodity WHERE name = :name"
                    ), {'name': row['commodity_name']})
                    existing_row = existing_result.fetchone()

                    if existing_row:
                        # Update existing record — fill in metadata that may be NULL
                        conn.execute(text("""
                            UPDATE usda_commodity
                            SET api_name    = :api_name,
                                usda_code   = :usda_code,
                                usda_source = COALESCE(usda_source, :usda_source),
                                description = COALESCE(description, :description),
                                uri         = COALESCE(uri, :uri),
                                updated_at  = NOW()
                            WHERE name = :name
                        """), {
                            'name': row['commodity_name'],
                            'api_name': row['api_name'],
                            'usda_code': int(row['usda_code']),
                            'usda_source': NASS_SOURCE,
                            'description': row['commodity_name'],
                            'uri': NASS_URI,
                        })
                    else:
                        # Insert new record with full metadata
                        conn.execute(text("""
                            INSERT INTO usda_commodity
                                (name, api_name, usda_code, usda_source, description, uri,
                                 created_at, updated_at)
                            VALUES
                                (:name, :api_name, :usda_code, :usda_source, :description, :uri,
                                 NOW(), NOW())
                        """), {
                            'name': row['commodity_name'],
                            'api_name': row['api_name'],
                            'usda_code': int(row['usda_code']),
                            'usda_source': NASS_SOURCE,
                            'description': row['commodity_name'],
                            'uri': NASS_URI,
                        })

                print(f"✅ Seeded {len(unique_commodities)} USDA commodities")

                # 2. Seed resource_usda_commodity_map table (name-based lookups)
                print("🌱 Seeding resource_usda_commodity_map table...")

                # Clear existing mappings first
                conn.execute(text("DELETE FROM resource_usda_commodity_map"))

                for _, row in mapped_df.iterrows():
                    # Lookup resource_id by name — try resource table first,
                    # fall back to primary_ag_product. Both map to the same
                    # resource_usda_commodity_map table; the type is encoded by
                    # which FK column is non-null.
                    resource_result = conn.execute(text(
                        "SELECT id FROM resource WHERE name = :name"
                    ), {'name': row['resource_name']})
                    resource_row = resource_result.fetchone()

                    if resource_row:
                        resource_id = resource_row[0]
                        pap_id = None
                    else:
                        pap_result = conn.execute(text(
                            "SELECT id FROM primary_ag_product WHERE name = :name"
                        ), {'name': row['resource_name']})
                        pap_row = pap_result.fetchone()

                        if not pap_row:
                            print(f"⚠️  '{row['resource_name']}' not found in resource or primary_ag_product - skipping")
                            continue

                        resource_id = None
                        pap_id = pap_row[0]

                    # Lookup commodity_id by name
                    commodity_result = conn.execute(text(
                        "SELECT id FROM usda_commodity WHERE name = :commodity_name"
                    ), {'commodity_name': row['commodity_name']})
                    commodity_row = commodity_result.fetchone()

                    if not commodity_row:
                        print(f"⚠️  Commodity '{row['commodity_name']}' not found - skipping")
                        continue

                    commodity_id = commodity_row[0]

                    # Insert mapping with runtime-resolved IDs
                    conn.execute(text("""
                        INSERT INTO resource_usda_commodity_map (
                            resource_id, primary_ag_product_id, usda_commodity_id,
                            match_tier, note, created_at, updated_at
                        )
                        VALUES (
                            :resource_id, :pap_id, :usda_commodity_id,
                            :match_tier, :note, NOW(), NOW()
                        )
                    """), {
                        'resource_id': resource_id,
                        'pap_id': pap_id,
                        'usda_commodity_id': commodity_id,
                        'match_tier': row['match_tier'],
                        'note': row['note']
                    })

                print(f"✅ Seeded {len(mapped_df)} resource-commodity mappings")

                # Commit transaction
                trans.commit()
                print("🎉 Successfully seeded commodity mappings from CSV!")
                return True

            except Exception as e:
                trans.rollback()
                print(f"❌ Error seeding commodity mappings: {e}")
                return False

    except Exception as e:
        print(f"❌ Error in seed_commodity_mappings_from_csv: {e}")
        return False


def backfill_usda_commodity_metadata(engine=None, csv_path: str = None) -> int:
    """
    Backfill NULL or stale metadata on existing usda_commodity rows.

    Fills in NULL description, uri, usda_source, and fixes api_name values that
    are NULL, empty, or the string 'nan' (a pandas artefact from prior seeder
    runs before the NaN-handling fix was in place).

    Safe to call on every ETL run — only rows that actually need updating are
    touched (WHERE clause guards on NULL / bad-value conditions).

    Returns:
        Number of usda_commodity rows updated.
    """
    try:
        if engine is None:
            engine = get_engine()
        if csv_path is None:
            current_dir = os.path.dirname(__file__)
            csv_path = os.path.join(current_dir, "commodity_mappings.csv")
        if not os.path.exists(csv_path):
            print(f"Warning: backfill_usda_commodity_metadata: CSV not found at {csv_path}")
            return 0

        NASS_URI = (
            "https://www.nass.usda.gov/Data_and_Statistics/"
            "County_Data_Files/Frequently_Asked_Questions/commcodes.php"
        )
        NASS_SOURCE = "NASS_WEB"

        df = pd.read_csv(csv_path)
        df['commodity_name'] = df['commodity_name'].astype(str).str.strip().str.lower()
        df['commodity_name'] = df['commodity_name'].where(df['commodity_name'] != 'nan', other=None)
        unique_names = (
            df[df['commodity_name'].notna()]['commodity_name']
            .drop_duplicates()
            .tolist()
        )

        updated = 0
        with engine.connect() as conn:
            for name in unique_names:
                api_name = _get_api_name(name.upper())  # None for DISABLED entries
                result = conn.execute(text("""
                    UPDATE usda_commodity
                    SET
                        api_name    = CASE
                                          WHEN api_name IS NULL OR api_name IN ('', 'nan')
                                          THEN :api_name
                                          ELSE api_name
                                      END,
                        usda_source = COALESCE(usda_source, :usda_source),
                        description = COALESCE(description, :description),
                        uri         = COALESCE(uri, :uri),
                        created_at  = COALESCE(created_at, NOW()),
                        updated_at  = NOW()
                    WHERE LOWER(name) = :name
                      AND (api_name IS NULL OR api_name IN ('', 'nan')
                           OR usda_source IS NULL
                           OR description IS NULL
                           OR uri IS NULL
                           OR created_at IS NULL)
                """), {
                    'name': name,
                    'api_name': api_name,
                    'usda_source': NASS_SOURCE,
                    'description': name,
                    'uri': NASS_URI,
                })
                updated += result.rowcount
            conn.commit()

        if updated:
            print(f"🔧 Backfilled metadata for {updated} usda_commodity rows")
        return updated

    except Exception as e:
        print(f"⚠️  Could not backfill usda_commodity metadata: {e}")
        return 0



def ensure_commodities_exist(engine, commodity_names: list[str]) -> int:
    """
    Ensure that a list of commodity names exists in the usda_commodity table.
    This is used to dynamically add discovered top commodities so that foreign key
    constraints are satisfied during the load step.

    Args:
        engine: SQLAlchemy engine
        commodity_names: List of commodity names (api_name format)

    Returns:
        Number of new commodities inserted
    """
    if not commodity_names:
        return 0

    from sqlalchemy import text

    inserted_count = 0
    NASS_URI = (
        "https://www.nass.usda.gov/Data_and_Statistics/"
        "County_Data_Files/Frequently_Asked_Questions/commcodes.php"
    )
    NASS_SOURCE = "NASS_WEB"

    with engine.begin() as conn:
        for name in commodity_names:
            # Check if it exists (case-insensitive)
            result = conn.execute(text(
                "SELECT id FROM usda_commodity WHERE LOWER(name) = LOWER(:name) OR LOWER(api_name) = LOWER(:name)"
            ), {'name': name})

            if not result.fetchone():
                # Insert new commodity
                conn.execute(text("""
                    INSERT INTO usda_commodity
                        (name, api_name, usda_source, description, uri, created_at, updated_at)
                    VALUES
                        (:name, :api_name, :usda_source, :description, :uri, NOW(), NOW())
                """), {
                    'name': name.lower(),
                    'api_name': name.upper(),
                    'usda_source': NASS_SOURCE,
                    'description': f"Dynamically discovered top commodity: {name}",
                    'uri': NASS_URI
                })
                inserted_count += 1

    if inserted_count > 0:
        print(f"🌱 Dynamically seeded {inserted_count} new top commodities into usda_commodity table")

    return inserted_count


def check_seeding_prerequisites(engine=None) -> dict:
    """
    Check if prerequisite tables (resource, primary_ag_product) are populated.

    Returns:
        dict: Status of prerequisite tables
    """
    try:
        if engine is None:
            engine = get_engine()

        with engine.connect() as conn:
            # Check resource table
            resource_count = conn.execute(text("SELECT COUNT(*) FROM resource")).scalar()

            # Check primary_ag_product table
            primary_ag_count = conn.execute(text("SELECT COUNT(*) FROM primary_ag_product")).scalar()

            return {
                'resource_count': resource_count,
                'primary_ag_product_count': primary_ag_count,
                'prerequisites_met': resource_count > 0 and primary_ag_count > 0
            }

    except Exception as e:
        print(f"Error checking prerequisites: {e}")
        return {
            'resource_count': 0,
            'primary_ag_product_count': 0,
            'prerequisites_met': False,
            'error': str(e)
        }


if __name__ == "__main__":
    # Check prerequisites first
    status = check_seeding_prerequisites()
    print(f"Prerequisites check: {status}")

    if status['prerequisites_met']:
        success = seed_commodity_mappings_from_csv()
        print(f"Seeding result: {'✅ Success' if success else '❌ Failed'}")
    else:
        print("❌ Prerequisites not met - resource and primary_ag_product tables must be populated first")
        print("   Run the full ETL pipeline (pixi run run-etl) to populate these tables")
