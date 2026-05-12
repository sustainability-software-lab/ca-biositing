#!/usr/bin/env python3
"""
Compile materialized view definitions to raw SQL for migration 0100_mv_view_fixes.

This script compiles the 9 SQLAlchemy view definitions to PostgreSQL SQL
and embeds them in the Alembic migration file.

Usage:
    pixi run python scripts/compile_mv_fixes.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.dialects import postgresql

# Import all views
from ca_biositing.datamodels.data_portal_views import (
    mv_biomass_search,
    mv_biomass_pricing,
    mv_biomass_end_uses,
    mv_biomass_availability,
    mv_biomass_composition,
    mv_biomass_volume_estimate,
    mv_biomass_sample_stats,
    mv_biomass_fermentation,
    mv_biomass_gasification,
)

# Define the 9 views with their metadata and index requirements
VIEWS = [
    {
        "name": "mv_biomass_search",
        "expr": mv_biomass_search,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_search_id ON data_portal.mv_biomass_search (id)",
            "CREATE INDEX idx_mv_biomass_search_search_vector ON data_portal.mv_biomass_search USING GIN (search_vector)",
            "CREATE INDEX idx_mv_biomass_search_resource_class ON data_portal.mv_biomass_search (resource_class)",
            "CREATE INDEX idx_mv_biomass_search_resource_subclass ON data_portal.mv_biomass_search (resource_subclass)",
            "CREATE INDEX idx_mv_biomass_search_primary_product ON data_portal.mv_biomass_search (primary_product)",
        ],
    },
    {
        "name": "mv_biomass_composition",
        "expr": mv_biomass_composition,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_composition_id ON data_portal.mv_biomass_composition (id)",
            "CREATE INDEX idx_mv_biomass_composition_resource_id ON data_portal.mv_biomass_composition (resource_id)",
            "CREATE INDEX idx_mv_biomass_composition_geoid_county ON data_portal.mv_biomass_composition (geoid, county)",
            "CREATE INDEX idx_mv_biomass_composition_analysis_type ON data_portal.mv_biomass_composition (analysis_type)",
            "CREATE INDEX idx_mv_biomass_composition_parameter_name ON data_portal.mv_biomass_composition (parameter_name)",
            "CREATE INDEX idx_mv_biomass_composition_resource_analysis ON data_portal.mv_biomass_composition (resource_id, analysis_type)",
            "CREATE INDEX idx_mv_biomass_composition_resource_geoid_analysis ON data_portal.mv_biomass_composition (resource_id, geoid, analysis_type)",
            "CREATE INDEX idx_mv_biomass_composition_resource_parameter ON data_portal.mv_biomass_composition (resource_id, parameter_name)",
        ],
    },
    {
        "name": "mv_biomass_volume_estimate",
        "expr": mv_biomass_volume_estimate,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_volume_estimate_id ON data_portal.mv_biomass_volume_estimate (id)",
            "CREATE INDEX idx_mv_biomass_volume_estimate_resource_id ON data_portal.mv_biomass_volume_estimate (resource_id)",
            "CREATE INDEX idx_mv_biomass_volume_estimate_geoid ON data_portal.mv_biomass_volume_estimate (geoid)",
            "CREATE INDEX idx_mv_biomass_volume_estimate_resource_year ON data_portal.mv_biomass_volume_estimate (resource_id, dataset_year)",
        ],
    },
    {
        "name": "mv_biomass_availability",
        "expr": mv_biomass_availability,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_availability_resource_id ON data_portal.mv_biomass_availability (resource_id)",
        ],
    },
    {
        "name": "mv_biomass_sample_stats",
        "expr": mv_biomass_sample_stats,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_sample_stats_resource_id ON data_portal.mv_biomass_sample_stats (resource_id)",
        ],
    },
    {
        "name": "mv_biomass_fermentation",
        "expr": mv_biomass_fermentation,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation (id)",
            "CREATE INDEX idx_mv_biomass_fermentation_resource_id ON data_portal.mv_biomass_fermentation (resource_id)",
            "CREATE INDEX idx_mv_biomass_fermentation_geoid ON data_portal.mv_biomass_fermentation (geoid)",
            "CREATE INDEX idx_mv_biomass_fermentation_county ON data_portal.mv_biomass_fermentation (county)",
            "CREATE INDEX idx_mv_biomass_fermentation_strain_name ON data_portal.mv_biomass_fermentation (strain_name)",
            "CREATE INDEX idx_mv_biomass_fermentation_product_name ON data_portal.mv_biomass_fermentation (product_name)",
        ],
    },
    {
        "name": "mv_biomass_gasification",
        "expr": mv_biomass_gasification,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_gasification_id ON data_portal.mv_biomass_gasification (id)",
            "CREATE INDEX idx_mv_biomass_gasification_resource_id ON data_portal.mv_biomass_gasification (resource_id)",
            "CREATE INDEX idx_mv_biomass_gasification_reactor_type ON data_portal.mv_biomass_gasification (reactor_type)",
            "CREATE INDEX idx_mv_biomass_gasification_parameter_name ON data_portal.mv_biomass_gasification (parameter_name)",
            "CREATE INDEX idx_mv_biomass_gasification_resource_reactor_param ON data_portal.mv_biomass_gasification (resource_id, reactor_type, parameter_name)",
        ],
    },
    {
        "name": "mv_biomass_pricing",
        "expr": mv_biomass_pricing,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing (id)",
            "CREATE INDEX idx_mv_biomass_pricing_resource_id ON data_portal.mv_biomass_pricing (resource_id)",
            "CREATE INDEX idx_mv_biomass_pricing_geoid_county ON data_portal.mv_biomass_pricing (geoid, county)",
            "CREATE INDEX idx_mv_biomass_pricing_report_source_date ON data_portal.mv_biomass_pricing (report_source, report_date)",
            "CREATE INDEX idx_mv_biomass_pricing_resource_date ON data_portal.mv_biomass_pricing (resource_id, report_date)",
        ],
    },
    {
        "name": "mv_biomass_end_uses",
        "expr": mv_biomass_end_uses,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_end_uses_resource_use_case ON data_portal.mv_biomass_end_uses (resource_id, use_case)",
            "CREATE INDEX idx_mv_biomass_end_uses_resource_id ON data_portal.mv_biomass_end_uses (resource_id)",
        ],
    },
]


def compile_view(select_expr):
    """Compile SQLAlchemy select() to PostgreSQL SQL."""
    compiled = select_expr.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True}
    )
    return str(compiled)


def generate_migration_file():
    """Generate the complete migration file."""

    # Compile all view SQL
    view_sqls = {}
    print("Compiling views...")
    for view_config in VIEWS:
        view_name = view_config["name"]
        try:
            sql = compile_view(view_config["expr"])
            view_sqls[view_name] = sql
            print(f"  ✓ {view_name}")
        except Exception as e:
            print(f"  ✗ {view_name}: {e}")
            raise

    # Build DROP_INDEX_STATEMENTS
    drop_index_statements = []
    for view_config in VIEWS:
        for index in view_config["indexes"]:
            # Extract index name from CREATE statement
            # Format: "CREATE [UNIQUE] INDEX idx_name ON schema.view_name (columns)"
            parts = index.split()
            idx_name = parts[3] if "UNIQUE" in index else parts[2]
            drop_index_statements.append(f'    "DROP INDEX IF EXISTS data_portal.{idx_name}",')

    # Build DROP_VIEW_STATEMENTS
    drop_view_statements = []
    for view_config in VIEWS:
        view_name = view_config["name"]
        drop_view_statements.append(f'    "DROP MATERIALIZED VIEW IF EXISTS data_portal.{view_name} CASCADE",')

    # Build CREATE_INDEX_STATEMENTS
    create_index_statements = []
    for view_config in VIEWS:
        for index in view_config["indexes"]:
            create_index_statements.append(f'    "{index}",')

    # Build view SQL definitions section
    view_sql_defs = []
    for view_config in VIEWS:
        view_name = view_config["name"]
        sql = view_sqls[view_name]
        view_sql_defs.append(f'''{view_name.upper()}_SQL = """
