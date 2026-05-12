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

-- 11. COMPREHENSIVE FERMENTATION METADATA NULLABILITY AUDIT
-- Audits ALL fermentation_record columns for null counts and completeness
\echo '=== 11. FERMENTATION RECORD COMPREHENSIVE METADATA AUDIT ==='
SELECT
    'updated_at' AS column_name,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE updated_at IS NULL) AS null_count,
    COUNT(*) FILTER (WHERE updated_at IS NOT NULL) AS non_null_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE updated_at IS NOT NULL) /
        NULLIF(COUNT(*), 0), 1) AS pct_populated
FROM fermentation_record
UNION ALL
SELECT 'etl_run_id', COUNT(*), COUNT(*) FILTER (WHERE etl_run_id IS NULL),
    COUNT(*) FILTER (WHERE etl_run_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE etl_run_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'lineage_group_id', COUNT(*), COUNT(*) FILTER (WHERE lineage_group_id IS NULL),
    COUNT(*) FILTER (WHERE lineage_group_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE lineage_group_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'record_id', COUNT(*), COUNT(*) FILTER (WHERE record_id IS NULL),
    COUNT(*) FILTER (WHERE record_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE record_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'dataset_id', COUNT(*), COUNT(*) FILTER (WHERE dataset_id IS NULL),
    COUNT(*) FILTER (WHERE dataset_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE dataset_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'experiment_id', COUNT(*), COUNT(*) FILTER (WHERE experiment_id IS NULL),
    COUNT(*) FILTER (WHERE experiment_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE experiment_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'resource_id', COUNT(*), COUNT(*) FILTER (WHERE resource_id IS NULL),
    COUNT(*) FILTER (WHERE resource_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE resource_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'prepared_sample_id', COUNT(*), COUNT(*) FILTER (WHERE prepared_sample_id IS NULL),
    COUNT(*) FILTER (WHERE prepared_sample_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE prepared_sample_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'technical_replicate_no', COUNT(*), COUNT(*) FILTER (WHERE technical_replicate_no IS NULL),
    COUNT(*) FILTER (WHERE technical_replicate_no IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE technical_replicate_no IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'technical_replicate_total', COUNT(*), COUNT(*) FILTER (WHERE technical_replicate_total IS NULL),
    COUNT(*) FILTER (WHERE technical_replicate_total IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE technical_replicate_total IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'method_id', COUNT(*), COUNT(*) FILTER (WHERE method_id IS NULL),
    COUNT(*) FILTER (WHERE method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE method_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'analyst_id', COUNT(*), COUNT(*) FILTER (WHERE analyst_id IS NULL),
    COUNT(*) FILTER (WHERE analyst_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE analyst_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'raw_data_id', COUNT(*), COUNT(*) FILTER (WHERE raw_data_id IS NULL),
    COUNT(*) FILTER (WHERE raw_data_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE raw_data_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'qc_pass', COUNT(*), COUNT(*) FILTER (WHERE qc_pass IS NULL),
    COUNT(*) FILTER (WHERE qc_pass IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'note', COUNT(*), COUNT(*) FILTER (WHERE note IS NULL),
    COUNT(*) FILTER (WHERE note IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE note IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'strain_id', COUNT(*), COUNT(*) FILTER (WHERE strain_id IS NULL),
    COUNT(*) FILTER (WHERE strain_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE strain_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'bioconversion_method_id', COUNT(*), COUNT(*) FILTER (WHERE bioconversion_method_id IS NULL),
    COUNT(*) FILTER (WHERE bioconversion_method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE bioconversion_method_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'pretreatment_method_id', COUNT(*), COUNT(*) FILTER (WHERE pretreatment_method_id IS NULL),
    COUNT(*) FILTER (WHERE pretreatment_method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE pretreatment_method_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'eh_method_id', COUNT(*), COUNT(*) FILTER (WHERE eh_method_id IS NULL),
    COUNT(*) FILTER (WHERE eh_method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE eh_method_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'well_position', COUNT(*), COUNT(*) FILTER (WHERE well_position IS NULL),
    COUNT(*) FILTER (WHERE well_position IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE well_position IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'vessel_id', COUNT(*), COUNT(*) FILTER (WHERE vessel_id IS NULL),
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE vessel_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
UNION ALL
SELECT 'analyte_detection_equipment_id', COUNT(*), COUNT(*) FILTER (WHERE analyte_detection_equipment_id IS NULL),
    COUNT(*) FILTER (WHERE analyte_detection_equipment_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE analyte_detection_equipment_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1)
FROM fermentation_record
ORDER BY pct_populated DESC, column_name;

-- 12. DEEP DIVE: eh_method_id ANALYSIS
-- Complete nullability analysis for eh_method_id with cross-references
\echo '=== 12. EH_METHOD_ID DEEP DIVE ANALYSIS ==='
SELECT
    'eh_method_id Coverage' AS metric,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE eh_method_id IS NULL) AS null_count,
    COUNT(*) FILTER (WHERE eh_method_id IS NOT NULL) AS populated_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE eh_method_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1) AS pct_populated
FROM fermentation_record
UNION ALL
SELECT
    'eh_method_id with QC Pass',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND eh_method_id IS NULL),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND eh_method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND eh_method_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM fermentation_record
UNION ALL
SELECT
    'eh_method_id with strain_id',
    COUNT(*) FILTER (WHERE strain_id IS NOT NULL),
    COUNT(*) FILTER (WHERE strain_id IS NOT NULL AND eh_method_id IS NULL),
    COUNT(*) FILTER (WHERE strain_id IS NOT NULL AND eh_method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE strain_id IS NOT NULL AND eh_method_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE strain_id IS NOT NULL), 0), 1)
FROM fermentation_record
UNION ALL
SELECT
    'eh_method_id with vessel_id',
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL),
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL AND eh_method_id IS NULL),
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL AND eh_method_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE vessel_id IS NOT NULL AND eh_method_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE vessel_id IS NOT NULL), 0), 1)
FROM fermentation_record;

-- 13. DEEP DIVE: well_position ANALYSIS
-- Complete nullability analysis for well_position
\echo '=== 13. WELL_POSITION DEEP DIVE ANALYSIS ==='
SELECT
    'well_position Coverage' AS metric,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE well_position IS NULL) AS null_count,
    COUNT(*) FILTER (WHERE well_position IS NOT NULL) AS populated_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE well_position IS NOT NULL) / NULLIF(COUNT(*), 0), 1) AS pct_populated
FROM fermentation_record
UNION ALL
SELECT
    'well_position with QC Pass',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND well_position IS NULL),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND well_position IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND well_position IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM fermentation_record
UNION ALL
SELECT
    'well_position with vessel_id',
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL),
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL AND well_position IS NULL),
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL AND well_position IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE vessel_id IS NOT NULL AND well_position IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE vessel_id IS NOT NULL), 0), 1)
FROM fermentation_record
UNION ALL
SELECT
    'Distinct well_position values (non-null)',
    COUNT(DISTINCT well_position),
    0,
    COUNT(DISTINCT well_position),
    100.0
