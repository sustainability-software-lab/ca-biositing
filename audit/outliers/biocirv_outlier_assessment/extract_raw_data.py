"""
extract_raw_data.py — RAW, UNFILTERED extraction for the BioCirV
replicate-precision / outlier-assessment pipeline.

This script pulls observation-level rows for the seven characterization
analysis record tables (compositional, proximate, ultimate, xrf, icp, xrd,
calorimetry) directly from the staging Postgres database using ONLY the
structural JOINs needed to attach metadata (parameter, unit, resource,
prepared_sample, field_sample, provider, contact/analyst, method,
experiment).

IMPORTANT — this is intentionally NOT the same as the audit-target views in
`audit/targets/views/*.py` (e.g. compositional.py, proximate.py,
mv_biomass_composition.py). Those views apply business-rule filtering
BEFORE the data reaches any downstream consumer:
    - `qc_pass != 'fail'` row drops
    - `compositional_sum` / `proximate_sum` range filters
    - ICP max-ppm filter
    - hard-coded resource exclusion lists

The outlier-assessment pipeline needs to see the raw population (including
rows that would be dropped by those filters) so replicate precision and
candidate outlier flags can be honestly characterized. This script must
NOT be used as a replacement for the filtered `audit/targets/views/*.py`
audit targets used elsewhere in the auditor platform — it exists solely to
feed the BioCirV outlier-assessment pipeline under `audit/outliers/`.

No rows are filtered out here beyond the necessary INNER JOINs to
`observation` and `parameter` (a record with no observations or no
resolvable parameter is not usable data in either pipeline). All other
joins (prepared_sample, field_sample, provider, contact, method,
experiment) are LEFT JOINs because their foreign keys are Optional on
`Aim1RecordBase`.

Run with:
    pixi run -e auditor python audit/outliers/biocirv_outlier_assessment/extract_raw_data.py
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

# Add project root to path so `ca_biositing` and `audit` are importable when
# this script is run directly (mirrors audit/scripts/freeze_reference.py).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from ca_biositing.datamodels.database import get_engine  # noqa: E402

try:
    from audit.config import settings
except Exception:
    settings = None


OUTPUT_DIR = Path(__file__).resolve().parent / "data"

# Final long-form column schema shared across all 7 analysis types.
COLUMNS = [
    "record_id",
    "resource_id",
    "resource_name",
    "prepared_sample_id",
    "experiment_id",
    "analysis_type",
    "parameter_name",
    "observed_value",
    "unit_name",
    "technical_replicate_no",
    "technical_replicate_total",
    "method_id",
    "method_name",
    "analyst_id",
    "analyst_name",
    "analyst_email",
    "provider_codename",
    "qc_pass",
    "note",
    "created_at",
    "exper_start_date",
]


def build_query(table: str, alias: str, analysis_type: str, record_type_list: str) -> str:
    """
    Build a raw, unfiltered SQL query for one Aim1 record table.

    Only structural joins are applied:
      - INNER JOIN observation / parameter (a record with no observations or
        no resolvable parameter is not usable data)
      - LEFT JOIN everything else, since prepared_sample_id, method_id,
        analyst_id, experiment_id, etc. are all Optional FKs on
        Aim1RecordBase and its record-table subclasses.

    No WHERE clause filtering on qc_pass, no sum-range CTEs, no resource
    name exclusion list — deliberately, per the outlier-assessment handoff.

    `exper_start_date` (from public.experiment) is carried as the closest
    available stand-in for "protocol_version" / date context described in
    the handoff's canonical schema — there is no dedicated protocol_version
    column anywhere in this schema.
    """
    return f"""
        SELECT
            {alias}.record_id                      AS record_id,
            {alias}.resource_id                     AS resource_id,
            r.name                                  AS resource_name,
            {alias}.prepared_sample_id              AS prepared_sample_id,
            {alias}.experiment_id                   AS experiment_id,
            '{analysis_type}'                       AS analysis_type,
            p.name                                  AS parameter_name,
            o.value                                 AS observed_value,
            u.name                                  AS unit_name,
            {alias}.technical_replicate_no          AS technical_replicate_no,
            {alias}.technical_replicate_total       AS technical_replicate_total,
            {alias}.method_id                       AS method_id,
            m.name                                  AS method_name,
            {alias}.analyst_id                      AS analyst_id,
            c.name                                  AS analyst_name,
            c.email                                 AS analyst_email,
            prov.codename                           AS provider_codename,
            {alias}.qc_pass                         AS qc_pass,
            {alias}.note                            AS note,
            {alias}.created_at                      AS created_at,
            e.exper_start_date                      AS exper_start_date
        FROM public.{table} {alias}
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER({alias}.record_id)
            AND o.record_type IN ({record_type_list})
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.resource r ON {alias}.resource_id = r.id
        LEFT JOIN public.prepared_sample ps ON {alias}.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov ON fs.provider_id = prov.id
        LEFT JOIN public.contact c ON {alias}.analyst_id = c.id
        LEFT JOIN public.method m ON {alias}.method_id = m.id
        LEFT JOIN public.experiment e ON {alias}.experiment_id = e.id
    """


# record_type IN-lists copied verbatim from the corresponding verified
# audit/targets/views/*.py files (join/record_type logic only — no
# WHERE-clause filtering, sum CTEs, or resource exclusions are carried over).
ANALYSIS_TABLES = [
    ("compositional_record", "cr", "compositional", "'compositional analysis', 'compositional_analysis'"),
    ("proximate_record", "pr", "proximate", "'proximate analysis', 'proximate_analysis'"),
    ("ultimate_record", "ur", "ultimate", "'ultimate analysis', 'ultimate_analysis'"),
    ("xrf_record", "xr", "xrf", "'xrf analysis', 'xrf_analysis'"),
    ("icp_record", "ir", "icp", "'icp analysis', 'icp_analysis', 'icp-oes', 'icp-ms'"),
    ("xrd_record", "xd", "xrd", "'xrd analysis', 'xrd_analysis'"),
    ("calorimetry_record", "cal", "calorimetry", "'calorimetry analysis', 'calorimetry_analysis'"),
]


def get_db_engine():
    """
    Mirrors the fallback logic in audit/agent.py (~lines 41-44):
    use settings.STAGING_DATABASE_URL if configured, else fall back to
    ca_biositing.datamodels.database.get_engine().
    """
    if settings is not None and getattr(settings, "STAGING_DATABASE_URL", None):
        return create_engine(settings.STAGING_DATABASE_URL, echo=False)
    return get_engine()


def extract_all(engine) -> pd.DataFrame:
    frames = []
    for table, alias, analysis_type, record_type_list in ANALYSIS_TABLES:
        sql = build_query(table, alias, analysis_type, record_type_list)
        print(f"Extracting raw data for analysis_type='{analysis_type}' from public.{table} ...")
        df = pd.read_sql(sql, engine)
        print(f"  -> {len(df)} rows")
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True, sort=False)

    # Ensure consistent column schema across all 7 analysis types; any
    # column not applicable/returned for a given analysis type is NaN-filled
    # rather than dropped.
    for col in COLUMNS:
        if col not in combined.columns:
            combined[col] = pd.NA
    combined = combined[COLUMNS]

    return combined


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    engine = get_db_engine()

    combined = extract_all(engine)

    print("\nRaw extraction row counts by analysis_type:")
    print(combined.groupby("analysis_type").size())

    datestr = datetime.now().strftime("%Y%m%d")
    output_path = OUTPUT_DIR / f"raw_extract_{datestr}.csv"
    combined.to_csv(output_path, index=False)
    print(f"\nSaved combined raw extract ({len(combined)} rows) to {output_path}")


if __name__ == "__main__":
    main()
