# audit/targets/views/icp.py
#
# Granular audit target for ICP (Inductively Coupled Plasma) analysis records only.
#
# Filter parity with mv_biomass_composition / ANALYSIS_DATA_VIEW:
#   - qc_pass != 'fail'
#   - unit must be 'ppm' (get_icp_filter: only ppm units pass)
#   - max ICP ppm per experiment <= 500,000 (outlier experiment exclusion)
#   - resource exclusions: sargassum, #n/a, lab media, alfalfa,
#     almond hulls and shells mix, almond shells and hulls mix, almond woodchips
#
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="icp",
    source_type="view",
    description=(
        "ICP (Inductively Coupled Plasma) analysis records: elemental concentrations "
        "in ppm (e.g. Ca, K, Mg, Na, P, S, Fe, Mn, Zn, Cu, B, Al, Si). "
        "Filtered to qc_pass != 'fail', unit = 'ppm', and max experiment value <= 500,000 ppm. "
        "Excludes problematic resources."
    ),

    # Layer 1: population-level stats per resource / parameter / unit
    population_sql="""
        WITH qc_max AS (
            SELECT
                ir.resource_id,
                ir.experiment_id,
                MAX(CASE WHEN LOWER(u.name) = 'ppm' THEN o.value ELSE 0 END) AS max_icp_ppm
            FROM public.icp_record ir
            JOIN public.observation o
                ON LOWER(o.record_id) = LOWER(ir.record_id)
                AND o.record_type IN (
                    'icp analysis', 'icp_analysis', 'icp-oes', 'icp-ms'
                )
            LEFT JOIN public.unit u ON o.unit_id = u.id
            WHERE ir.qc_pass != 'fail'
            GROUP BY ir.resource_id, ir.experiment_id
        )
        SELECT
            r.name                  AS resource_name,
            LOWER(p.name)           AS parameter_name,
            LOWER(u.name)           AS unit,
            AVG(o.value)            AS avg_value,
            STDDEV(o.value)         AS std_dev,
            MIN(o.value)            AS min_value,
            MAX(o.value)            AS max_value,
            COUNT(o.value)          AS observation_count
        FROM public.icp_record ir
        JOIN public.resource r ON ir.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(ir.record_id)
            AND o.record_type IN (
                'icp analysis', 'icp_analysis', 'icp-oes', 'icp-ms'
            )
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        JOIN qc_max qm
            ON qm.resource_id = ir.resource_id
            AND COALESCE(qm.experiment_id, -1) = COALESCE(ir.experiment_id, -1)
        WHERE
            ir.qc_pass != 'fail'
            AND LOWER(u.name) = 'ppm'
            AND (qm.max_icp_ppm IS NULL OR qm.max_icp_ppm <= 500000)
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
        WITH qc_max AS (
            SELECT
                ir.resource_id,
                ir.experiment_id,
                MAX(CASE WHEN LOWER(u.name) = 'ppm' THEN o.value ELSE 0 END) AS max_icp_ppm
            FROM public.icp_record ir
            JOIN public.observation o
                ON LOWER(o.record_id) = LOWER(ir.record_id)
                AND o.record_type IN (
                    'icp analysis', 'icp_analysis', 'icp-oes', 'icp-ms'
                )
            LEFT JOIN public.unit u ON o.unit_id = u.id
            WHERE ir.qc_pass != 'fail'
            GROUP BY ir.resource_id, ir.experiment_id
        )
        SELECT
            r.name          AS resource_name,
            LOWER(p.name)   AS parameter_name,
            LOWER(u.name)   AS unit,
            o.value         AS observed_value,
            ir.record_id,
            ir.qc_pass,
            ir.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            ir.created_at,
            prov.codename    AS provider_codename,
            ir.created_at    AS sample_date  -- fallback: no dedicated sample_date column on this record type
        FROM public.icp_record ir
        JOIN public.resource r ON ir.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(ir.record_id)
            AND o.record_type IN (
                'icp analysis', 'icp_analysis', 'icp-oes', 'icp-ms'
            )
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON ir.analyst_id = c.id
        LEFT JOIN public.prepared_sample ps ON ir.prepared_sample_id = ps.id
        LEFT JOIN public.field_sample fs    ON ps.field_sample_id = fs.id
        LEFT JOIN public.provider prov      ON fs.provider_id = prov.id
        JOIN qc_max qm
            ON qm.resource_id = ir.resource_id
            AND COALESCE(qm.experiment_id, -1) = COALESCE(ir.experiment_id, -1)
        WHERE
            ir.qc_pass != 'fail'
            AND LOWER(u.name) = 'ppm'
            AND (qm.max_icp_ppm IS NULL OR qm.max_icp_ppm <= 500000)
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
    gx_suite_path="audit/expectations/icp.json",
    use_isolation_forest=False,
))
