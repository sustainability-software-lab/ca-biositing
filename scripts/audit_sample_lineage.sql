-- ============================================================================
-- CA Biositing Data Audit Profiling Queries - Sample Tracking & Lineage
-- Focus: primary_ag_product -> resource -> field_sample -> prepared_sample
-- ============================================================================

-- 1. GLOBAL RECORD COUNTS
\echo '=== 1. GLOBAL RECORD COUNTS ==='
SELECT
    (SELECT COUNT(*) FROM primary_ag_product) AS primary_ag_products,
    (SELECT COUNT(*) FROM resource) AS resources,
    (SELECT COUNT(*) FROM field_sample) AS field_samples,
    (SELECT COUNT(*) FROM prepared_sample) AS prepared_samples;

-- 2. CHAIN CONNECTIVITY (Downstream to Upstream)
\echo '=== 2. CHAIN CONNECTIVITY ==='

-- 2.1 Prepared Sample -> Field Sample
\echo '--- 2.1 Prepared Sample -> Field Sample ---'
SELECT
    COUNT(*) AS total_prepared_samples,
    COUNT(field_sample_id) AS records_with_field_sample,
    ROUND(100.0 * COUNT(field_sample_id) / COUNT(*), 2) AS connectivity_pct
FROM prepared_sample;

-- 2.2 Field Sample -> Resource
\echo '--- 2.2 Field Sample -> Resource ---'
SELECT
    COUNT(*) AS total_field_samples,
    COUNT(resource_id) AS records_with_resource,
    ROUND(100.0 * COUNT(resource_id) / COUNT(*), 2) AS connectivity_pct
FROM field_sample;

-- 2.3 Resource -> Primary Ag Product
\echo '--- 2.3 Resource -> Primary Ag Product ---'
SELECT
    COUNT(*) AS total_resources,
    COUNT(primary_ag_product_id) AS records_with_primary_ag,
    ROUND(100.0 * COUNT(primary_ag_product_id) / COUNT(*), 2) AS connectivity_pct
FROM resource;

-- 2.4 Full Chain Integrity (Prepared -> Primary Ag Product)
\echo '--- 2.4 Full Chain Integrity ---'
SELECT
    COUNT(ps.id) AS total_prepared_samples,
    COUNT(pap.id) AS fully_linked_to_ag_product,
    ROUND(100.0 * COUNT(pap.id) / COUNT(ps.id), 2) AS full_lineage_pct
FROM prepared_sample ps
LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
LEFT JOIN resource r ON fs.resource_id = r.id
LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id;

-- 3. UNIQUE RESOURCES IN PREPARED SAMPLES
\echo '=== 3. UNIQUE RESOURCES IN PREPARED SAMPLES ==='
SELECT
    COUNT(DISTINCT r.id) AS unique_resources_in_prepared_samples,
    COUNT(DISTINCT pap.id) AS unique_primary_ag_products_in_prepared_samples
FROM prepared_sample ps
JOIN field_sample fs ON ps.field_sample_id = fs.id
JOIN resource r ON fs.resource_id = r.id
JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id;

-- 4. METADATA INTEGRITY
\echo '=== 4. METADATA INTEGRITY ==='

-- 4.1 Provider Coverage (Field Sample)
\echo '--- 4.1 Provider Coverage (Field Sample) ---'
SELECT
    COUNT(*) AS total_field_samples,
    COUNT(provider_id) AS provider_filled,
    ROUND(100.0 * COUNT(provider_id) / COUNT(*), 2) AS provider_pct
FROM field_sample;

-- 4.2 Preparation Method Coverage (Prepared Sample)
\echo '--- 4.2 Preparation Method Coverage (Prepared Sample) ---'
SELECT
    COUNT(*) AS total_prepared_samples,
    COUNT(prep_method_id) AS prep_method_filled,
    ROUND(100.0 * COUNT(prep_method_id) / COUNT(*), 2) AS prep_method_pct
FROM prepared_sample;

-- 4.3 Technical Replicate Usage
-- Note: These fields typically exist on analytical records linking to prepared_sample
\echo '--- 4.3 Technical Replicate Usage (Aggregated across Aim 1 Records) ---'
SELECT
    'icp_record' AS table_name,
    COUNT(*) AS total_records,
    COUNT(technical_replicate_no) AS replicate_no_filled,
    COUNT(technical_replicate_total) AS replicate_total_filled,
    ROUND(100.0 * COUNT(technical_replicate_no) / COUNT(*), 2) AS replicate_no_pct
FROM icp_record
UNION ALL
SELECT
    'xrf_record' AS table_name,
    COUNT(*) AS total_records,
    COUNT(technical_replicate_no) AS replicate_no_filled,
    COUNT(technical_replicate_total) AS replicate_total_filled,
    ROUND(100.0 * COUNT(technical_replicate_no) / COUNT(*), 2) AS replicate_no_pct
FROM xrf_record;

-- 5. GEOGRAPHICAL LINKING
\echo '=== 5. GEOGRAPHICAL LINKING ==='
SELECT
    COUNT(*) AS total_field_samples,
    COUNT(sampling_location_id) AS location_id_filled,
    ROUND(100.0 * COUNT(sampling_location_id) / COUNT(*), 2) AS location_pct
FROM field_sample;

-- 6. IDENTIFYING BROKEN LINKS (Orphans)
\echo '=== 6. IDENTIFYING BROKEN LINKS (ORPHANS) ==='

-- 6.1 Prepared Samples with missing or invalid field_sample_id
\echo '--- 6.1 Orphaned Prepared Samples ---'
SELECT id, name, field_sample_id
FROM prepared_sample
WHERE field_sample_id IS NULL OR field_sample_id NOT IN (SELECT id FROM field_sample)
LIMIT 10;

