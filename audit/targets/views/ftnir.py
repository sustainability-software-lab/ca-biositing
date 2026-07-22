# audit/targets/views/ftnir.py
#
# Granular audit target for FTNIR (Fourier Transform Near-Infrared) analysis records only.
#
# Filter parity with mv_biomass_composition / ANALYSIS_DATA_VIEW:
#   - qc_pass != 'fail'
#   - no additional sum or unit constraints (ftnir is in the "all other types" branch)
#   - resource exclusions: sargassum, #n/a, lab media, alfalfa,
#     almond hulls and shells mix, almond shells and hulls mix, almond woodchips
#
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="ftnir",
    source_type="view",
    description=(
        "FTNIR (Fourier Transform Near-Infrared) analysis records: rapid spectroscopic "
        "predictions of compositional parameters (e.g. moisture, protein, fiber, starch). "
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
        FROM public.ftnir_record fr
        JOIN public.resource r ON fr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(fr.record_id)
            AND o.record_type IN ('ftnir analysis', 'ftnir_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        WHERE
            fr.qc_pass != 'fail'
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
            fr.record_id,
            fr.qc_pass,
            fr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            fr.created_at,
            prov.codename    AS provider_codename,
            fr.created_at    AS sample_date  -- fallback: no dedicated sample_date column on this record type
        FROM public.ftnir_record fr
        JOIN public.resource r ON fr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(fr.record_id)
            AND o.record_type IN ('ftnir analysis', 'ftnir_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON fr.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON fr.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        WHERE
            fr.qc_pass != 'fail'
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
    gx_suite_path="audit/expectations/ftnir.json",
    use_isolation_forest=False,
))
