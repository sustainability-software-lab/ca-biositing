#!/usr/bin/env python3
"""
Compile materialized view definitions to raw SQL for manual Alembic migrations.

This script compiles the 9 SQLAlchemy view definitions to PostgreSQL SQL
and embeds them in an Alembic migration file. It supports creating new
revisions or updating existing ones for rapid iteration.

Usage:
    # Create a new migration for view fixes
    pixi run python scripts/compile_mv_fixes.py -m "Fix view search and stats"

    # Overwrite an existing migration (useful for iterative development)
    pixi run python scripts/compile_mv_fixes.py --revision 0009 --force
"""

import argparse
import datetime
import os
import sys
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.dialects import postgresql

# Import data_portal views
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

# Import ca_biositing views
from ca_biositing.datamodels import views as ca_views

# Define views with their metadata and index requirements
# Schema and name mapping
VIEWS = [
    # data_portal schema views
    {
        "name": "mv_biomass_search",
        "schema": "data_portal",
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
        "schema": "data_portal",
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
        "schema": "data_portal",
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
        "schema": "data_portal",
        "expr": mv_biomass_availability,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_availability_resource_id ON data_portal.mv_biomass_availability (resource_id)",
        ],
    },
    {
        "name": "mv_biomass_sample_stats",
        "schema": "data_portal",
        "expr": mv_biomass_sample_stats,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_sample_stats_resource_id ON data_portal.mv_biomass_sample_stats (resource_id)",
        ],
    },
    {
        "name": "mv_biomass_fermentation",
        "schema": "data_portal",
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
        "schema": "data_portal",
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
        "schema": "data_portal",
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
        "schema": "data_portal",
        "expr": mv_biomass_end_uses,
        "indexes": [
            "CREATE UNIQUE INDEX idx_mv_biomass_end_uses_resource_use_case ON data_portal.mv_biomass_end_uses (resource_id, use_case)",
            "CREATE INDEX idx_mv_biomass_end_uses_resource_id ON data_portal.mv_biomass_end_uses (resource_id)",
        ],
    },
    # ca_biositing schema views
    {
        "name": "analysis_data_view",
        "schema": "ca_biositing",
        "expr": ca_views.ANALYSIS_DATA_VIEW,
        "indexes": [
            "CREATE UNIQUE INDEX idx_analysis_data_view_id ON ca_biositing.analysis_data_view (id)",
            "CREATE INDEX idx_analysis_data_view_resource ON ca_biositing.analysis_data_view (resource)",
            "CREATE INDEX idx_analysis_data_view_geoid ON ca_biositing.analysis_data_view (geoid)",
            "CREATE INDEX idx_analysis_data_view_parameter ON ca_biositing.analysis_data_view (parameter)",
        ],
    },
    {
        "name": "analysis_average_view",
        "schema": "ca_biositing",
        "expr": ca_views.ANALYSIS_AVERAGE_VIEW,
        "indexes": [
            "CREATE UNIQUE INDEX idx_analysis_average_view_res_geo_param ON ca_biositing.analysis_average_view (resource, geoid, parameter, unit)",
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


def get_latest_revision() -> Optional[str]:
    """Find the latest revision ID in alembic/versions/."""
    versions_dir = Path("alembic/versions")
    if not versions_dir.exists():
        return None

    revisions = []
    for f in versions_dir.glob("*.py"):
        match = re.match(r"^(\d+)_", f.name)
        if match:
            revisions.append(match.group(1))

    return sorted(revisions)[-1] if revisions else None


def generate_migration_content(revision_id: str, down_revision: str, message: str) -> str:
    """Generate the complete migration file content."""

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
        schema = view_config["schema"]
        for index in view_config["indexes"]:
            parts = index.split()
            idx_name = parts[3] if "UNIQUE" in index else parts[2]
            drop_index_statements.append(f'    "DROP INDEX IF EXISTS {schema}.{idx_name}",')

    # Build DROP_VIEW_STATEMENTS
    drop_view_statements = []
    # Drop in reverse order to handle dependencies (analysis_average depends on analysis_data)
    for view_config in reversed(VIEWS):
        view_name = view_config["name"]
        schema = view_config["schema"]
        drop_view_statements.append(f'    "DROP MATERIALIZED VIEW IF EXISTS {schema}.{view_name} CASCADE",')

    # Build view SQL definitions section
    view_sql_defs = []
    # Create in original order (respecting dependencies)
    for view_config in VIEWS:
        view_name = view_config["name"]
        schema = view_config["schema"]
        sql = view_sqls[view_name]
        view_sql_defs.append(f'''{view_name.upper()}_SQL = """
CREATE MATERIALIZED VIEW {schema}.{view_name} AS
{sql}
"""''')

    # Build CREATE_INDEX_STATEMENTS
    create_index_statements = []
    for view_config in VIEWS:
        for index in view_config["indexes"]:
            create_index_statements.append(f'    "{index}",')

    date_str = datetime.date.today().isoformat()

    content = f'''"""{message}

Revision ID: {revision_id}
Revises: {down_revision}
Create Date: {date_str}

This migration (auto-generated by compile_mv_fixes.py):
1. Drops existing indexes on the materialized views
2. Drops materialized views in CASCADE mode
3. Recreates views with updated SQL compiled from SQLAlchemy expressions
4. Creates required indexes for concurrent refresh and query performance
5. Grants schema access to the readonly role

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "{revision_id}"
down_revision: Union[str, Sequence[str], None] = "{down_revision}"
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
    """Recreate materialized views."""

    # Drop all existing indexes
    for statement in DROP_INDEX_STATEMENTS:
        op.execute(statement)

    # Drop all existing views
    for statement in DROP_VIEW_STATEMENTS:
        op.execute(statement)

    # Create all views with new SQL (in order of definition)
{chr(10).join([f'    op.execute({v["name"].upper()}_SQL)' for v in VIEWS])}

    # Create all indexes
    for statement in CREATE_INDEX_STATEMENTS:
        op.execute(statement)

    # Grant permissions to readonly role
    op.execute("GRANT USAGE ON SCHEMA data_portal TO biocirv_readonly")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA data_portal TO biocirv_readonly")
    op.execute("GRANT USAGE ON SCHEMA ca_biositing TO biocirv_readonly")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA ca_biositing TO biocirv_readonly")


def downgrade() -> None:
    """Drop materialized views and their indexes."""

    # Drop indexes
    for statement in DROP_INDEX_STATEMENTS:
        op.execute(statement)

    # Drop views
    for statement in DROP_VIEW_STATEMENTS:
        op.execute(statement)
'''
    return content


def main():
    parser = argparse.ArgumentParser(description="Compile SQLAlchemy views to Alembic migration.")
    parser.add_argument("-m", "--message", help="Migration message (required if creating new revision)")
    parser.add_argument("--revision", help="Specific revision ID to overwrite (e.g. 0009)")
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing revision file")

    args = parser.parse_args()

    versions_dir = Path("alembic/versions")

    if args.revision:
        # Overwrite existing revision
        revision_id = args.revision
        existing_files = list(versions_dir.glob(f"{revision_id}_*.py"))

        if not existing_files:
            print(f"Error: No migration found for revision {revision_id}")
            sys.exit(1)

        migration_path = existing_files[0]

        if not args.force:
            print(f"Error: Migration file {migration_path} already exists. Use --force to overwrite.")
            sys.exit(1)

        # Parse existing down_revision and message from file if possible
        with open(migration_path, "r") as f:
            old_content = f.read()
            dr_match = re.search(r'down_revision: Union\[str, Sequence\[str\], None\] = "([^"]+)"', old_content)
            down_revision = dr_match.group(1) if dr_match else "None"
            msg_match = re.search(r'"""(.*)', old_content)
            message = msg_match.group(1).strip() if msg_match else "Update materialized views"

        print(f"Overwriting revision {revision_id} ({migration_path.name})...")
    else:
        # Create new revision
        if not args.message:
            print("Error: -m/--message is required when creating a new revision.")
            sys.exit(1)

        down_revision = get_latest_revision() or "None"
        try:
            next_rev_int = int(down_revision) + 1
            revision_id = f"{next_rev_int:04d}"
        except ValueError:
            print(f"Error: Could not determine next revision number from latest: {down_revision}")
            sys.exit(1)

        safe_message = re.sub(r'[^a-z0-9]+', '_', args.message.lower()).strip('_')
        migration_path = versions_dir / f"{revision_id}_{safe_message}.py"
        message = args.message

        print(f"Creating new revision {revision_id} -> {migration_path.name}...")

    # Generate content
    content = generate_migration_content(revision_id, down_revision, message)

    # Write file
    with open(migration_path, "w") as f:
        f.write(content)

    print(f"\n✓ Migration file updated: {migration_path}")
    print("\nNext steps:")
    print(f"1. Run: POSTGRES_HOST=localhost pixi run alembic downgrade -1")
    print(f"2. Run: POSTGRES_HOST=localhost pixi run migrate")


if __name__ == "__main__":
    main()
