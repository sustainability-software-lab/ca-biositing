"""Consolidated PR f989683 views with geoid grouping

Revision ID: 9e8f7a6b5c54
Revises: f98d1a9fe9a7
Create Date: 2026-04-07 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e8f7a6b5c54'
down_revision = 'f98d1a9fe9a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all 10 data portal materialized views with immutable SQL."""

    # Drop all indexes first
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_availability_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_composition_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_county_production_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_end_uses_resource_use_case CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_gasification_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_pricing_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_sample_stats_resource_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_usda_county_production_id CASCADE")

    # Drop all views CASCADE in case they exist from broken migrations
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_search CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_availability CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_composition CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_county_production CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_end_uses CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_fermentation CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_gasification CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_pricing CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_sample_stats CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_usda_county_production CASCADE")

    # ========================================================================
    # 1. mv_biomass_search
    # ========================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_search AS
        SELECT resource.id, resource.name, resource.resource_code, resource.description, resource_class.name AS resource_class, resource_subclass.name AS resource_subclass, primary_ag_product.name AS primary_product, resource_morphology.morphology_uri AS image_url, resource.uri AS literature_uri, anon_1.total_annual_volume, anon_1.county_count, anon_1.volume_unit, anon_2.moisture_percent, anon_2.sugar_content_percent, anon_2.ash_percent, anon_2.lignin_percent, anon_2.carbon_percent, anon_2.hydrogen_percent, anon_2.cn_ratio, anon_3.transport_notes, anon_4.storage_notes, coalesce(anon_5.tags, CAST(ARRAY[] AS VARCHAR[])) AS tags, anon_6.from_month AS season_from_month, anon_6.to_month AS season_to_month, anon_6.year_round, coalesce(anon_2.has_proximate, false) AS has_proximate, coalesce(anon_2.has_compositional, false) AS has_compositional, coalesce(anon_2.has_ultimate, false) AS has_ultimate, coalesce(anon_2.has_xrf, false) AS has_xrf, coalesce(anon_2.has_icp, false) AS has_icp, coalesce(anon_2.has_calorimetry, false) AS has_calorimetry, coalesce(anon_2.has_xrd, false) AS has_xrd, coalesce(anon_2.has_ftnir, false) AS has_ftnir, coalesce(anon_2.has_fermentation, false) AS has_fermentation, coalesce(anon_2.has_gasification, false) AS has_gasification, coalesce(anon_2.has_pretreatment, false) AS has_pretreatment, CASE WHEN (anon_2.moisture_percent IS NOT NULL) THEN true ELSE false END AS has_moisture_data, CASE WHEN (anon_2.sugar_content_percent > 0) THEN true ELSE false END AS has_sugar_data, CASE WHEN (resource_morphology.morphology_uri IS NOT NULL) THEN true ELSE false END AS has_image, CASE WHEN (anon_1.total_annual_volume IS NOT NULL) THEN true ELSE false END AS has_volume_data, resource.created_at, resource.updated_at, to_tsvector('english', coalesce(resource.name, '') || ' ' || coalesce(resource.description, '') || ' ' || coalesce(resource_class.name, '') || ' ' || coalesce(resource_subclass.name, '') || ' ' || coalesce(primary_ag_product.name, '')) AS search_vector
        FROM resource LEFT OUTER JOIN resource_class ON resource.resource_class_id = resource_class.id LEFT OUTER JOIN resource_subclass ON resource.resource_subclass_id = resource_subclass.id LEFT OUTER JOIN primary_ag_product ON resource.primary_ag_product_id = primary_ag_product.id LEFT OUTER JOIN resource_morphology ON resource_morphology.resource_id = resource.id LEFT OUTER JOIN (SELECT billion_ton2023_record.resource_id AS resource_id, sum(billion_ton2023_record.production) AS total_annual_volume, count(distinct(billion_ton2023_record.geoid)) AS county_count, max(unit.name) AS volume_unit
        FROM billion_ton2023_record JOIN unit ON billion_ton2023_record.production_unit_id = unit.id GROUP BY billion_ton2023_record.resource_id) AS anon_1 ON anon_1.resource_id = resource.id LEFT OUTER JOIN (SELECT anon_7.resource_id AS resource_id, avg(CASE WHEN (anon_8.parameter = 'moisture') THEN anon_8.value END) AS moisture_percent, avg(CASE WHEN (anon_8.parameter = 'ash') THEN anon_8.value END) AS ash_percent, CASE WHEN (avg(CASE WHEN (anon_8.parameter = 'lignin') THEN anon_8.value END) IS NOT NULL OR avg(CASE WHEN (anon_8.parameter = 'lignin+') THEN anon_8.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_8.parameter = 'lignin') THEN anon_8.value END), 0) + coalesce(avg(CASE WHEN (anon_8.parameter = 'lignin+') THEN anon_8.value END), 0) END AS lignin_percent, CASE WHEN (avg(CASE WHEN (anon_8.parameter = 'glucose') THEN anon_8.value END) IS NOT NULL OR avg(CASE WHEN (anon_8.parameter = 'xylose') THEN anon_8.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_8.parameter = 'glucose') THEN anon_8.value END), 0) + coalesce(avg(CASE WHEN (anon_8.parameter = 'xylose') THEN anon_8.value END), 0) END AS sugar_content_percent, avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) AS carbon_percent, avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'hydrogen') THEN anon_8.value END) AS hydrogen_percent, CASE WHEN (avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) IS NOT NULL AND avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) IS NOT NULL AND avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) != 0) THEN avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) / CAST(avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) AS NUMERIC) END AS cn_ratio, bool_or(anon_7.type = 'proximate analysis') AS has_proximate, bool_or(anon_7.type = 'compositional analysis') AS has_compositional, bool_or(anon_7.type = 'ultimate analysis') AS has_ultimate, bool_or(anon_7.type = 'xrf analysis') AS has_xrf, bool_or(anon_7.type = 'icp analysis') AS has_icp, bool_or(anon_7.type = 'calorimetry analysis') AS has_calorimetry, bool_or(anon_7.type = 'xrd analysis') AS has_xrd, bool_or(anon_7.type = 'ftnir analysis') AS has_ftnir, bool_or(anon_7.type = 'fermentation') AS has_fermentation, bool_or(anon_7.type = 'gasification') AS has_gasification, bool_or(anon_7.type = 'pretreatment') AS has_pretreatment
        FROM (SELECT compositional_record.resource_id AS resource_id, compositional_record.record_id AS record_id, 'compositional analysis' AS type
        FROM compositional_record UNION ALL SELECT proximate_record.resource_id AS resource_id, proximate_record.record_id AS record_id, 'proximate analysis' AS type
        FROM proximate_record UNION ALL SELECT ultimate_record.resource_id AS resource_id, ultimate_record.record_id AS record_id, 'ultimate analysis' AS type
        FROM ultimate_record UNION ALL SELECT xrf_record.resource_id AS resource_id, xrf_record.record_id AS record_id, 'xrf analysis' AS type
        FROM xrf_record UNION ALL SELECT icp_record.resource_id AS resource_id, icp_record.record_id AS record_id, 'icp analysis' AS type
        FROM icp_record UNION ALL SELECT calorimetry_record.resource_id AS resource_id, calorimetry_record.record_id AS record_id, 'calorimetry analysis' AS type
        FROM calorimetry_record UNION ALL SELECT xrd_record.resource_id AS resource_id, xrd_record.record_id AS record_id, 'xrd analysis' AS type
        FROM xrd_record UNION ALL SELECT ftnir_record.resource_id AS resource_id, ftnir_record.record_id AS record_id, 'ftnir analysis' AS type
        FROM ftnir_record UNION ALL SELECT fermentation_record.resource_id AS resource_id, fermentation_record.record_id AS record_id, 'fermentation' AS type
        FROM fermentation_record UNION ALL SELECT gasification_record.resource_id AS resource_id, gasification_record.record_id AS record_id, 'gasification' AS type
        FROM gasification_record UNION ALL SELECT pretreatment_record.resource_id AS resource_id, pretreatment_record.record_id AS record_id, 'pretreatment' AS type
        FROM pretreatment_record) AS anon_7 LEFT OUTER JOIN (SELECT observation.record_id AS record_id, observation.record_type AS record_type, parameter.name AS parameter, observation.value AS value
        FROM observation JOIN parameter ON observation.parameter_id = parameter.id) AS anon_8 ON lower(anon_7.record_id) = lower(anon_8.record_id) AND anon_8.record_type = anon_7.type GROUP BY anon_7.resource_id) AS anon_2 ON anon_2.resource_id = resource.id LEFT OUTER JOIN (SELECT anon_2.resource_id AS resource_id, array_remove(ARRAY[CASE WHEN (anon_2.moisture_percent <= anon_9.moisture_low) THEN 'low moisture' END, CASE WHEN (anon_2.moisture_percent >= anon_9.moisture_high) THEN 'high moisture' END, CASE WHEN (anon_2.ash_percent <= anon_9.ash_low) THEN 'low ash' END, CASE WHEN (anon_2.ash_percent >= anon_9.ash_high) THEN 'high ash' END, CASE WHEN (anon_2.lignin_percent <= anon_9.lignin_low) THEN 'low lignin' END, CASE WHEN (anon_2.lignin_percent >= anon_9.lignin_high) THEN 'high lignin' END, CASE WHEN (anon_2.sugar_content_percent <= anon_9.sugar_low) THEN 'low sugar' END, CASE WHEN (anon_2.sugar_content_percent >= anon_9.sugar_high) THEN 'high sugar' END], NULL) AS tags
        FROM (SELECT anon_7.resource_id AS resource_id, avg(CASE WHEN (anon_8.parameter = 'moisture') THEN anon_8.value END) AS moisture_percent, avg(CASE WHEN (anon_8.parameter = 'ash') THEN anon_8.value END) AS ash_percent, CASE WHEN (avg(CASE WHEN (anon_8.parameter = 'lignin') THEN anon_8.value END) IS NOT NULL OR avg(CASE WHEN (anon_8.parameter = 'lignin+') THEN anon_8.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_8.parameter = 'lignin') THEN anon_8.value END), 0) + coalesce(avg(CASE WHEN (anon_8.parameter = 'lignin+') THEN anon_8.value END), 0) END AS lignin_percent, CASE WHEN (avg(CASE WHEN (anon_8.parameter = 'glucose') THEN anon_8.value END) IS NOT NULL OR avg(CASE WHEN (anon_8.parameter = 'xylose') THEN anon_8.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_8.parameter = 'glucose') THEN anon_8.value END), 0) + coalesce(avg(CASE WHEN (anon_8.parameter = 'xylose') THEN anon_8.value END), 0) END AS sugar_content_percent, avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) AS carbon_percent, avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'hydrogen') THEN anon_8.value END) AS hydrogen_percent, CASE WHEN (avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) IS NOT NULL AND avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) IS NOT NULL AND avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) != 0) THEN avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) / CAST(avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) AS NUMERIC) END AS cn_ratio, bool_or(anon_7.type = 'proximate analysis') AS has_proximate, bool_or(anon_7.type = 'compositional analysis') AS has_compositional, bool_or(anon_7.type = 'ultimate analysis') AS has_ultimate, bool_or(anon_7.type = 'xrf analysis') AS has_xrf, bool_or(anon_7.type = 'icp analysis') AS has_icp, bool_or(anon_7.type = 'calorimetry analysis') AS has_calorimetry, bool_or(anon_7.type = 'xrd analysis') AS has_xrd, bool_or(anon_7.type = 'ftnir analysis') AS has_ftnir, bool_or(anon_7.type = 'fermentation') AS has_fermentation, bool_or(anon_7.type = 'gasification') AS has_gasification, bool_or(anon_7.type = 'pretreatment') AS has_pretreatment
        FROM (SELECT compositional_record.resource_id AS resource_id, compositional_record.record_id AS record_id, 'compositional analysis' AS type
        FROM compositional_record UNION ALL SELECT proximate_record.resource_id AS resource_id, proximate_record.record_id AS record_id, 'proximate analysis' AS type
        FROM proximate_record UNION ALL SELECT ultimate_record.resource_id AS resource_id, ultimate_record.record_id AS record_id, 'ultimate analysis' AS type
        FROM ultimate_record UNION ALL SELECT xrf_record.resource_id AS resource_id, xrf_record.record_id AS record_id, 'xrf analysis' AS type
        FROM xrf_record UNION ALL SELECT icp_record.resource_id AS resource_id, icp_record.record_id AS record_id, 'icp analysis' AS type
        FROM icp_record UNION ALL SELECT calorimetry_record.resource_id AS resource_id, calorimetry_record.record_id AS record_id, 'calorimetry analysis' AS type
        FROM calorimetry_record UNION ALL SELECT xrd_record.resource_id AS resource_id, xrd_record.record_id AS record_id, 'xrd analysis' AS type
        FROM xrd_record UNION ALL SELECT ftnir_record.resource_id AS resource_id, ftnir_record.record_id AS record_id, 'ftnir analysis' AS type
        FROM ftnir_record UNION ALL SELECT fermentation_record.resource_id AS resource_id, fermentation_record.record_id AS record_id, 'fermentation' AS type
        FROM fermentation_record UNION ALL SELECT gasification_record.resource_id AS resource_id, gasification_record.record_id AS record_id, 'gasification' AS type
        FROM gasification_record UNION ALL SELECT pretreatment_record.resource_id AS resource_id, pretreatment_record.record_id AS record_id, 'pretreatment' AS type
        FROM pretreatment_record) AS anon_7 LEFT OUTER JOIN (SELECT observation.record_id AS record_id, observation.record_type AS record_type, parameter.name AS parameter, observation.value AS value
        FROM observation JOIN parameter ON observation.parameter_id = parameter.id) AS anon_8 ON lower(anon_7.record_id) = lower(anon_8.record_id) AND anon_8.record_type = anon_7.type GROUP BY anon_7.resource_id) AS anon_2 JOIN (SELECT percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_2.moisture_percent) AS moisture_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_2.moisture_percent) AS moisture_high, percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_2.ash_percent) AS ash_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_2.ash_percent) AS ash_high, percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_2.lignin_percent) AS lignin_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_2.lignin_percent) AS lignin_high, percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_2.sugar_content_percent) AS sugar_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_2.sugar_content_percent) AS sugar_high
        FROM (SELECT anon_7.resource_id AS resource_id, avg(CASE WHEN (anon_8.parameter = 'moisture') THEN anon_8.value END) AS moisture_percent, avg(CASE WHEN (anon_8.parameter = 'ash') THEN anon_8.value END) AS ash_percent, CASE WHEN (avg(CASE WHEN (anon_8.parameter = 'lignin') THEN anon_8.value END) IS NOT NULL OR avg(CASE WHEN (anon_8.parameter = 'lignin+') THEN anon_8.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_8.parameter = 'lignin') THEN anon_8.value END), 0) + coalesce(avg(CASE WHEN (anon_8.parameter = 'lignin+') THEN anon_8.value END), 0) END AS lignin_percent, CASE WHEN (avg(CASE WHEN (anon_8.parameter = 'glucose') THEN anon_8.value END) IS NOT NULL OR avg(CASE WHEN (anon_8.parameter = 'xylose') THEN anon_8.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_8.parameter = 'glucose') THEN anon_8.value END), 0) + coalesce(avg(CASE WHEN (anon_8.parameter = 'xylose') THEN anon_8.value END), 0) END AS sugar_content_percent, avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) AS carbon_percent, avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'hydrogen') THEN anon_8.value END) AS hydrogen_percent, CASE WHEN (avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) IS NOT NULL AND avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) IS NOT NULL AND avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) != 0) THEN avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'carbon') THEN anon_8.value END) / CAST(avg(CASE WHEN (anon_7.type = 'ultimate analysis' AND lower(anon_8.parameter) = 'nitrogen') THEN anon_8.value END) AS NUMERIC) END AS cn_ratio, bool_or(anon_7.type = 'proximate analysis') AS has_proximate, bool_or(anon_7.type = 'compositional analysis') AS has_compositional, bool_or(anon_7.type = 'ultimate analysis') AS has_ultimate, bool_or(anon_7.type = 'xrf analysis') AS has_xrf, bool_or(anon_7.type = 'icp analysis') AS has_icp, bool_or(anon_7.type = 'calorimetry analysis') AS has_calorimetry, bool_or(anon_7.type = 'xrd analysis') AS has_xrd, bool_or(anon_7.type = 'ftnir analysis') AS has_ftnir, bool_or(anon_7.type = 'fermentation') AS has_fermentation, bool_or(anon_7.type = 'gasification') AS has_gasification, bool_or(anon_7.type = 'pretreatment') AS has_pretreatment
        FROM (SELECT compositional_record.resource_id AS resource_id, compositional_record.record_id AS record_id, 'compositional analysis' AS type
        FROM compositional_record UNION ALL SELECT proximate_record.resource_id AS resource_id, proximate_record.record_id AS record_id, 'proximate analysis' AS type
        FROM proximate_record UNION ALL SELECT ultimate_record.resource_id AS resource_id, ultimate_record.record_id AS record_id, 'ultimate analysis' AS type
        FROM ultimate_record UNION ALL SELECT xrf_record.resource_id AS resource_id, xrf_record.record_id AS record_id, 'xrf analysis' AS type
        FROM xrf_record UNION ALL SELECT icp_record.resource_id AS resource_id, icp_record.record_id AS record_id, 'icp analysis' AS type
        FROM icp_record UNION ALL SELECT calorimetry_record.resource_id AS resource_id, calorimetry_record.record_id AS record_id, 'calorimetry analysis' AS type
        FROM calorimetry_record UNION ALL SELECT xrd_record.resource_id AS resource_id, xrd_record.record_id AS record_id, 'xrd analysis' AS type
        FROM xrd_record UNION ALL SELECT ftnir_record.resource_id AS resource_id, ftnir_record.record_id AS record_id, 'ftnir analysis' AS type
        FROM ftnir_record UNION ALL SELECT fermentation_record.resource_id AS resource_id, fermentation_record.record_id AS record_id, 'fermentation' AS type
        FROM fermentation_record UNION ALL SELECT gasification_record.resource_id AS resource_id, gasification_record.record_id AS record_id, 'gasification' AS type
        FROM gasification_record UNION ALL SELECT pretreatment_record.resource_id AS resource_id, pretreatment_record.record_id AS record_id, 'pretreatment' AS type
        FROM pretreatment_record) AS anon_7 LEFT OUTER JOIN (SELECT observation.record_id AS record_id, observation.record_type AS record_type, parameter.name AS parameter, observation.value AS value
        FROM observation JOIN parameter ON observation.parameter_id = parameter.id) AS anon_8 ON lower(anon_7.record_id) = lower(anon_8.record_id) AND anon_8.record_type = anon_7.type GROUP BY anon_7.resource_id) AS anon_2) AS anon_9 ON true) AS anon_5 ON anon_5.resource_id = resource.id LEFT OUTER JOIN (SELECT resource.id AS resource_id, resource.name AS resource_name, min(resource_availability.from_month) AS from_month, max(resource_availability.to_month) AS to_month, bool_or(resource_availability.year_round) AS year_round, avg(resource_availability.residue_factor_dry_tons_acre) AS dry_tons_per_acre, avg(resource_availability.residue_factor_wet_tons_acre) AS wet_tons_per_acre
        FROM resource_availability JOIN resource ON resource_availability.resource_id = resource.id GROUP BY resource.id, resource.name) AS anon_6 ON anon_6.resource_id = resource.id LEFT OUTER JOIN (SELECT resource_transport_record.resource_id AS resource_id, max(resource_transport_record.transport_description) AS transport_notes
        FROM resource_transport_record GROUP BY resource_transport_record.resource_id) AS anon_3 ON anon_3.resource_id = resource.id LEFT OUTER JOIN (SELECT resource_storage_record.resource_id AS resource_id, max(resource_storage_record.storage_description) AS storage_notes
        FROM resource_storage_record GROUP BY resource_storage_record.resource_id) AS anon_4 ON anon_4.resource_id = resource.id
        WHERE lower(resource.name) != 'sargassum'
    """)

    # ========================================================================
    # 2. mv_biomass_availability
    # ========================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_availability AS
        SELECT resource.id AS resource_id, resource.name AS resource_name, min(resource_availability.from_month) AS from_month, max(resource_availability.to_month) AS to_month, bool_or(resource_availability.year_round) AS year_round, avg(resource_availability.residue_factor_dry_tons_acre) AS dry_tons_per_acre, avg(resource_availability.residue_factor_wet_tons_acre) AS wet_tons_per_acre
        FROM resource_availability JOIN resource ON resource_availability.resource_id = resource.id GROUP BY resource.id, resource.name
    """)


    # ========================================================================
    # 3. mv_biomass_composition
    # ========================================================================
    # QC Filter: qc_pass != 'fail' - excludes only records marked as failed
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_composition AS
        SELECT row_number() OVER (ORDER BY anon_1.resource_id, anon_1.geoid, anon_1.analysis_type, anon_1.parameter_name, anon_1.unit) AS id, anon_1.resource_id, resource.name AS resource_name, anon_1.analysis_type, anon_1.parameter_name, anon_1.geoid, place.county_name AS county, anon_1.unit, avg(anon_1.value) AS avg_value, min(anon_1.value) AS min_value, max(anon_1.value) AS max_value, stddev(anon_1.value) AS std_dev, count(*) AS observation_count
        FROM (SELECT compositional_record.resource_id AS resource_id, 'compositional' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM compositional_record JOIN observation ON observation.record_id = compositional_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON compositional_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE compositional_record.qc_pass != 'fail' UNION ALL SELECT proximate_record.resource_id AS resource_id, 'proximate' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM proximate_record JOIN observation ON observation.record_id = proximate_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON proximate_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE proximate_record.qc_pass != 'fail' UNION ALL SELECT ultimate_record.resource_id AS resource_id, 'ultimate' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM ultimate_record JOIN observation ON observation.record_id = ultimate_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON ultimate_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE ultimate_record.qc_pass != 'fail' UNION ALL SELECT xrf_record.resource_id AS resource_id, 'xrf' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM xrf_record JOIN observation ON observation.record_id = xrf_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON xrf_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE xrf_record.qc_pass != 'fail' UNION ALL SELECT icp_record.resource_id AS resource_id, 'icp' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM icp_record JOIN observation ON observation.record_id = icp_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON icp_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE icp_record.qc_pass != 'fail' UNION ALL SELECT calorimetry_record.resource_id AS resource_id, 'calorimetry' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM calorimetry_record JOIN observation ON observation.record_id = calorimetry_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON calorimetry_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE calorimetry_record.qc_pass != 'fail' UNION ALL SELECT xrd_record.resource_id AS resource_id, 'xrd' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM xrd_record JOIN observation ON observation.record_id = xrd_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON xrd_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE xrd_record.qc_pass != 'fail' UNION ALL SELECT ftnir_record.resource_id AS resource_id, 'ftnir' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM ftnir_record JOIN observation ON observation.record_id = ftnir_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON ftnir_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE ftnir_record.qc_pass != 'fail' UNION ALL SELECT pretreatment_record.resource_id AS resource_id, 'pretreatment' AS analysis_type, parameter.name AS parameter_name, observation.value AS value, unit.name AS unit, location_address.geography_id AS geoid
        FROM pretreatment_record JOIN observation ON observation.record_id = pretreatment_record.record_id JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id LEFT OUTER JOIN prepared_sample ON pretreatment_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
        WHERE pretreatment_record.qc_pass != 'fail') AS anon_1 JOIN resource ON anon_1.resource_id = resource.id LEFT OUTER JOIN place ON anon_1.geoid = place.geoid GROUP BY anon_1.resource_id, resource.name, anon_1.analysis_type, anon_1.parameter_name, anon_1.geoid, place.county_name, anon_1.unit
    """)

    # ========================================================================
    # 4. mv_biomass_county_production
    # ========================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_county_production AS
        SELECT row_number() OVER (ORDER BY billion_ton2023_record.resource_id, place.geoid, billion_ton2023_record.scenario_name, billion_ton2023_record.price_offered_usd) AS id, billion_ton2023_record.resource_id, resource.name AS resource_name, resource_class.name AS resource_class, place.geoid, place.county_name AS county, place.state_name AS state, billion_ton2023_record.scenario_name AS scenario, billion_ton2023_record.price_offered_usd, billion_ton2023_record.production, unit.name AS production_unit, billion_ton2023_record.production_energy_content AS energy_content, eu.name AS energy_unit, billion_ton2023_record.product_density_dtpersqmi AS density_dt_per_sqmi, billion_ton2023_record.county_square_miles, 2023 AS year
        FROM billion_ton2023_record JOIN resource ON billion_ton2023_record.resource_id = resource.id LEFT OUTER JOIN resource_class ON resource.resource_class_id = resource_class.id JOIN place ON billion_ton2023_record.geoid = place.geoid LEFT OUTER JOIN unit ON billion_ton2023_record.production_unit_id = unit.id LEFT OUTER JOIN unit AS eu ON billion_ton2023_record.energy_content_unit_id = eu.id
    """)

    # ========================================================================
    # 5. mv_biomass_end_uses
    # ========================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_end_uses AS
        SELECT resource_end_use_record.resource_id, resource.name AS resource_name, coalesce(method.name, 'unknown') AS use_case, CAST(anon_1.percent_of_volume AS FLOAT) AS percentage_low, CAST(NULL AS FLOAT) AS percentage_high, CAST(anon_1.trending AS TEXT) AS trend, CAST(NULL AS FLOAT) AS value_low_usd, CAST(NULL AS FLOAT) AS value_high_usd, CAST(NULL AS TEXT) AS value_notes
        FROM resource_end_use_record JOIN resource ON resource_end_use_record.resource_id = resource.id LEFT OUTER JOIN method ON resource_end_use_record.method_id = method.id LEFT OUTER JOIN (SELECT observation.record_id AS record_id, avg(CASE WHEN (lower(parameter.name) IN ('percent of volume', 'percent_of_volume', 'percentage of volume', 'volume percent')) THEN observation.value END) AS percent_of_volume, max(CASE WHEN (lower(parameter.name) IN ('percent of volume', 'percent_of_volume', 'percentage of volume', 'volume percent')) THEN unit.name END) AS unit, max(CASE WHEN (lower(parameter.name) = 'trending') THEN CAST(observation.value AS VARCHAR) END) AS trending
        FROM observation JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE lower(observation.record_type) = 'resource_end_use_record' GROUP BY observation.record_id) AS anon_1 ON CAST(resource_end_use_record.id AS VARCHAR) = anon_1.record_id
        WHERE resource_end_use_record.resource_id IS NOT NULL GROUP BY resource_end_use_record.resource_id, resource.name, coalesce(method.name, 'unknown'), anon_1.percent_of_volume, anon_1.trending
    """)

    # ========================================================================
    # 6. mv_biomass_fermentation
    # ========================================================================
    # QC Filter: qc_pass != 'fail' - excludes only records marked as failed
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_fermentation AS
        SELECT row_number() OVER (ORDER BY fermentation_record.resource_id, location_address.geography_id, strain.name, pm.name, em.name, parameter.name, unit.name) AS id, fermentation_record.resource_id, resource.name AS resource_name, location_address.geography_id AS geoid, place.county_name AS county, strain.name AS strain_name, pm.name AS pretreatment_method, em.name AS enzyme_name, parameter.name AS product_name, avg(observation.value) AS avg_value, min(observation.value) AS min_value, max(observation.value) AS max_value, stddev(observation.value) AS std_dev, count(*) AS observation_count, unit.name AS unit
        FROM fermentation_record JOIN resource ON fermentation_record.resource_id = resource.id LEFT OUTER JOIN prepared_sample ON fermentation_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id LEFT OUTER JOIN place ON location_address.geography_id = place.geoid LEFT OUTER JOIN strain ON fermentation_record.strain_id = strain.id LEFT OUTER JOIN method AS pm ON fermentation_record.pretreatment_method_id = pm.id LEFT OUTER JOIN method AS em ON fermentation_record.eh_method_id = em.id JOIN observation ON lower(observation.record_id) = lower(fermentation_record.record_id) JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE fermentation_record.qc_pass != 'fail' GROUP BY fermentation_record.resource_id, resource.name, location_address.geography_id, place.county_name, strain.name, pm.name, em.name, parameter.name, unit.name
    """)

    # ========================================================================
    # 7. mv_biomass_gasification
    # ========================================================================
    # QC Filter: qc_pass != 'fail' - excludes only records marked as failed
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_gasification AS
        SELECT row_number() OVER (ORDER BY gasification_record.resource_id, location_address.geography_id, decon_vessel.name, parameter.name, unit.name) AS id, gasification_record.resource_id, resource.name AS resource_name, decon_vessel.name AS reactor_type, parameter.name AS parameter_name, location_address.geography_id AS geoid, avg(observation.value) AS avg_value, min(observation.value) AS min_value, max(observation.value) AS max_value, stddev(observation.value) AS std_dev, count(*) AS observation_count, unit.name AS unit
        FROM gasification_record JOIN resource ON gasification_record.resource_id = resource.id LEFT OUTER JOIN prepared_sample ON gasification_record.prepared_sample_id = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id LEFT OUTER JOIN decon_vessel ON gasification_record.reactor_type_id = decon_vessel.id JOIN observation ON lower(observation.record_id) = lower(gasification_record.record_id) JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE gasification_record.qc_pass != 'fail' GROUP BY gasification_record.resource_id, resource.name, location_address.geography_id, decon_vessel.name, parameter.name, unit.name
    """)

    # ========================================================================
    # 8. mv_biomass_pricing
    # ========================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_pricing AS
        SELECT row_number() OVER (ORDER BY usda_market_record.id) AS id, usda_commodity.name AS commodity_name, place.geoid, place.county_name AS county, place.state_name AS state, usda_market_record.report_date, usda_market_record.market_type_category, usda_market_record.sale_type, anon_1.price_min, anon_1.price_max, anon_1.price_avg, anon_1.price_unit
        FROM usda_market_record JOIN usda_market_report ON usda_market_record.report_id = usda_market_report.id JOIN usda_commodity ON usda_market_record.commodity_id = usda_commodity.id LEFT OUTER JOIN location_address ON usda_market_report.office_city_id = location_address.id LEFT OUTER JOIN place ON location_address.geography_id = place.geoid JOIN (SELECT observation.record_id AS record_id, avg(observation.value) AS price_avg, min(observation.value) AS price_min, max(observation.value) AS price_max, unit.name AS price_unit
        FROM observation JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE observation.record_type = 'usda_market_record' AND lower(parameter.name) = 'price received' GROUP BY observation.record_id, unit.name) AS anon_1 ON CAST(usda_market_record.id AS VARCHAR) = anon_1.record_id
    """)

    # ========================================================================
    # 9. mv_biomass_sample_stats
    # ========================================================================
    # QC Filter: qc_pass != 'fail' - excludes only records marked as failed
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_biomass_sample_stats AS
        SELECT resource.id AS resource_id, resource.name AS resource_name, count(distinct(anon_1.prepared_sample_id)) AS sample_count, count(distinct(provider.id)) AS supplier_count, count(distinct(anon_1.dataset_id)) AS dataset_count, count(*) AS total_record_count
        FROM resource LEFT OUTER JOIN (SELECT compositional_record.resource_id AS resource_id, compositional_record.prepared_sample_id AS prepared_sample_id, compositional_record.dataset_id AS dataset_id
        FROM compositional_record
        WHERE compositional_record.qc_pass != 'fail' UNION ALL SELECT proximate_record.resource_id AS resource_id, proximate_record.prepared_sample_id AS prepared_sample_id, proximate_record.dataset_id AS dataset_id
        FROM proximate_record
        WHERE proximate_record.qc_pass != 'fail' UNION ALL SELECT ultimate_record.resource_id AS resource_id, ultimate_record.prepared_sample_id AS prepared_sample_id, ultimate_record.dataset_id AS dataset_id
        FROM ultimate_record
        WHERE ultimate_record.qc_pass != 'fail' UNION ALL SELECT xrf_record.resource_id AS resource_id, xrf_record.prepared_sample_id AS prepared_sample_id, xrf_record.dataset_id AS dataset_id
        FROM xrf_record
        WHERE xrf_record.qc_pass != 'fail' UNION ALL SELECT icp_record.resource_id AS resource_id, icp_record.prepared_sample_id AS prepared_sample_id, icp_record.dataset_id AS dataset_id
        FROM icp_record
        WHERE icp_record.qc_pass != 'fail' UNION ALL SELECT calorimetry_record.resource_id AS resource_id, calorimetry_record.prepared_sample_id AS prepared_sample_id, calorimetry_record.dataset_id AS dataset_id
        FROM calorimetry_record
        WHERE calorimetry_record.qc_pass != 'fail' UNION ALL SELECT xrd_record.resource_id AS resource_id, xrd_record.prepared_sample_id AS prepared_sample_id, xrd_record.dataset_id AS dataset_id
        FROM xrd_record
        WHERE xrd_record.qc_pass != 'fail' UNION ALL SELECT ftnir_record.resource_id AS resource_id, ftnir_record.prepared_sample_id AS prepared_sample_id, ftnir_record.dataset_id AS dataset_id
        FROM ftnir_record
        WHERE ftnir_record.qc_pass != 'fail' UNION ALL SELECT fermentation_record.resource_id AS resource_id, fermentation_record.prepared_sample_id AS prepared_sample_id, fermentation_record.dataset_id AS dataset_id
        FROM fermentation_record
        WHERE fermentation_record.qc_pass != 'fail' UNION ALL SELECT gasification_record.resource_id AS resource_id, gasification_record.prepared_sample_id AS prepared_sample_id, gasification_record.dataset_id AS dataset_id
        FROM gasification_record
        WHERE gasification_record.qc_pass != 'fail' UNION ALL SELECT pretreatment_record.resource_id AS resource_id, pretreatment_record.prepared_sample_id AS prepared_sample_id, pretreatment_record.dataset_id AS dataset_id
        FROM pretreatment_record
        WHERE pretreatment_record.qc_pass != 'fail') AS anon_1 ON anon_1.resource_id = resource.id LEFT OUTER JOIN prepared_sample ON CAST(anon_1.prepared_sample_id AS INTEGER) = prepared_sample.id LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id LEFT OUTER JOIN provider ON field_sample.provider_id = provider.id GROUP BY resource.id, resource.name
    """)

    # ========================================================================
    # 10. mv_usda_county_production
    # ========================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW data_portal.mv_usda_county_production AS
        SELECT row_number() OVER (ORDER BY resource.id, place.geoid, usda_census_record.year) AS id, resource.id AS resource_id, resource.name AS resource_name, primary_ag_product.name AS primary_ag_product, place.geoid, place.county_name AS county, place.state_name AS state, usda_census_record.year AS dataset_year, avg(anon_1.primary_product_volume) AS primary_product_volume, max(anon_1.volume_unit) AS volume_unit, avg(anon_1.production_acres) AS production_acres, NULL AS known_biomass_volume, avg(anon_1.production_acres) * coalesce(max(CASE WHEN (anon_2.geoid = place.geoid) THEN anon_2.residue_factor_dry_tons_acre END), max(CASE WHEN (anon_2.geoid = '06000') THEN anon_2.residue_factor_dry_tons_acre END)) AS calculated_estimate_volume, 'dry_tons_acre' AS biomass_unit
        FROM usda_census_record JOIN resource_usda_commodity_map ON usda_census_record.commodity_code = resource_usda_commodity_map.usda_commodity_id JOIN resource ON resource_usda_commodity_map.resource_id = resource.id JOIN primary_ag_product ON resource.primary_ag_product_id = primary_ag_product.id JOIN place ON usda_census_record.geoid = place.geoid JOIN (SELECT observation.record_id AS record_id, avg(CASE WHEN (lower(parameter.name) = 'production') THEN observation.value END) AS primary_product_volume, max(CASE WHEN (lower(parameter.name) = 'production') THEN unit.name END) AS volume_unit, avg(CASE WHEN (lower(parameter.name) IN ('area bearing', 'area harvested', 'area in production') AND lower(unit.name) = 'acres') THEN observation.value END) AS production_acres
        FROM observation JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id
        WHERE observation.record_type = 'usda_census_record' GROUP BY observation.record_id) AS anon_1 ON CAST(usda_census_record.id AS VARCHAR) = anon_1.record_id LEFT OUTER JOIN (SELECT resource_availability.resource_id AS resource_id, resource_availability.geoid AS geoid, resource_availability.residue_factor_dry_tons_acre AS residue_factor_dry_tons_acre
        FROM resource_availability) AS anon_2 ON resource.id = anon_2.resource_id
        WHERE usda_census_record.year >= 2017 GROUP BY resource.id, resource.name, primary_ag_product.name, place.geoid, place.county_name, place.state_name, usda_census_record.year
    """)

    # Grant schema access to readonly role
    op.execute("GRANT USAGE ON SCHEMA data_portal TO biocirv_readonly")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA data_portal TO biocirv_readonly")


def downgrade() -> None:
    """Drop all recreated views."""
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_search CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_availability CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_composition CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_county_production CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_end_uses CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_fermentation CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_gasification CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_pricing CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_sample_stats CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_usda_county_production CASCADE")
