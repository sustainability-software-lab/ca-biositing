-- ============================================================================
-- CA Biositing Data Audit Profiling Queries
-- Focus: proximate, ultimate, compositional records with QC filtering
-- ============================================================================

-- 1. RECORD COUNTS WITH QC FILTERING
-- Shows total, pass, fail, and null QC statuses per record type
\echo '=== 1. RECORD COUNTS WITH QC FILTERING ==='
SELECT
    'proximate' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count
FROM proximate_record
UNION ALL
SELECT
    'ultimate',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM ultimate_record
UNION ALL
SELECT
    'compositional',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM compositional_record;

-- 2. OBSERVATION COUNTS PER RECORD TYPE
-- Shows total observations linked to each record type
\echo '=== 2. OBSERVATION COUNTS PER RECORD TYPE ==='
SELECT
    record_type,
    COUNT(*) AS total_observations,
    COUNT(DISTINCT record_id) AS unique_records,
    ROUND(AVG(obs_per_record), 2) AS avg_obs_per_record
FROM (
    SELECT
        record_type,
        record_id,
        COUNT(*) AS obs_per_record
    FROM observation
    WHERE record_type IN ('proximate analysis', 'ultimate analysis', 'compositional analysis')
    GROUP BY record_type, record_id
) subq
GROUP BY record_type
ORDER BY record_type;

-- 3. PARAMETER COVERAGE PER RECORD TYPE (With QC Filtering)
-- Shows which parameters are present per record type, including unit info
\echo '=== 3. PARAMETER COVERAGE PER RECORD TYPE ==='
WITH proximate_qc_pass AS (
    SELECT record_id FROM proximate_record WHERE qc_pass != 'fail'
),
ultimate_qc_pass AS (
    SELECT record_id FROM ultimate_record WHERE qc_pass != 'fail'
),
compositional_qc_pass AS (
    SELECT record_id FROM compositional_record WHERE qc_pass != 'fail'
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
WHERE o.record_type = 'proximate analysis' AND o.record_id IN (SELECT record_id FROM proximate_qc_pass)
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
WHERE o.record_type = 'ultimate analysis' AND o.record_id IN (SELECT record_id FROM ultimate_qc_pass)
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
WHERE o.record_type = 'compositional analysis' AND o.record_id IN (SELECT record_id FROM compositional_qc_pass)
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
        AND o.record_type IN ('proximate analysis', 'ultimate analysis', 'compositional analysis')
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
WHERE o.record_type IN ('proximate analysis', 'ultimate analysis', 'compositional analysis')
GROUP BY p.name, u.name
ORDER BY parameter_name, observation_count DESC;

-- 6. DUPLICATE DETECTION (Same sample, conflicting observations)
-- Checks for records with same prepared_sample but conflicting parameter values
\echo '=== 6. DUPLICATE DETECTION ==='
WITH prox_duplicates AS (
    SELECT
        prepared_sample_id,
        p.name AS parameter_name,
        COUNT(DISTINCT o.value) AS value_count,
        STRING_AGG(DISTINCT CAST(o.value AS TEXT), ' | ') AS values_seen,
        COUNT(*) AS obs_count
    FROM proximate_record pr
    JOIN observation o ON pr.record_id = o.record_id AND o.record_type = 'proximate analysis'
    JOIN parameter p ON o.parameter_id = p.id
    WHERE pr.qc_pass != 'fail'
    GROUP BY prepared_sample_id, p.name
    HAVING COUNT(DISTINCT o.value) > 1
)
SELECT
    'proximate' AS record_type,
    prepared_sample_id,
    parameter_name,
    value_count,
    values_seen,
    obs_count
FROM prox_duplicates
UNION ALL
SELECT
    'ultimate',
    prepared_sample_id,
    parameter_name,
    value_count,
    values_seen,
    obs_count
FROM (
    SELECT
        prepared_sample_id,
        p.name AS parameter_name,
        COUNT(DISTINCT o.value) AS value_count,
        STRING_AGG(DISTINCT CAST(o.value AS TEXT), ' | ') AS values_seen,
        COUNT(*) AS obs_count
    FROM ultimate_record ur
    JOIN observation o ON ur.record_id = o.record_id AND o.record_type = 'ultimate analysis'
    JOIN parameter p ON o.parameter_id = p.id
    WHERE ur.qc_pass != 'fail'
    GROUP BY prepared_sample_id, p.name
    HAVING COUNT(DISTINCT o.value) > 1
) ult_dups
UNION ALL
SELECT
    'compositional',
    prepared_sample_id,
    parameter_name,
    value_count,
    values_seen,
    obs_count
FROM (
    SELECT
        prepared_sample_id,
        p.name AS parameter_name,
        COUNT(DISTINCT o.value) AS value_count,
        STRING_AGG(DISTINCT CAST(o.value AS TEXT), ' | ') AS values_seen,
        COUNT(*) AS obs_count
    FROM compositional_record cr
    JOIN observation o ON cr.record_id = o.record_id AND o.record_type = 'compositional analysis'
    JOIN parameter p ON o.parameter_id = p.id
    WHERE cr.qc_pass != 'fail'
    GROUP BY prepared_sample_id, p.name
    HAVING COUNT(DISTINCT o.value) > 1
) comp_dups
ORDER BY record_type, prepared_sample_id;

-- 7. DIMENSION BASIS ANALYSIS (wet vs. dry basis)
-- Shows dimension_type usage per parameter
\echo '=== 7. DIMENSION BASIS ANALYSIS ==='
SELECT
    o.record_type,
    p.name AS parameter_name,
    dt.name AS dimension_type,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT o.dimension_value) AS distinct_dim_values,
    COUNT(o.dimension_value) FILTER (WHERE o.dimension_value IS NULL) AS null_dim_values
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN dimension_type dt ON o.dimension_type_id = dt.id
WHERE o.record_type IN ('proximate analysis', 'ultimate analysis', 'compositional analysis')
    AND o.dimension_type_id IS NOT NULL
