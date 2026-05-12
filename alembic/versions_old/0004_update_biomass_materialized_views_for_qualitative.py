"""Update biomass materialized views for qualitative end-use changes.

Revision ID: d2b6b2a7c9d1
Revises: 1bed1a9104a7
Create Date: 2026-04-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2b6b2a7c9d1"
down_revision: Union[str, Sequence[str], None] = "1bed1a9104a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MV_BIOMASS_END_USES_SQL = """
SELECT resource_end_use_record.resource_id, resource.name AS resource_name, coalesce(use_case.name, 'unknown') AS use_case, CAST(avg(anon_1.percentage_low) AS FLOAT) AS percentage_low, CAST(avg(anon_1.percentage_high) AS FLOAT) AS percentage_high, CAST(max(anon_1.trend) AS TEXT) AS trend, CAST(avg(anon_1.value_low_usd) AS FLOAT) AS value_low_usd, CAST(avg(anon_1.value_high_usd) AS FLOAT) AS value_high_usd, CAST(max(anon_1.value_unit) AS TEXT) AS value_notes
FROM resource_end_use_record JOIN resource ON resource_end_use_record.resource_id = resource.id LEFT OUTER JOIN use_case ON resource_end_use_record.use_case_id = use_case.id LEFT OUTER JOIN (SELECT observation.record_id AS record_id, avg(CASE WHEN (lower(parameter.name) = 'resource_use_perc_low') THEN observation.value END) AS percentage_low, avg(CASE WHEN (lower(parameter.name) = 'resource_use_perc_high') THEN observation.value END) AS percentage_high, avg(CASE WHEN (lower(parameter.name) = 'resource_value_low') THEN observation.value END) AS value_low_usd, avg(CASE WHEN (lower(parameter.name) = 'resource_value_high') THEN observation.value END) AS value_high_usd, max(CASE WHEN (lower(parameter.name) = 'resource_use_perc_low') THEN unit.name END) AS unit, max(CASE WHEN (lower(parameter.name) = 'resource_use_trend') THEN CAST(observation.note AS VARCHAR) END) AS trend, max(CASE WHEN (lower(parameter.name) IN ('resource_value_low', 'resource_value_high')) THEN unit.name END) AS value_unit
FROM observation JOIN parameter ON observation.parameter_id = parameter.id LEFT OUTER JOIN unit ON observation.unit_id = unit.id
WHERE lower(observation.record_type) = 'resource_end_use_record' GROUP BY observation.record_id) AS anon_1 ON CAST(resource_end_use_record.id AS VARCHAR) = anon_1.record_id
WHERE resource_end_use_record.resource_id IS NOT NULL GROUP BY resource_end_use_record.resource_id, resource.name, coalesce(use_case.name, 'unknown')
"""


MV_BIOMASS_SEARCH_SQL = """
SELECT resource.id, resource.name, resource.resource_code, resource.description, resource_class.name AS resource_class, resource_subclass.name AS resource_subclass, coalesce(primary_ag_product.name, anon_1.primary_product_fallback) AS primary_product, resource_morphology.morphology_uri AS image_url, resource.uri AS literature_uri, anon_2.total_annual_volume, anon_2.county_count, anon_2.volume_unit, anon_3.moisture_percent, anon_3.sugar_content_percent, anon_3.ash_percent, anon_3.lignin_percent, anon_3.carbon_percent, anon_3.hydrogen_percent, anon_3.cn_ratio, CAST(anon_4.transport_notes AS TEXT) AS transport_description, CAST(anon_5.storage_notes AS TEXT) AS storage_description, anon_4.transport_notes, anon_5.storage_notes, coalesce(anon_6.tags, CAST(ARRAY[] AS VARCHAR[])) AS tags, anon_7.from_month AS season_from_month, anon_7.to_month AS season_to_month, anon_7.year_round, coalesce(anon_3.has_proximate, false) AS has_proximate, coalesce(anon_3.has_compositional, false) AS has_compositional, coalesce(anon_3.has_ultimate, false) AS has_ultimate, coalesce(anon_3.has_xrf, false) AS has_xrf, coalesce(anon_3.has_icp, false) AS has_icp, coalesce(anon_3.has_calorimetry, false) AS has_calorimetry, coalesce(anon_3.has_xrd, false) AS has_xrd, coalesce(anon_3.has_ftnir, false) AS has_ftnir, coalesce(anon_3.has_fermentation, false) AS has_fermentation, coalesce(anon_3.has_gasification, false) AS has_gasification, coalesce(anon_3.has_pretreatment, false) AS has_pretreatment, CASE WHEN (anon_3.moisture_percent IS NOT NULL) THEN true ELSE false END AS has_moisture_data, CASE WHEN (anon_3.sugar_content_percent > 0) THEN true ELSE false END AS has_sugar_data, CASE WHEN (resource_morphology.morphology_uri IS NOT NULL) THEN true ELSE false END AS has_image, CASE WHEN (anon_2.total_annual_volume IS NOT NULL) THEN true ELSE false END AS has_volume_data, resource.created_at, resource.updated_at, to_tsvector('english', coalesce(resource.name, '') || ' ' || coalesce(resource.description, '') || ' ' || coalesce(resource_class.name, '') || ' ' || coalesce(resource_subclass.name, '') || ' ' || coalesce(primary_ag_product.name, anon_1.primary_product_fallback, '')) AS search_vector
FROM resource LEFT OUTER JOIN resource_class ON resource.resource_class_id = resource_class.id LEFT OUTER JOIN resource_subclass ON resource.resource_subclass_id = resource_subclass.id LEFT OUTER JOIN primary_ag_product ON resource.primary_ag_product_id = primary_ag_product.id LEFT OUTER JOIN resource_morphology ON resource_morphology.resource_id = resource.id LEFT OUTER JOIN (SELECT billion_ton2023_record.resource_id AS resource_id, sum(billion_ton2023_record.production) AS total_annual_volume, count(distinct(billion_ton2023_record.geoid)) AS county_count, max(unit.name) AS volume_unit
FROM billion_ton2023_record JOIN unit ON billion_ton2023_record.production_unit_id = unit.id GROUP BY billion_ton2023_record.resource_id) AS anon_2 ON anon_2.resource_id = resource.id LEFT OUTER JOIN (SELECT anon_8.resource_id AS resource_id, avg(CASE WHEN (anon_9.parameter = 'moisture') THEN anon_9.value END) AS moisture_percent, avg(CASE WHEN (anon_9.parameter = 'ash') THEN anon_9.value END) AS ash_percent, CASE WHEN (avg(CASE WHEN (anon_9.parameter = 'lignin') THEN anon_9.value END) IS NOT NULL OR avg(CASE WHEN (anon_9.parameter = 'lignin+') THEN anon_9.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_9.parameter = 'lignin') THEN anon_9.value END), 0) + coalesce(avg(CASE WHEN (anon_9.parameter = 'lignin+') THEN anon_9.value END), 0) END AS lignin_percent, CASE WHEN (avg(CASE WHEN (anon_9.parameter = 'glucose') THEN anon_9.value END) IS NOT NULL OR avg(CASE WHEN (anon_9.parameter = 'xylose') THEN anon_9.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_9.parameter = 'glucose') THEN anon_9.value END), 0) + coalesce(avg(CASE WHEN (anon_9.parameter = 'xylose') THEN anon_9.value END), 0) END AS sugar_content_percent, avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) AS carbon_percent, avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'hydrogen') THEN anon_9.value END) AS hydrogen_percent, CASE WHEN (avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) IS NOT NULL AND avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) IS NOT NULL AND avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) != 0) THEN avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) / CAST(avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) AS NUMERIC) END AS cn_ratio, bool_or(anon_8.type = 'proximate analysis') AS has_proximate, bool_or(anon_8.type = 'compositional analysis') AS has_compositional, bool_or(anon_8.type = 'ultimate analysis') AS has_ultimate, bool_or(anon_8.type = 'xrf analysis') AS has_xrf, bool_or(anon_8.type = 'icp analysis') AS has_icp, bool_or(anon_8.type = 'calorimetry analysis') AS has_calorimetry, bool_or(anon_8.type = 'xrd analysis') AS has_xrd, bool_or(anon_8.type = 'ftnir analysis') AS has_ftnir, bool_or(anon_8.type = 'fermentation') AS has_fermentation, bool_or(anon_8.type = 'gasification') AS has_gasification, bool_or(anon_8.type = 'pretreatment') AS has_pretreatment
FROM (SELECT compositional_record.resource_id AS resource_id, compositional_record.record_id AS record_id, 'compositional analysis' AS type
FROM compositional_record
WHERE compositional_record.qc_pass != 'fail' UNION ALL SELECT proximate_record.resource_id AS resource_id, proximate_record.record_id AS record_id, 'proximate analysis' AS type
FROM proximate_record
WHERE proximate_record.qc_pass != 'fail' UNION ALL SELECT ultimate_record.resource_id AS resource_id, ultimate_record.record_id AS record_id, 'ultimate analysis' AS type
FROM ultimate_record
WHERE ultimate_record.qc_pass != 'fail' UNION ALL SELECT xrf_record.resource_id AS resource_id, xrf_record.record_id AS record_id, 'xrf analysis' AS type
FROM xrf_record
WHERE xrf_record.qc_pass != 'fail' UNION ALL SELECT icp_record.resource_id AS resource_id, icp_record.record_id AS record_id, 'icp analysis' AS type
FROM icp_record
WHERE icp_record.qc_pass != 'fail' UNION ALL SELECT calorimetry_record.resource_id AS resource_id, calorimetry_record.record_id AS record_id, 'calorimetry analysis' AS type
FROM calorimetry_record
WHERE calorimetry_record.qc_pass != 'fail' UNION ALL SELECT xrd_record.resource_id AS resource_id, xrd_record.record_id AS record_id, 'xrd analysis' AS type
FROM xrd_record
WHERE xrd_record.qc_pass != 'fail' UNION ALL SELECT ftnir_record.resource_id AS resource_id, ftnir_record.record_id AS record_id, 'ftnir analysis' AS type
FROM ftnir_record
WHERE ftnir_record.qc_pass != 'fail' UNION ALL SELECT fermentation_record.resource_id AS resource_id, fermentation_record.record_id AS record_id, 'fermentation' AS type
FROM fermentation_record
WHERE fermentation_record.qc_pass != 'fail' UNION ALL SELECT gasification_record.resource_id AS resource_id, gasification_record.record_id AS record_id, 'gasification' AS type
FROM gasification_record
WHERE gasification_record.qc_pass != 'fail' UNION ALL SELECT pretreatment_record.resource_id AS resource_id, pretreatment_record.record_id AS record_id, 'pretreatment' AS type
FROM pretreatment_record
WHERE pretreatment_record.qc_pass != 'fail') AS anon_8 LEFT OUTER JOIN (SELECT observation.record_id AS record_id, observation.record_type AS record_type, parameter.name AS parameter, observation.value AS value
FROM observation JOIN parameter ON observation.parameter_id = parameter.id
WHERE observation.record_type IN ('compositional analysis', 'proximate analysis', 'ultimate analysis', 'xrf analysis', 'icp analysis', 'calorimetry analysis', 'xrd analysis', 'ftnir analysis', 'pretreatment', 'gasification', 'fermentation')) AS anon_9 ON lower(anon_8.record_id) = lower(anon_9.record_id) AND anon_9.record_type = anon_8.type GROUP BY anon_8.resource_id) AS anon_3 ON anon_3.resource_id = resource.id LEFT OUTER JOIN (SELECT anon_3.resource_id AS resource_id, array_remove(ARRAY[CASE WHEN (anon_3.moisture_percent <= anon_10.moisture_low) THEN 'low moisture' END, CASE WHEN (anon_3.moisture_percent >= anon_10.moisture_high) THEN 'high moisture' END, CASE WHEN (anon_3.ash_percent <= anon_10.ash_low) THEN 'low ash' END, CASE WHEN (anon_3.ash_percent >= anon_10.ash_high) THEN 'high ash' END, CASE WHEN (anon_3.lignin_percent <= anon_10.lignin_low) THEN 'low lignin' END, CASE WHEN (anon_3.lignin_percent >= anon_10.lignin_high) THEN 'high lignin' END, CASE WHEN (anon_3.sugar_content_percent <= anon_10.sugar_low) THEN 'low sugar' END, CASE WHEN (anon_3.sugar_content_percent >= anon_10.sugar_high) THEN 'high sugar' END], NULL) AS tags
FROM (SELECT anon_8.resource_id AS resource_id, avg(CASE WHEN (anon_9.parameter = 'moisture') THEN anon_9.value END) AS moisture_percent, avg(CASE WHEN (anon_9.parameter = 'ash') THEN anon_9.value END) AS ash_percent, CASE WHEN (avg(CASE WHEN (anon_9.parameter = 'lignin') THEN anon_9.value END) IS NOT NULL OR avg(CASE WHEN (anon_9.parameter = 'lignin+') THEN anon_9.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_9.parameter = 'lignin') THEN anon_9.value END), 0) + coalesce(avg(CASE WHEN (anon_9.parameter = 'lignin+') THEN anon_9.value END), 0) END AS lignin_percent, CASE WHEN (avg(CASE WHEN (anon_9.parameter = 'glucose') THEN anon_9.value END) IS NOT NULL OR avg(CASE WHEN (anon_9.parameter = 'xylose') THEN anon_9.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_9.parameter = 'glucose') THEN anon_9.value END), 0) + coalesce(avg(CASE WHEN (anon_9.parameter = 'xylose') THEN anon_9.value END), 0) END AS sugar_content_percent, avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) AS carbon_percent, avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'hydrogen') THEN anon_9.value END) AS hydrogen_percent, CASE WHEN (avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) IS NOT NULL AND avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) IS NOT NULL AND avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) != 0) THEN avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) / CAST(avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) AS NUMERIC) END AS cn_ratio, bool_or(anon_8.type = 'proximate analysis') AS has_proximate, bool_or(anon_8.type = 'compositional analysis') AS has_compositional, bool_or(anon_8.type = 'ultimate analysis') AS has_ultimate, bool_or(anon_8.type = 'xrf analysis') AS has_xrf, bool_or(anon_8.type = 'icp analysis') AS has_icp, bool_or(anon_8.type = 'calorimetry analysis') AS has_calorimetry, bool_or(anon_8.type = 'xrd analysis') AS has_xrd, bool_or(anon_8.type = 'ftnir analysis') AS has_ftnir, bool_or(anon_8.type = 'fermentation') AS has_fermentation, bool_or(anon_8.type = 'gasification') AS has_gasification, bool_or(anon_8.type = 'pretreatment') AS has_pretreatment
FROM (SELECT compositional_record.resource_id AS resource_id, compositional_record.record_id AS record_id, 'compositional analysis' AS type
FROM compositional_record
WHERE compositional_record.qc_pass != 'fail' UNION ALL SELECT proximate_record.resource_id AS resource_id, proximate_record.record_id AS record_id, 'proximate analysis' AS type
FROM proximate_record
WHERE proximate_record.qc_pass != 'fail' UNION ALL SELECT ultimate_record.resource_id AS resource_id, ultimate_record.record_id AS record_id, 'ultimate analysis' AS type
FROM ultimate_record
WHERE ultimate_record.qc_pass != 'fail' UNION ALL SELECT xrf_record.resource_id AS resource_id, xrf_record.record_id AS record_id, 'xrf analysis' AS type
FROM xrf_record
WHERE xrf_record.qc_pass != 'fail' UNION ALL SELECT icp_record.resource_id AS resource_id, icp_record.record_id AS record_id, 'icp analysis' AS type
FROM icp_record
WHERE icp_record.qc_pass != 'fail' UNION ALL SELECT calorimetry_record.resource_id AS resource_id, calorimetry_record.record_id AS record_id, 'calorimetry analysis' AS type
FROM calorimetry_record
WHERE calorimetry_record.qc_pass != 'fail' UNION ALL SELECT xrd_record.resource_id AS resource_id, xrd_record.record_id AS record_id, 'xrd analysis' AS type
FROM xrd_record
WHERE xrd_record.qc_pass != 'fail' UNION ALL SELECT ftnir_record.resource_id AS resource_id, ftnir_record.record_id AS record_id, 'ftnir analysis' AS type
FROM ftnir_record
WHERE ftnir_record.qc_pass != 'fail' UNION ALL SELECT fermentation_record.resource_id AS resource_id, fermentation_record.record_id AS record_id, 'fermentation' AS type
FROM fermentation_record
WHERE fermentation_record.qc_pass != 'fail' UNION ALL SELECT gasification_record.resource_id AS resource_id, gasification_record.record_id AS record_id, 'gasification' AS type
FROM gasification_record
WHERE gasification_record.qc_pass != 'fail' UNION ALL SELECT pretreatment_record.resource_id AS resource_id, pretreatment_record.record_id AS record_id, 'pretreatment' AS type
FROM pretreatment_record
WHERE pretreatment_record.qc_pass != 'fail') AS anon_8 LEFT OUTER JOIN (SELECT observation.record_id AS record_id, observation.record_type AS record_type, parameter.name AS parameter, observation.value AS value
FROM observation JOIN parameter ON observation.parameter_id = parameter.id
WHERE observation.record_type IN ('compositional analysis', 'proximate analysis', 'ultimate analysis', 'xrf analysis', 'icp analysis', 'calorimetry analysis', 'xrd analysis', 'ftnir analysis', 'pretreatment', 'gasification', 'fermentation')) AS anon_9 ON lower(anon_8.record_id) = lower(anon_9.record_id) AND anon_9.record_type = anon_8.type GROUP BY anon_8.resource_id) AS anon_3 JOIN (SELECT percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_3.moisture_percent) AS moisture_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_3.moisture_percent) AS moisture_high, percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_3.ash_percent) AS ash_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_3.ash_percent) AS ash_high, percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_3.lignin_percent) AS lignin_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_3.lignin_percent) AS lignin_high, percentile_cont(0.1) WITHIN GROUP (ORDER BY anon_3.sugar_content_percent) AS sugar_low, percentile_cont(0.9) WITHIN GROUP (ORDER BY anon_3.sugar_content_percent) AS sugar_high
FROM (SELECT anon_8.resource_id AS resource_id, avg(CASE WHEN (anon_9.parameter = 'moisture') THEN anon_9.value END) AS moisture_percent, avg(CASE WHEN (anon_9.parameter = 'ash') THEN anon_9.value END) AS ash_percent, CASE WHEN (avg(CASE WHEN (anon_9.parameter = 'lignin') THEN anon_9.value END) IS NOT NULL OR avg(CASE WHEN (anon_9.parameter = 'lignin+') THEN anon_9.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_9.parameter = 'lignin') THEN anon_9.value END), 0) + coalesce(avg(CASE WHEN (anon_9.parameter = 'lignin+') THEN anon_9.value END), 0) END AS lignin_percent, CASE WHEN (avg(CASE WHEN (anon_9.parameter = 'glucose') THEN anon_9.value END) IS NOT NULL OR avg(CASE WHEN (anon_9.parameter = 'xylose') THEN anon_9.value END) IS NOT NULL) THEN coalesce(avg(CASE WHEN (anon_9.parameter = 'glucose') THEN anon_9.value END), 0) + coalesce(avg(CASE WHEN (anon_9.parameter = 'xylose') THEN anon_9.value END), 0) END AS sugar_content_percent, avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) AS carbon_percent, avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'hydrogen') THEN anon_9.value END) AS hydrogen_percent, CASE WHEN (avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) IS NOT NULL AND avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) IS NOT NULL AND avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) != 0) THEN avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'carbon') THEN anon_9.value END) / CAST(avg(CASE WHEN (anon_8.type = 'ultimate analysis' AND lower(anon_9.parameter) = 'nitrogen') THEN anon_9.value END) AS NUMERIC) END AS cn_ratio, bool_or(anon_8.type = 'proximate analysis') AS has_proximate, bool_or(anon_8.type = 'compositional analysis') AS has_compositional, bool_or(anon_8.type = 'ultimate analysis') AS has_ultimate, bool_or(anon_8.type = 'xrf analysis') AS has_xrf, bool_or(anon_8.type = 'icp analysis') AS has_icp, bool_or(anon_8.type = 'calorimetry analysis') AS has_calorimetry, bool_or(anon_8.type = 'xrd analysis') AS has_xrd, bool_or(anon_8.type = 'ftnir analysis') AS has_ftnir, bool_or(anon_8.type = 'fermentation') AS has_fermentation, bool_or(anon_8.type = 'gasification') AS has_gasification, bool_or(anon_8.type = 'pretreatment') AS has_pretreatment
FROM (SELECT compositional_record.resource_id AS resource_id, compositional_record.record_id AS record_id, 'compositional analysis' AS type
FROM compositional_record
WHERE compositional_record.qc_pass != 'fail' UNION ALL SELECT proximate_record.resource_id AS resource_id, proximate_record.record_id AS record_id, 'proximate analysis' AS type
FROM proximate_record
WHERE proximate_record.qc_pass != 'fail' UNION ALL SELECT ultimate_record.resource_id AS resource_id, ultimate_record.record_id AS record_id, 'ultimate analysis' AS type
FROM ultimate_record
WHERE ultimate_record.qc_pass != 'fail' UNION ALL SELECT xrf_record.resource_id AS resource_id, xrf_record.record_id AS record_id, 'xrf analysis' AS type
FROM xrf_record
WHERE xrf_record.qc_pass != 'fail' UNION ALL SELECT icp_record.resource_id AS resource_id, icp_record.record_id AS record_id, 'icp analysis' AS type
FROM icp_record
WHERE icp_record.qc_pass != 'fail' UNION ALL SELECT calorimetry_record.resource_id AS resource_id, calorimetry_record.record_id AS record_id, 'calorimetry analysis' AS type
FROM calorimetry_record
WHERE calorimetry_record.qc_pass != 'fail' UNION ALL SELECT xrd_record.resource_id AS resource_id, xrd_record.record_id AS record_id, 'xrd analysis' AS type
FROM xrd_record
WHERE xrd_record.qc_pass != 'fail' UNION ALL SELECT ftnir_record.resource_id AS resource_id, ftnir_record.record_id AS record_id, 'ftnir analysis' AS type
FROM ftnir_record
WHERE ftnir_record.qc_pass != 'fail' UNION ALL SELECT fermentation_record.resource_id AS resource_id, fermentation_record.record_id AS record_id, 'fermentation' AS type
FROM fermentation_record
WHERE fermentation_record.qc_pass != 'fail' UNION ALL SELECT gasification_record.resource_id AS resource_id, gasification_record.record_id AS record_id, 'gasification' AS type
FROM gasification_record
WHERE gasification_record.qc_pass != 'fail' UNION ALL SELECT pretreatment_record.resource_id AS resource_id, pretreatment_record.record_id AS record_id, 'pretreatment' AS type
FROM pretreatment_record
WHERE pretreatment_record.qc_pass != 'fail') AS anon_8 LEFT OUTER JOIN (SELECT observation.record_id AS record_id, observation.record_type AS record_type, parameter.name AS parameter, observation.value AS value
FROM observation JOIN parameter ON observation.parameter_id = parameter.id
WHERE observation.record_type IN ('compositional analysis', 'proximate analysis', 'ultimate analysis', 'xrf analysis', 'icp analysis', 'calorimetry analysis', 'xrd analysis', 'ftnir analysis', 'pretreatment', 'gasification', 'fermentation')) AS anon_9 ON lower(anon_8.record_id) = lower(anon_9.record_id) AND anon_9.record_type = anon_8.type GROUP BY anon_8.resource_id) AS anon_3) AS anon_10 ON true) AS anon_6 ON anon_6.resource_id = resource.id LEFT OUTER JOIN (SELECT resource.id AS resource_id, resource.name AS resource_name, min(resource_availability.from_month) AS from_month, max(resource_availability.to_month) AS to_month, bool_or(resource_availability.year_round) AS year_round, avg(resource_availability.residue_factor_dry_tons_acre) AS dry_tons_per_acre, avg(resource_availability.residue_factor_wet_tons_acre) AS wet_tons_per_acre
FROM resource_availability JOIN resource ON resource_availability.resource_id = resource.id GROUP BY resource.id, resource.name) AS anon_7 ON anon_7.resource_id = resource.id LEFT OUTER JOIN (SELECT resource_transport_record.resource_id AS resource_id, max(resource_transport_record.transport_description) AS transport_notes
FROM resource_transport_record GROUP BY resource_transport_record.resource_id) AS anon_4 ON anon_4.resource_id = resource.id LEFT OUTER JOIN (SELECT resource_storage_record.resource_id AS resource_id, max(resource_storage_record.storage_description) AS storage_notes
FROM resource_storage_record GROUP BY resource_storage_record.resource_id) AS anon_5 ON anon_5.resource_id = resource.id LEFT OUTER JOIN (SELECT resource_usda_commodity_map.resource_id AS resource_id, max(primary_ag_product.name) AS primary_product_fallback
FROM resource_usda_commodity_map JOIN primary_ag_product ON resource_usda_commodity_map.primary_ag_product_id = primary_ag_product.id
WHERE resource_usda_commodity_map.resource_id IS NOT NULL GROUP BY resource_usda_commodity_map.resource_id) AS anon_1 ON anon_1.resource_id = resource.id
WHERE lower(resource.name) != 'sargassum'
"""


def upgrade() -> None:
    """Recreate biomass materialized views from frozen SQL snapshots."""
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_primary_product CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_resource_subclass CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_resource_class CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_name_trgm CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_search_vector CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_search_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_end_uses_resource_id CASCADE")
    op.execute("DROP INDEX IF EXISTS data_portal.idx_mv_biomass_end_uses_resource_use_case CASCADE")

    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_search CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_end_uses CASCADE")

    op.execute(f"CREATE MATERIALIZED VIEW data_portal.mv_biomass_search AS {MV_BIOMASS_SEARCH_SQL}")
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_search_id ON data_portal.mv_biomass_search (id)")
    op.execute("CREATE INDEX idx_mv_biomass_search_search_vector ON data_portal.mv_biomass_search USING GIN (search_vector)")
    op.execute("CREATE INDEX idx_mv_biomass_search_name_trgm ON data_portal.mv_biomass_search USING GIN (name gin_trgm_ops)")
    op.execute("CREATE INDEX idx_mv_biomass_search_resource_class ON data_portal.mv_biomass_search (resource_class)")
    op.execute("CREATE INDEX idx_mv_biomass_search_resource_subclass ON data_portal.mv_biomass_search (resource_subclass)")
    op.execute("CREATE INDEX idx_mv_biomass_search_primary_product ON data_portal.mv_biomass_search (primary_product)")

    op.execute(f"CREATE MATERIALIZED VIEW data_portal.mv_biomass_end_uses AS {MV_BIOMASS_END_USES_SQL}")
    op.execute("CREATE UNIQUE INDEX idx_mv_biomass_end_uses_resource_use_case ON data_portal.mv_biomass_end_uses (resource_id, use_case)")
    op.execute("CREATE INDEX idx_mv_biomass_end_uses_resource_id ON data_portal.mv_biomass_end_uses (resource_id)")

    op.execute("GRANT USAGE ON SCHEMA data_portal TO biocirv_readonly")
    op.execute("GRANT SELECT ON data_portal.mv_biomass_search TO biocirv_readonly")
    op.execute("GRANT SELECT ON data_portal.mv_biomass_end_uses TO biocirv_readonly")


def downgrade() -> None:
    """Drop biomass materialized views created by this revision."""
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_search CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_end_uses CASCADE")
