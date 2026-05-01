-- ============================================================================
-- CA Biositing Data Audit Profiling Queries - ICP Comprehensive Audit
-- Focus: ICP records and linked observations, including ALL records
-- ============================================================================

-- 1. ICP RECORD COUNTS BY QC STATUS
\echo '=== 1. ICP RECORD COUNTS BY QC STATUS ==='
SELECT
    qc_pass,
    COUNT(*) AS record_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM icp_record
GROUP BY qc_pass
ORDER BY record_count DESC;

-- 2. ICP OBSERVATION COUNTS
\echo '=== 2. ICP OBSERVATION COUNTS ==='
SELECT
    COUNT(*) AS total_observations,
    COUNT(DISTINCT record_id) AS records_with_observations,
    ROUND(AVG(obs_per_record), 2) AS avg_obs_per_record,
    MIN(obs_per_record) AS min_obs_per_record,
    MAX(obs_per_record) AS max_obs_per_record
FROM (
    SELECT
        record_id,
        COUNT(*) AS obs_per_record
    FROM observation
    WHERE record_type = 'icp analysis'
    GROUP BY record_id
) subq;

-- 3. ICP PARAMETER COVERAGE (All records)
\echo '=== 3. ICP PARAMETER COVERAGE (ALL RECORDS) ==='
SELECT
    p.name AS parameter_name,
    COALESCE(u.name, '<NULL>') AS unit_name,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT o.record_id) AS records_with_param,
    ROUND(100.0 * COUNT(DISTINCT o.record_id) / (SELECT COUNT(*) FROM icp_record), 2) AS record_coverage_pct
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'icp analysis'
GROUP BY p.name, u.name
ORDER BY obs_count DESC;

-- 4. ICP METADATA COMPLETENESS (All records)
\echo '=== 4. ICP METADATA COMPLETENESS (ALL RECORDS) ==='
SELECT
    COUNT(*) AS total_records,
    COUNT(analyst_id) AS analyst_filled,
    ROUND(100.0 * COUNT(analyst_id) / COUNT(*), 2) AS analyst_pct,
    COUNT(method_id) AS method_filled,
    ROUND(100.0 * COUNT(method_id) / COUNT(*), 2) AS method_pct,
    COUNT(raw_data_id) AS raw_data_filled,
    ROUND(100.0 * COUNT(raw_data_id) / COUNT(*), 2) AS raw_data_pct,
    COUNT(prepared_sample_id) AS sample_filled,
    ROUND(100.0 * COUNT(prepared_sample_id) / COUNT(*), 2) AS sample_pct,
    COUNT(experiment_id) AS experiment_filled,
    ROUND(100.0 * COUNT(experiment_id) / COUNT(*), 2) AS experiment_pct
FROM icp_record;

-- 5. ICP VALUE RANGES PER PARAMETER (All records)
\echo '=== 5. ICP VALUE RANGES PER PARAMETER ==='
SELECT
    p.name AS parameter_name,
    COALESCE(u.name, '<NULL>') AS unit_name,
    COUNT(*) AS obs_count,
    MIN(o.value) AS min_value,
    MAX(o.value) AS max_value,
    ROUND(AVG(o.value)::NUMERIC, 4) AS avg_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o.value) AS median_value
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'icp analysis' AND o.value IS NOT NULL
GROUP BY p.name, u.name
ORDER BY p.name;
