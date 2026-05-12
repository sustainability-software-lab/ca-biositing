-- ============================================================================
-- CA Biositing Data Audit Profiling Queries - XRF Comprehensive Audit
-- Focus: XRF records and linked observations, including ALL records (even provisional)
-- ============================================================================

-- 1. XRF RECORD COUNTS BY QC STATUS
\echo '=== 1. XRF RECORD COUNTS BY QC STATUS ==='
SELECT
    qc_pass,
    COUNT(*) AS record_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM xrf_record
GROUP BY qc_pass
ORDER BY record_count DESC;

-- 2. XRF OBSERVATION COUNTS
\echo '=== 2. XRF OBSERVATION COUNTS ==='
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
    WHERE record_type = 'xrf analysis'
    GROUP BY record_id
) subq;

-- 3. XRF PARAMETER COVERAGE (All records)
\echo '=== 3. XRF PARAMETER COVERAGE (ALL RECORDS) ==='
SELECT
    p.name AS parameter_name,
    COALESCE(u.name, '<NULL>') AS unit_name,
    COUNT(*) AS obs_count,
    COUNT(DISTINCT o.record_id) AS records_with_param,
    ROUND(100.0 * COUNT(DISTINCT o.record_id) / (SELECT COUNT(*) FROM xrf_record), 2) AS record_coverage_pct
FROM observation o
LEFT JOIN parameter p ON o.parameter_id = p.id
LEFT JOIN unit u ON o.unit_id = u.id
WHERE o.record_type = 'xrf analysis'
GROUP BY p.name, u.name
ORDER BY obs_count DESC;

-- 4. XRF METADATA COMPLETENESS (All records)
\echo '=== 4. XRF METADATA COMPLETENESS (ALL RECORDS) ==='
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
FROM xrf_record;

-- 5. XRF VALUE RANGES PER PARAMETER (All records)
\echo '=== 5. XRF VALUE RANGES PER PARAMETER ==='
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
WHERE o.record_type = 'xrf analysis' AND o.value IS NOT NULL
GROUP BY p.name, u.name
ORDER BY p.name;

-- 6. XRF SPECIFIC FIELDS COMPLETENESS
\echo '=== 6. XRF SPECIFIC FIELDS COMPLETENESS ==='
SELECT
    COUNT(*) AS total_records,
    COUNT(wavelength_nm) AS wavelength_filled,
    ROUND(100.0 * COUNT(wavelength_nm) / COUNT(*), 2) AS wavelength_pct,
    COUNT(intensity) AS intensity_filled,
    ROUND(100.0 * COUNT(intensity) / COUNT(*), 2) AS intensity_pct,
    COUNT(energy_slope) AS energy_slope_filled,
    ROUND(100.0 * COUNT(energy_slope) / COUNT(*), 2) AS energy_slope_pct,
    COUNT(energy_offset) AS energy_offset_filled,
    ROUND(100.0 * COUNT(energy_offset) / COUNT(*), 2) AS energy_offset_pct
FROM xrf_record;