CREATE MATERIALIZED VIEW data_portal.{view_name} AS
{sql}
"""''')

    # Build the complete migration file
    migration_content = f'''"""Recreate all 9 materialized views with fixes.

Revision ID: 0100_mv_view_fixes
Revises: 55f93e3a6237
Create Date: 2026-05-05

This migration:
1. Drops all indexes on the 9 data portal materialized views
2. Drops all 9 materialized views in CASCADE mode
3. Recreates all 9 views with updated SQL (fixes for mv_biomass_search, mv_biomass_pricing, mv_biomass_end_uses)
4. Creates all required indexes for concurrent refresh and query performance
5. Grants schema access to the readonly role

Modified views:
  - mv_biomass_search: Added volume_estimate_year column, updated sugar calculation to use glucan+xylan
  - mv_biomass_pricing: Added resource_id and resource_name, replaced commodity mapping
  - mv_biomass_end_uses: Added value_multiplier_low and value_multiplier_high columns

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0100_mv_view_fixes"
down_revision: Union[str, Sequence[str], None] = "55f93e3a6237"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Drop indexes (in reverse order)
DROP_INDEX_STATEMENTS = [
{chr(10).join(drop_index_statements)}
]

# Drop views
DROP_VIEW_STATEMENTS = [
{chr(10).join(drop_view_statements)}
]

