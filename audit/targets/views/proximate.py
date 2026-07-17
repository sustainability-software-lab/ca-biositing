# audit/targets/views/proximate.py
#
# Granular audit target for proximate analysis records only.
#
# Filter parity with mv_biomass_composition / ANALYSIS_DATA_VIEW:
#   - qc_pass != 'fail'
#   - proximate_sum between 95 and 105 (or sum == 0 meaning no key params present)
#     sum = moisture + ash_solids + volatile_solids
#     (volatile_solids falls back to 100 - fixed_carbon when absent)
#   - resource exclusions: sargassum, #n/a, lab media, alfalfa,
#     almond hulls and shells mix, almond shells and hulls mix, almond woodchips
#
from audit.targets.registry import AuditTarget, register

register(AuditTarget(
    name="proximate",
    source_type="view",
    description=(
        "Proximate analysis records: moisture, ash, volatile solids, fixed carbon. "
        "Filtered to qc_pass != 'fail' and proximate sum in [95, 105] "
        "(moisture + ash solids + volatile solids). Excludes problematic resources."
    ),

    # Layer 1: population-level stats per resource / parameter / unit
    population_sql="""
        WITH qc_sums AS (
            SELECT
                pr.resource_id,
                pr.experiment_id,
                COALESCE(AVG(CASE WHEN LOWER(p.name) = 'moisture'        THEN o.value END), 0)
                + COALESCE(AVG(CASE WHEN LOWER(p.name) IN ('ash', 'ash solids') THEN o.value END), 0)
                + COALESCE(
                    AVG(CASE WHEN LOWER(p.name) = 'volatile solids' THEN o.value END),
                    100 - COALESCE(AVG(CASE WHEN LOWER(p.name) = 'fixed carbon' THEN o.value END), 0)
                  ) AS proximate_sum
            FROM public.proximate_record pr
            JOIN public.observation o
                ON LOWER(o.record_id) = LOWER(pr.record_id)
                AND o.record_type IN ('proximate analysis', 'proximate_analysis')
            JOIN public.parameter p ON o.parameter_id = p.id
            WHERE pr.qc_pass != 'fail'
            GROUP BY pr.resource_id, pr.experiment_id
        )
        SELECT
            r.name                  AS resource_name,
            CASE WHEN p.name = 'ash' THEN 'ash solids' ELSE LOWER(p.name) END AS parameter_name,
            LOWER(u.name)           AS unit,
            AVG(o.value)            AS avg_value,
            STDDEV(o.value)         AS std_dev,
            MIN(o.value)            AS min_value,
            MAX(o.value)            AS max_value,
            COUNT(o.value)          AS observation_count
        FROM public.proximate_record pr
        JOIN public.resource r ON pr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(pr.record_id)
            AND o.record_type IN ('proximate analysis', 'proximate_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        JOIN qc_sums qs
            ON qs.resource_id = pr.resource_id
            AND COALESCE(qs.experiment_id, -1) = COALESCE(pr.experiment_id, -1)
        WHERE
            pr.qc_pass != 'fail'
            AND LOWER(r.name) NOT IN (
                'sargassum', '#n/a', 'lab media', 'alfalfa',
                'almond hulls and shells mix',
                'almond shells and hulls mix',
                'almond woodchips'
            )
            AND (
                qs.proximate_sum = 0
                OR (qs.proximate_sum >= 95 AND qs.proximate_sum <= 105)
            )
        GROUP BY r.name, p.name, u.name
        HAVING COUNT(o.value) >= 3
    """,

    # Layer 2: individual observations with analyst attribution and QC context
    observation_sql="""
        WITH qc_sums AS (
            SELECT
                pr.resource_id,
                pr.experiment_id,
                COALESCE(AVG(CASE WHEN LOWER(p.name) = 'moisture'        THEN o.value END), 0)
                + COALESCE(AVG(CASE WHEN LOWER(p.name) IN ('ash', 'ash solids') THEN o.value END), 0)
                + COALESCE(
                    AVG(CASE WHEN LOWER(p.name) = 'volatile solids' THEN o.value END),
                    100 - COALESCE(AVG(CASE WHEN LOWER(p.name) = 'fixed carbon' THEN o.value END), 0)
                  ) AS proximate_sum
            FROM public.proximate_record pr
            JOIN public.observation o
                ON LOWER(o.record_id) = LOWER(pr.record_id)
                AND o.record_type IN ('proximate analysis', 'proximate_analysis')
            JOIN public.parameter p ON o.parameter_id = p.id
            WHERE pr.qc_pass != 'fail'
            GROUP BY pr.resource_id, pr.experiment_id
        )
        SELECT
            r.name          AS resource_name,
            CASE WHEN p.name = 'ash' THEN 'ash solids' ELSE LOWER(p.name) END AS parameter_name,
            LOWER(u.name)   AS unit,
            o.value         AS observed_value,
            pr.record_id,
            pr.qc_pass,
            pr.note,
            c.name          AS analyst_name,
            c.email         AS analyst_email,
            pr.created_at
        FROM public.proximate_record pr
        JOIN public.resource r ON pr.resource_id = r.id
        JOIN public.observation o
            ON LOWER(o.record_id) = LOWER(pr.record_id)
            AND o.record_type IN ('proximate analysis', 'proximate_analysis')
        JOIN public.parameter p ON o.parameter_id = p.id
        LEFT JOIN public.unit u ON o.unit_id = u.id
        LEFT JOIN public.contact c ON pr.analyst_id = c.id
        JOIN qc_sums qs
            ON qs.resource_id = pr.resource_id
            AND COALESCE(qs.experiment_id, -1) = COALESCE(pr.experiment_id, -1)
        WHERE
            pr.qc_pass != 'fail'
            AND LOWER(r.name) NOT IN (
                'sargassum', '#n/a', 'lab media', 'alfalfa',
                'almond hulls and shells mix',
                'almond shells and hulls mix',
                'almond woodchips'
            )
            AND (
                qs.proximate_sum = 0
                OR (qs.proximate_sum >= 95 AND qs.proximate_sum <= 105)
            )
    """,

    group_by_cols=["resource_name", "parameter_name", "unit"],
    numeric_cols=["observed_value"],
    id_cols=["record_id", "resource_name", "parameter_name"],
    analyst_col="analyst_email",
    gx_suite_path="audit/expectations/proximate.json",
    use_isolation_forest=False,
))
