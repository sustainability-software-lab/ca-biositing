-- ============================================================================
-- CA Biositing Data Audit Profiling Queries - AIM2
-- Focus: fermentation, gasification, pretreatment, autoclave records
-- ============================================================================

-- 1. RECORD COUNTS WITH QC FILTERING
-- Shows total, pass, fail, and null QC statuses per record type
\echo '=== 1. RECORD COUNTS WITH QC FILTERING ==='
SELECT
    'fermentation' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count
FROM fermentation_record
UNION ALL
SELECT
    'gasification',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM gasification_record
UNION ALL
SELECT
    'pretreatment',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM pretreatment_record
UNION ALL
SELECT
    'autoclave',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM autoclave_record
ORDER BY record_type;

-- 2. OBSERVATION COUNTS PER RECORD TYPE
-- Shows total observations linked to each record type
\echo '=== 2. OBSERVATION COUNTS PER RECORD TYPE ==='
SELECT
    record_type,
    COUNT(*) AS total_observations,
    COUNT(DISTINCT record_id) AS unique_records,
    ROUND(AVG(obs_per_record), 2) AS avg_obs_per_record,
    MIN(obs_per_record) AS min_obs_per_record,
    MAX(obs_per_record) AS max_obs_per_record
FROM (
    SELECT
        record_type,
        record_id,
        COUNT(*) AS obs_per_record
    FROM observation
    WHERE record_type IN ('fermentation', 'gasification', 'pretreatment', 'autoclave')
    GROUP BY record_type, record_id
) subq
GROUP BY record_type
ORDER BY record_type;

-- 3. PARAMETER COVERAGE PER RECORD TYPE (With QC Filtering)
-- Shows which parameters are present per record type, including unit info
\echo '=== 3. PARAMETER COVERAGE PER RECORD TYPE ==='
WITH fermentation_qc_pass AS (
    SELECT record_id FROM fermentation_record WHERE qc_pass != 'fail'
),
gasification_qc_pass AS (
    SELECT record_id FROM gasification_record WHERE qc_pass != 'fail'
),
pretreatment_qc_pass AS (
    SELECT record_id FROM pretreatment_record WHERE qc_pass != 'fail'
),
autoclave_qc_pass AS (
    SELECT record_id FROM autoclave_record WHERE qc_pass != 'fail'
)
SELECT
    o.record_type,
    p.name AS parameter_name,
    COALESCE(u.name, '<NULL>') AS unit_name,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT o.record_id) AS records_with_param,
    COUNT(DISTINCT o.value) FILTER (WHERE o.value IS NOT NULL) AS non_null_values,
    COUNT(o.value) FILTER (WHERE o.value IS NULL) AS null_values
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'fermentation' AND o.record_id IN (SELECT record_id FROM fermentation_qc_pass)
GROUP BY o.record_type, p.name, u.name
UNION ALL
SELECT
    o.record_type,
    p.name,
    COALESCE(u.name, '<NULL>'),
    COUNT(*),
    COUNT(DISTINCT o.record_id),
    COUNT(DISTINCT o.value) FILTER (WHERE o.value IS NOT NULL),
    COUNT(o.value) FILTER (WHERE o.value IS NULL)
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'gasification' AND o.record_id IN (SELECT record_id FROM gasification_qc_pass)
GROUP BY o.record_type, p.name, u.name
UNION ALL
SELECT
    o.record_type,
    p.name,
    COALESCE(u.name, '<NULL>'),
    COUNT(*),
    COUNT(DISTINCT o.record_id),
    COUNT(DISTINCT o.value) FILTER (WHERE o.value IS NOT NULL),
    COUNT(o.value) FILTER (WHERE o.value IS NULL)
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'pretreatment' AND o.record_id IN (SELECT record_id FROM pretreatment_qc_pass)
GROUP BY o.record_type, p.name, u.name
UNION ALL
SELECT
    o.record_type,
    p.name,
    COALESCE(u.name, '<NULL>'),
    COUNT(*),
    COUNT(DISTINCT o.record_id),
    COUNT(DISTINCT o.value) FILTER (WHERE o.value IS NOT NULL),
    COUNT(o.value) FILTER (WHERE o.value IS NULL)
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'autoclave' AND o.record_id IN (SELECT record_id FROM autoclave_qc_pass)
GROUP BY o.record_type, p.name, u.name
ORDER BY record_type, parameter_name, unit_name;

-- 4. PLACEHOLDER VALUES DETECTION
-- Looks for common placeholder patterns: "nd", "blank", empty strings, etc.
\echo '=== 4. PLACEHOLDER VALUES DETECTION ==='
SELECT
    record_type,
    parameter_name,
    CASE
        WHEN CAST(value AS TEXT) ILIKE 'nd%' THEN 'ND pattern'
        WHEN CAST(value AS TEXT) ILIKE 'blank%' THEN 'BLANK pattern'
        WHEN CAST(value AS TEXT) = '' THEN 'Empty string'
        WHEN value IS NULL AND note LIKE '%nd%' THEN 'ND in note'
        WHEN value IS NULL AND note LIKE '%blank%' THEN 'BLANK in note'
        ELSE 'Other'
    END AS placeholder_type,
    COUNT(*) AS count
FROM (
    SELECT
        o.record_type,
        p.name AS parameter_name,
        o.value,
        o.note
    FROM observation o
    LEFT JOIN parameter p ON o.parameter_id = p.id
    WHERE (CAST(o.value AS TEXT) ILIKE '%nd%'
        OR CAST(o.value AS TEXT) ILIKE '%blank%'
        OR o.note ILIKE '%nd%'
        OR o.note ILIKE '%blank%')
        AND o.record_type IN ('fermentation', 'gasification', 'pretreatment', 'autoclave')
) subq
GROUP BY record_type, parameter_name, placeholder_type
ORDER BY record_type, parameter_name, count DESC;