GROUP BY o.record_type, p.name, dt.name
ORDER BY record_type, parameter_name, dimension_type;

-- 8. METADATA COMPLETENESS (analyst, method, raw_data)
-- Shows coverage of optional metadata fields per record type
\echo '=== 8. METADATA COMPLETENESS ==='
SELECT
    'proximate' AS record_type,
    COUNT(*) AS total_qc_pass,
    COUNT(analyst_id) AS analyst_id_filled,
    ROUND(100.0 * COUNT(analyst_id) / COUNT(*), 2) AS analyst_pct,
    COUNT(method_id) AS method_id_filled,
    ROUND(100.0 * COUNT(method_id) / COUNT(*), 2) AS method_pct,
    COUNT(raw_data_id) AS raw_data_filled,
    ROUND(100.0 * COUNT(raw_data_id) / COUNT(*), 2) AS raw_data_pct
FROM proximate_record
WHERE qc_pass != 'fail'
UNION ALL
SELECT
    'ultimate',
    COUNT(*),
    COUNT(analyst_id),
    ROUND(100.0 * COUNT(analyst_id) / COUNT(*), 2),
    COUNT(method_id),
    ROUND(100.0 * COUNT(method_id) / COUNT(*), 2),
    COUNT(raw_data_id),
    ROUND(100.0 * COUNT(raw_data_id) / COUNT(*), 2)
FROM ultimate_record
WHERE qc_pass != 'fail'
UNION ALL
SELECT
    'compositional',
    COUNT(*),
    COUNT(analyst_id),
    ROUND(100.0 * COUNT(analyst_id) / COUNT(*), 2),
    COUNT(method_id),
    ROUND(100.0 * COUNT(method_id) / COUNT(*), 2),
    COUNT(raw_data_id),
    ROUND(100.0 * COUNT(raw_data_id) / COUNT(*), 2)
FROM compositional_record
WHERE qc_pass != 'fail';

-- 9. SAMPLE COVERAGE (prepared_sample linkage)
-- Shows how many unique prepared_samples per record type
\echo '=== 9. SAMPLE COVERAGE ==='
SELECT
    'proximate' AS record_type,
    COUNT(*) AS total_records,
    COUNT(DISTINCT prepared_sample_id) AS unique_prepared_samples,
    COUNT(DISTINCT resource_id) AS unique_resources,
    COUNT(DISTINCT experiment_id) AS unique_experiments
FROM proximate_record
WHERE qc_pass != 'fail'
UNION ALL
SELECT
    'ultimate',
    COUNT(*),
    COUNT(DISTINCT prepared_sample_id),
    COUNT(DISTINCT resource_id),
    COUNT(DISTINCT experiment_id)
FROM ultimate_record
WHERE qc_pass != 'fail'
UNION ALL
SELECT
    'compositional',
    COUNT(*),
    COUNT(DISTINCT prepared_sample_id),
    COUNT(DISTINCT resource_id),
    COUNT(DISTINCT experiment_id)
FROM compositional_record
WHERE qc_pass != 'fail';

-- 10. VALUE RANGES (min, max, distribution) - Per Parameter
-- Identifies outliers and value ranges
\echo '=== 10. VALUE RANGES PER PARAMETER ==='
SELECT
    o.record_type,
    p.name AS parameter_name,
    COUNT(*) AS obs_count,
    MIN(o.value) AS min_value,
    MAX(o.value) AS max_value,
    ROUND(AVG(o.value)::NUMERIC, 4) AS avg_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o.value) AS median_value
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
WHERE o.record_type IN ('proximate analysis', 'ultimate analysis', 'compositional analysis')
    AND o.value IS NOT NULL
GROUP BY o.record_type, p.name
ORDER BY record_type, parameter_name;