FROM fermentation_record
WHERE well_position IS NOT NULL;

-- 14. DEEP DIVE: vessel_id ANALYSIS
-- Complete nullability analysis for vessel_id with linkage validation
\echo '=== 14. VESSEL_ID DEEP DIVE ANALYSIS ==='
SELECT
    'vessel_id Coverage' AS metric,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE vessel_id IS NULL) AS null_count,
    COUNT(*) FILTER (WHERE vessel_id IS NOT NULL) AS populated_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE vessel_id IS NOT NULL) / NULLIF(COUNT(*), 0), 1) AS pct_populated
FROM fermentation_record
UNION ALL
SELECT
    'vessel_id with QC Pass',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NULL),
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE qc_pass != 'fail'), 0), 1)
FROM fermentation_record
UNION ALL
SELECT
    'vessel_id with strain_id',
    COUNT(*) FILTER (WHERE strain_id IS NOT NULL),
    COUNT(*) FILTER (WHERE strain_id IS NOT NULL AND vessel_id IS NULL),
    COUNT(*) FILTER (WHERE strain_id IS NOT NULL AND vessel_id IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE strain_id IS NOT NULL AND vessel_id IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE strain_id IS NOT NULL), 0), 1)
FROM fermentation_record
UNION ALL
SELECT
    'Unique vessel_id values (non-null)',
    COUNT(DISTINCT vessel_id),
    0,
    COUNT(DISTINCT vessel_id),
    100.0
FROM fermentation_record
WHERE vessel_id IS NOT NULL;

-- 15. METADATA COMPLETENESS MATRIX (QC-Pass Records Only)
-- Summarizes completeness of key metadata fields for QC-pass records
\echo '=== 15. METADATA COMPLETENESS MATRIX (QC-PASS RECORDS) ==='
SELECT
    COUNT(*) FILTER (WHERE qc_pass != 'fail') AS total_qc_pass,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND updated_at IS NOT NULL) AS updated_at_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND etl_run_id IS NOT NULL) AS etl_run_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND lineage_group_id IS NOT NULL) AS lineage_group_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND dataset_id IS NOT NULL) AS dataset_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND resource_id IS NOT NULL) AS resource_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND prepared_sample_id IS NOT NULL) AS prepared_sample_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND analyst_id IS NOT NULL) AS analyst_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND raw_data_id IS NOT NULL) AS raw_data_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND method_id IS NOT NULL) AS method_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND strain_id IS NOT NULL) AS strain_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND vessel_id IS NOT NULL) AS vessel_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND eh_method_id IS NOT NULL) AS eh_method_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND well_position IS NOT NULL) AS well_position_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND pretreatment_method_id IS NOT NULL) AS pretreatment_method_id_filled,
    COUNT(*) FILTER (WHERE qc_pass != 'fail' AND bioconversion_method_id IS NOT NULL) AS bioconversion_method_id_filled
FROM fermentation_record;
