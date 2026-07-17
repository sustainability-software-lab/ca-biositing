# audit/targets/views/ultimate.py
#
# Granular audit target for ultimate analysis records only.
#
# Filter parity with mv_biomass_composition / ANALYSIS_DATA_VIEW:
#   - qc_pass != 'fail'
#   - parameter must be in whitelist: carbon, nitrogen, oxygen, sulfur, hydrogen
#   - value <= 100 (each elemental percentage cannot exceed 100%)
#   - resource exclusions: sargassum, #n/a, lab media, alfalfa,
#     almond hulls and shells mix, almond shells and hulls mix, almond woodchips
#
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="ultimate",
    source_type="view",
    description=(
        "Ultimate (elemental) analysis records: carbon, nitrogen, oxygen, sulfur, hydrogen. "
        "Filtered to qc_pass != 'fail', parameter in whitelist "
        "(carbon, nitrogen, oxygen, sulfur, hydrogen), and value <= 100. "
        "Excludes problematic resources."
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
        FROM public.ultimate_record ur
        JOIN public.resource r ON ur.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(ur.record_id)
            AND o.record_type IN ('ultimate analysis', 'ultimate_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        WHERE
            ur.qc_pass != 'fail'
            AND LOWER(p.name) IN ('carbon', 'nitrogen', 'oxygen', 'sulfur', 'hydrogen')
            AND o.value <= 100
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
            ur.record_id,
            ur.qc_pass,
            ur.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            ur.created_at,
            prov.codename    AS provider_codename,
            ur.created_at    AS sample_date  -- fallback: no dedicated sample_date column on this record type
        FROM public.ultimate_record ur
        JOIN public.resource r ON ur.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(ur.record_id)
            AND o.record_type IN ('ultimate analysis', 'ultimate_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON ur.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON ur.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        WHERE
            ur.qc_pass != 'fail'
            AND LOWER(p.name) IN ('carbon', 'nitrogen', 'oxygen', 'sulfur', 'hydrogen')
            AND o.value <= 100
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
    gx_suite_path="audit/expectations/ultimate.json",
    use_isolation_forest=False,
))