-- 6.2 Field Samples with missing or invalid resource_id
\echo '--- 6.2 Orphaned Field Samples ---'
SELECT id, name, resource_id
FROM field_sample
WHERE resource_id IS NULL OR resource_id NOT IN (SELECT id FROM resource)
LIMIT 10;

-- 7. GEOGRAPHICAL ANALYSIS
\echo '=== 7. GEOGRAPHICAL ANALYSIS ==='

-- 7.1 Unique GEOIDs in Field Samples (via location_address)
\echo '--- 7.1 Unique GEOIDs in Field Samples ---'
SELECT
    COUNT(DISTINCT la.geography_id) AS unique_geoids,
    COUNT(DISTINCT fs.id) AS total_field_samples_with_location,
    ROUND(100.0 * COUNT(DISTINCT la.geography_id) / COUNT(DISTINCT fs.id), 2) AS geoid_diversity_pct
FROM field_sample fs
LEFT JOIN location_address la ON fs.sampling_location_id = la.id
WHERE la.geography_id IS NOT NULL;

-- 7.2 GEOID Distribution (Top 10 most common)
\echo '--- 7.2 Top 10 Most Common GEOIDs in Field Samples ---'
SELECT
    la.geography_id,
    p.state_name,
    COUNT(DISTINCT fs.id) AS field_samples_count,
    COUNT(DISTINCT r.id) AS unique_resources,
    ROUND(100.0 * COUNT(DISTINCT fs.id) / (SELECT COUNT(*) FROM field_sample WHERE sampling_location_id IN (SELECT id FROM location_address)), 2) AS pct_of_total
FROM field_sample fs
JOIN location_address la ON fs.sampling_location_id = la.id
LEFT JOIN place p ON la.geography_id = p.geoid
LEFT JOIN resource r ON fs.resource_id = r.id
GROUP BY la.geography_id, p.state_name
ORDER BY field_samples_count DESC
LIMIT 10;

-- 7.3 Missing Location Data
\echo '--- 7.3 Missing Location Data ---'
SELECT
    COUNT(*) AS field_samples_no_location,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM field_sample), 2) AS pct_missing
FROM field_sample
WHERE sampling_location_id IS NULL;

-- 7.4 Location Address Completeness
\echo '--- 7.4 Location Address Completeness ---'
SELECT
    COUNT(*) AS total_locations,
    COUNT(geography_id) AS locations_with_geoid,
    COUNT(address_line1) AS locations_with_address,
    ROUND(100.0 * COUNT(geography_id) / COUNT(*), 2) AS geoid_coverage_pct,
    ROUND(100.0 * COUNT(address_line1) / COUNT(*), 2) AS address_coverage_pct
FROM location_address;

-- 8. RESIDUE FACTOR ANALYSIS
\echo '=== 8. RESIDUE FACTOR ANALYSIS ==='

-- 8.1 Residue Factor Coverage
\echo '--- 8.1 Residue Factor Coverage ---'
SELECT
    COUNT(*) AS total_residue_factors,
    COUNT(DISTINCT resource_id) AS resources_with_factors,
    COUNT(DISTINCT CASE WHEN factor_min IS NOT NULL OR factor_max IS NOT NULL THEN resource_id END) AS resources_with_min_max_values,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN factor_min IS NOT NULL OR factor_max IS NOT NULL THEN resource_id END) / COUNT(DISTINCT resource_id), 2) AS completeness_pct
FROM residue_factor;

-- 8.2 Resources in Sample Lineage vs. Residue Factor Coverage
\echo '--- 8.2 Sample Lineage Resources vs. Residue Factor Coverage ---'
SELECT
    COUNT(DISTINCT r.id) AS total_resources_in_lineage,
    COUNT(DISTINCT rf.resource_id) AS resources_with_residue_factors,
    ROUND(100.0 * COUNT(DISTINCT rf.resource_id) / COUNT(DISTINCT r.id), 2) AS residue_factor_coverage_pct
FROM resource r
LEFT JOIN residue_factor rf ON r.id = rf.resource_id
WHERE r.id IN (
    SELECT DISTINCT fs.resource_id FROM field_sample fs WHERE fs.resource_id IS NOT NULL
);

-- 8.3 Factor Types Distribution
\echo '--- 8.3 Factor Types Distribution ---'
SELECT
    factor_type,
    COUNT(*) AS record_count,
    COUNT(DISTINCT resource_id) AS unique_resources,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM residue_factor WHERE factor_type IS NOT NULL), 2) AS pct_of_factors
FROM residue_factor
WHERE factor_type IS NOT NULL
GROUP BY factor_type
ORDER BY record_count DESC;

-- 8.4 Resources in Lineage with Detailed Residue Factor Status
\echo '--- 8.4 Resources in Sample Lineage - Residue Factor Status ---'
SELECT
    r.id,
    r.name,
    COUNT(DISTINCT fs.id) AS field_samples_count,
    COUNT(DISTINCT rf.id) AS residue_factor_count,
    COALESCE(rf.factor_type, 'NO FACTOR') AS primary_factor_type,
    CASE WHEN rf.id IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_residue_factor
FROM resource r
LEFT JOIN field_sample fs ON r.id = fs.resource_id
LEFT JOIN residue_factor rf ON r.id = rf.resource_id
WHERE r.id IN (
    SELECT DISTINCT fs.resource_id FROM field_sample fs WHERE fs.resource_id IS NOT NULL
)
GROUP BY r.id, r.name, rf.factor_type, rf.id
ORDER BY field_samples_count DESC
LIMIT 50;
