-- ============================================================================
-- CA Biositing Data Audit Profiling Queries - AIM1 Secondary
-- Focus: ICP, XRF, XRD, FTNIR analytical records
-- ============================================================================

-- 1. RECORD COUNTS WITH QC FILTERING
\echo '=== 1. RECORD COUNTS WITH QC FILTERING (AIM1 SECONDARY) ==='
SELECT
    'icp' AS record_type,
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
    COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count,
    COUNT(*) FILTER (WHERE qc_pass IS NULL) AS qc_null_count
FROM icp_record
UNION ALL
SELECT
    'xrf',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM xrf_record
UNION ALL
SELECT
    'xrd',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM xrd_record
UNION ALL
SELECT
    'ftnir',
    COUNT(*),
    COUNT(*) FILTER (WHERE qc_pass = 'pass'),
    COUNT(*) FILTER (WHERE qc_pass = 'fail'),
    COUNT(*) FILTER (WHERE qc_pass IS NULL)
FROM ftnir_record
ORDER BY record_type;

-- 2. OBSERVATION COUNTS PER RECORD TYPE
\echo '=== 2. OBSERVATION COUNTS PER RECORD TYPE (AIM1 SECONDARY) ==='
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
    WHERE record_type IN ('icp analysis', 'xrf analysis', 'xrd analysis', 'ftnir analysis')
    GROUP BY record_type, record_id
) subq
GROUP BY record_type
ORDER BY record_type;

-- 3. METADATA COMPLETENESS (analyst, method, raw_data)
\echo '=== 3. METADATA COMPLETENESS PER RECORD TYPE (AIM1 SECONDARY) ==='
SELECT
    'icp' AS record_type,
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
FROM icp_record
UNION ALL
SELECT
    'xrf',
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
FROM xrf_record
UNION ALL
SELECT
    'xrd',
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
FROM xrd_record
UNION ALL
SELECT
    'ftnir',
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
FROM ftnir_record
ORDER BY record_type;

-- 4. PARAMETER COVERAGE (Top 15 parameters per type)
\echo '=== 4. TOP PARAMETERS BY OBSERVATION COUNT (AIM1 SECONDARY) ==='
WITH icp_qc_pass AS (
    SELECT record_id FROM icp_record WHERE qc_pass != 'fail'
),
xrf_qc_pass AS (
    SELECT record_id FROM xrf_record WHERE qc_pass != 'fail'
),
xrd_qc_pass AS (
    SELECT record_id FROM xrd_record WHERE qc_pass != 'fail'
),
ftnir_qc_pass AS (
    SELECT record_id FROM ftnir_record WHERE qc_pass != 'fail'
)
SELECT
    o.record_type,
    p.name AS parameter_name,
    COALESCE(u.name, '<NULL>') AS unit_name,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT o.record_id) AS records_with_param
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'icp analysis' AND o.record_id IN (SELECT record_id FROM icp_qc_pass)
GROUP BY o.record_type, p.name, u.name
UNION ALL
SELECT
    o.record_type,
    p.name,
    COALESCE(u.name, '<NULL>'),
    COUNT(*),
    COUNT(DISTINCT o.record_id)
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'xrf analysis' AND o.record_id IN (SELECT record_id FROM xrf_qc_pass)
GROUP BY o.record_type, p.name, u.name
UNION ALL
SELECT
    o.record_type,
    p.name,
    COALESCE(u.name, '<NULL>'),
    COUNT(*),
    COUNT(DISTINCT o.record_id)
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'xrd analysis' AND o.record_id IN (SELECT record_id FROM xrd_qc_pass)
GROUP BY o.record_type, p.name, u.name
UNION ALL
SELECT
    o.record_type,
    p.name,
    COALESCE(u.name, '<NULL>'),
    COUNT(*),
    COUNT(DISTINCT o.record_id)
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'ftnir analysis' AND o.record_id IN (SELECT record_id FROM ftnir_qc_pass)
GROUP BY o.record_type, p.name, u.name
ORDER BY record_type, obs_count DESC
LIMIT 60;

-- 5. SAMPLE & RESOURCE COVERAGE
\echo '=== 5. SAMPLE & RESOURCE COVERAGE (AIM1 SECONDARY) ==='
SELECT
    'icp' AS record_type,
    COUNT(*) FILTER (WHERE qc_pass != 'fail') AS total_qc_pass,
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail') AS unique_prepared_samples,
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail') AS unique_resources,
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail') AS unique_experiments
FROM icp_record
UNION ALL
SELECT
    'xrf',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail')
FROM xrf_record
UNION ALL
SELECT
    'xrd',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail')
FROM xrd_record
UNION ALL
SELECT
    'ftnir',
    COUNT(*) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT prepared_sample_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT resource_id) FILTER (WHERE qc_pass != 'fail'),
    COUNT(DISTINCT experiment_id) FILTER (WHERE qc_pass != 'fail')
FROM ftnir_record
ORDER BY record_type;

-- 6. QC DISTRIBUTION COMPARISON
\echo '=== 6. QC PASS RATES COMPARISON (AIM1 SECONDARY) ==='
SELECT
    record_type,
    total_records,
    qc_pass_count,
    ROUND(100.0 * qc_pass_count / NULLIF(total_records, 0), 1) AS qc_pass_pct,
    qc_fail_count,
    ROUND(100.0 * qc_fail_count / NULLIF(total_records, 0), 1) AS qc_fail_pct
FROM (
    SELECT
        'icp' AS record_type,
        COUNT(*) AS total_records,
        COUNT(*) FILTER (WHERE qc_pass = 'pass') AS qc_pass_count,
        COUNT(*) FILTER (WHERE qc_pass = 'fail') AS qc_fail_count
    FROM icp_record
    UNION ALL
    SELECT
        'xrf',
        COUNT(*),
        COUNT(*) FILTER (WHERE qc_pass = 'pass'),
        COUNT(*) FILTER (WHERE qc_pass = 'fail')
    FROM xrf_record
    UNION ALL
    SELECT
        'xrd',
        COUNT(*),
        COUNT(*) FILTER (WHERE qc_pass = 'pass'),
        COUNT(*) FILTER (WHERE qc_pass = 'fail')
    FROM xrd_record
    UNION ALL
    SELECT
        'ftnir',
        COUNT(*),
        COUNT(*) FILTER (WHERE qc_pass = 'pass'),
        COUNT(*) FILTER (WHERE qc_pass = 'fail')
    FROM ftnir_record
) subq
ORDER BY record_type;
