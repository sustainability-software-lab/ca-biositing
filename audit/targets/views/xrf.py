# audit/targets/views/xrf.py
#
# Granular audit target for XRF (X-Ray Fluorescence) analysis records only.
#
# Filter parity with mv_biomass_composition / ANALYSIS_DATA_VIEW:
#   - qc_pass != 'fail'
#   - no additional unit or sum constraints (xrf is in the "all other types" branch)
#   - resource exclusions: sargassum, #n/a, lab media, alfalfa,
#     almond hulls and shells mix, almond shells and hulls mix, almond woodchips
#
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="xrf",
    source_type="view",
    description=(
        "XRF (X-Ray Fluorescence) analysis records: elemental oxide and elemental "
        "weight-percent measurements (e.g. SiO2, Al2O3, Fe2O3, CaO, K2O, Na2O, MgO, P2O5). "
        "Filtered to qc_pass != 'fail'. Excludes problematic resources."
    ),

    # Layer 1: population-level stats per resource / parameter / unit
    population_sql="""
        SELECT
            r.name                  AS resource_name,
            LOWER(p.name)           AS parameter_name,
            LOWER(u.name)           AS unit,
            AVG(o.value)            AS avg_value,
            STDDEV(o.value)         AS std_dev,
            MIN(o.value)            AS min_value,
            MAX(o.value)            AS max_value,
            COUNT(o.value)          AS observation_count
        FROM public.xrf_record xr
        JOIN public.resource r ON xr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(xr.record_id)
            AND o.record_type IN ('xrf analysis', 'xrf_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        WHERE
            xr.qc_pass != 'fail'
            AND LOWER(r.name) NOT IN (
                'sargassum', '#n/a', 'lab media', 'alfalfa',
                'almond hulls and shells mix',
                'almond shells and hulls mix',
                'almond woodchips'
            )
        GROUP BY r.name, p.name, u.name
        HAVING COUNT(o.value) >= 3
    """,

    # Layer 2: individual observations with analyst attribution and QC context
    observation_sql="""
        SELECT
            r.name          AS resource_name,
            LOWER(p.name)   AS parameter_name,
            LOWER(u.name)   AS unit,
            o.value         AS observed_value,
            xr.record_id,
            xr.qc_pass,
            xr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            xr.created_at,
            prov.codename    AS provider_codename,
            xr.created_at    AS sample_date  -- fallback: no dedicated sample_date column on this record type
        FROM public.xrf_record xr
        JOIN public.resource r ON xr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(xr.record_id)
            AND o.record_type IN ('xrf analysis', 'xrf_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON xr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON xr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        WHERE
            xr.qc_pass != 'fail'
            AND LOWER(r.name) NOT IN (
                'sargassum', '#n/a', 'lab media', 'alfalfa',
                'almond hulls and shells mix',
                'almond shells and hulls mix',
                'almond woodchips'
            )
    """,

    group_by_cols=["resource_name", "parameter_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id", "resource_name", "parameter_name"],
    analyst_col="analyst_email",
    gx_suite_path="audit/expectations/xrf.json",
    use_isolation_forest=False,
))
