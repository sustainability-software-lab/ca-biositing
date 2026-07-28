# audit/skills/investigator/query_helpers.py
"""
Helper functions for the audit-investigator skill.
Provides local DuckDB queries over flagged_*.csv files
without hitting the main database.
"""
import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional
from audit.config import settings

def get_latest_run_dir() -> Path:
    """Returns the most recent audit output directory."""
    output_root = Path(settings.OUTPUT_ROOT)
    if not output_root.exists():
        return output_root
    runs = sorted([d for d in output_root.iterdir() if d.is_dir()], reverse=True)
    return runs[0] if runs else output_root

def query_flagged(
    target_name: str,
    run_dir: Optional[Path] = None,
    sql: str = "SELECT * FROM flagged LIMIT 100",
) -> pd.DataFrame:
    """
    Query a flagged_*.csv file using DuckDB SQL.
    The table is aliased as 'flagged'.
    """
    if run_dir is None:
        run_dir = get_latest_run_dir()
    csv_path = run_dir / f"flagged_{target_name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No flagged CSV for {target_name} in {run_dir}")
    conn = duckdb.connect()
    conn.execute(f"CREATE VIEW flagged AS SELECT * FROM read_csv_auto('{csv_path}')")
    return conn.execute(sql).df()

def get_provider_history(
    provider_codename: str,
    target_name: str = "mv_biomass_composition_extended",
    run_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Returns all flagged observations for a specific provider."""
    sql = f"SELECT * FROM flagged WHERE provider_codename = '{provider_codename}'"
    return query_flagged(target_name, run_dir, sql)

def get_parameter_summary(
    parameter_name: str,
    target_name: str = "mv_biomass_composition",
    run_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Returns summary stats for a specific parameter's flagged observations."""
    sql = f"""
        SELECT resource_name, COUNT(*) as count,
               AVG(z_score) as avg_z, MAX(z_score) as max_z,
               AVG(observed_value) as avg_val
        FROM flagged
        WHERE parameter_name = '{parameter_name}'
        GROUP BY resource_name ORDER BY count DESC
    """
    return query_flagged(target_name, run_dir, sql)