# View SQL definitions (compiled from SQLAlchemy)
{chr(10).join(view_sql_defs)}

# Create indexes
CREATE_INDEX_STATEMENTS = [
{chr(10).join(create_index_statements)}
]


def upgrade() -> None:
    """Recreate all 9 materialized views with fixes."""

    # Drop all existing indexes
    for statement in DROP_INDEX_STATEMENTS:
        op.execute(statement)

    # Drop all existing views
    for statement in DROP_VIEW_STATEMENTS:
        op.execute(statement)

    # Create all views with new SQL
    op.execute(MV_BIOMASS_SEARCH_SQL)
    # Re-verify that all views are created
    op.execute(MV_BIOMASS_COMPOSITION_SQL)
    op.execute(MV_BIOMASS_VOLUME_ESTIMATE_SQL)
    op.execute(MV_BIOMASS_AVAILABILITY_SQL)
    op.execute(MV_BIOMASS_SAMPLE_STATS_SQL)
    op.execute(MV_BIOMASS_FERMENTATION_SQL)
    op.execute(MV_BIOMASS_GASIFICATION_SQL)
    # Pricing View
    op.execute(MV_BIOMASS_PRICING_SQL)
    # End Uses View
    op.execute(MV_BIOMASS_END_USES_SQL)

    # Create all indexes
    for statement in CREATE_INDEX_STATEMENTS:
        op.execute(statement)

    # Grant permissions to readonly role
    op.execute("GRANT USAGE ON SCHEMA data_portal TO biocirv_readonly")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA data_portal TO biocirv_readonly")


def downgrade() -> None:
    """Drop all 9 materialized views and their indexes."""

    # Drop indexes
    for statement in DROP_INDEX_STATEMENTS:
        op.execute(statement)

    # Drop views
    for statement in DROP_VIEW_STATEMENTS:
        op.execute(statement)
'''

    return migration_content


def main():
    """Generate and write the migration file."""

    print("=" * 80)
    print("Generating migration 0100_mv_view_fixes.py")
    print("=" * 80)
    print()

    # Generate migration content
    migration_content = generate_migration_file()

    # Write migration file
    alembic_versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migration_path = alembic_versions_dir / "0100_mv_view_fixes.py"

    with open(migration_path, "w") as f:
        f.write(migration_content)

    print()
    print("=" * 80)
    print(f"✓ Migration file created: {migration_path.relative_to(Path.cwd())}")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review the migration file for correctness")
    print("2. Run: pixi run migrate")
    print("3. Verify views: pixi run access-db -c 'SELECT COUNT(*) FROM data_portal.mv_biomass_search;'")
    print("4. Run audit: pixi run audit")


if __name__ == "__main__":
    main()