-- 5. UNIT VARIATION PER PARAMETER
-- Shows which units are used for each parameter
\echo '=== 5. UNIT VARIATION PER PARAMETER ==='
SELECT
    p.name AS parameter_name,
    COALESCE(u.name, '<NULL>') AS unit_name,
    COUNT(*) AS observation_count,
    STRING_AGG(DISTINCT o.record_type, ', ') AS record_types
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type IN ('fermentation', 'gasification', 'pretreatment', 'autoclave')
GROUP BY p.name, u.name
ORDER BY parameter_name, observation_count DESC;

-- 6. METADATA COMPLETENESS (analyst, method, raw_data)
-- Shows what % of records have analyst_id, method_id, raw_data_id populated
\echo '=== 6. METADATA COMPLETENESS PER RECORD TYPE ==='
SELECT
    'fermentation' AS record_type,
    COUNT(*) FILTER (WHERE qc_pass != 'fail') AS total_qc_pass,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL) AS analyst_filled,
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1) AS analyst_pct,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL) AS method_filled,
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1) AS method_pct,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL) AS raw_data_filled,
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1) AS raw_data_pct
FROM fermentation_record
UNION ALL
SELECT
    'gasification',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM gasification_record
UNION ALL
SELECT
    'pretreatment',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM pretreatment_record
UNION ALL
SELECT
    'autoclave',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM autoclave_record
ORDER BY record_type;

-- 7. SAMPLE & RESOURCE COVERAGE
-- Shows prepared samples and resources linked to each record type
\echo '=== 7. SAMPLE & RESOURCE COVERAGE ==='
SELECT
    'fermentation' AS record_type,
    COUNT(*) FILTER (WHERE qc_pass != 'fail') AS total_qc_pass,
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail') AS unique_prepared_samples,
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail') AS unique_resources,
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail') AS unique_experiments
FROM fermentation_record
UNION ALL
SELECT
    'gasification',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail')
FROM gasification_record
UNION ALL
SELECT
    'pretreatment',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail')
FROM pretreatment_record
UNION ALL
SELECT
    'autoclave',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail')
FROM autoclave_record
ORDER BY record_type;

-- 8. VALUE RANGES & OUTLIERS (FOR NUMERIC PARAMETERS)
-- Shows min, max, median, avg for each parameter
\echo '=== 8. VALUE RANGES & OUTLIERS (NUMERIC PARAMETERS) ==='
SELECT
    o.record_type,
    p.name AS parameter_name,
    COALESCE(u.name, '<NULL>') AS unit_name,
    COUNT(o.value) FILTER (WHERE o.value IS NOT NULL AND o.value::text ~ '^\d+\.?\d*$') AS numeric_count,
    MIN((CASE WHEN o.value::text ~ '^\d+\.?\d*$' THEN o.value::NUMERIC ELSE NULL END)) AS min_value,
    MAX((CASE WHEN o.value::text ~ '^\d+\.?\d*$' THEN o.value::NUMERIC ELSE NULL END)) AS max_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (CASE WHEN o.value::text ~ '^\d+\.?\d*$' THEN o.value::NUMERIC ELSE NULL END)) AS median_value,
    ROUND(AVG((CASE WHEN o.value::text ~ '^\d+\.?\d*$' THEN o.value::NUMERIC ELSE NULL END))::NUMERIC, 4) AS avg_value
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type IN ('fermentation', 'gasification', 'pretreatment', 'autoclave')
GROUP BY o.record_type, p.name, u.name
HAVING COUNT(o.value) FILTER (WHERE o.value IS NOT NULL AND o.value::text ~ '^\d+\.?\d*$') > 0
ORDER BY record_type, parameter_name, unit_name;

-- 9. EXPERIMENT LINKAGE ANALYSIS
-- Shows experiment_id distribution for QC-pass records
\echo '=== 9. EXPERIMENT LINKAGE ANALYSIS ==='
SELECT
    'fermentation' AS record_type,
    COUNT(*) FILTER (WHERE qc_pass != 'fail') AS total_qc_pass,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NULL) AS no_experiment,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL) AS with_experiment,
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1) AS experiment_coverage_pct
FROM fermentation_record
UNION ALL
SELECT
    'gasification',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NULL),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM gasification_record
UNION ALL
SELECT
    'pretreatment',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NULL),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM pretreatment_record
UNION ALL
SELECT
    'autoclave',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NULL),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND experiment_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM autoclave_record
ORDER BY record_type;

-- 10. RECORD-SPECIFIC FIELD COMPLETENESS
-- Shows coverage of record-specific fields (vessel, method, strain, etc.)
\echo '=== 10. RECORD-SPECIFIC FIELD COMPLETENESS ==='
SELECT
    'fermentation - strain_id' AS record_type,
    COUNT(*) FILTER (WHERE qc_pass != 'fail') AS total_qc_pass,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND strain_id IS NOT NULL) AS field_filled,
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND strain_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1) AS field_pct
FROM fermentation_record
UNION ALL
SELECT
    'fermentation - vessel_id',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM fermentation_record
UNION ALL
SELECT
    'gasification - reactor_type_id',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND reactor_type_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND reactor_type_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM gasification_record
UNION ALL
SELECT
    'pretreatment - vessel_id',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM pretreatment_record
UNION ALL
SELECT
    'pretreatment - temperature',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND temperature IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND temperature IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM pretreatment_record
ORDER BY record_type;
