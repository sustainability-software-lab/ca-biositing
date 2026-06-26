# Data Dictionary: Materialized Views

This document outlines the schema for the core materialized views in the
`data_portal` schema. These views are optimized for read performance and are the
primary data source for the web service and data portal.

## mv_biomass_availability

| Column Name         | Data Type         | Description |
| :------------------ | :---------------- | :---------- |
| `resource_id`       | integer           |             |
| `resource_name`     | character varying |             |
| `from_month`        | integer           |             |
| `to_month`          | integer           |             |
| `year_round`        | boolean           |             |
| `dry_tons_per_acre` | double precision  |             |
| `wet_tons_per_acre` | double precision  |             |

## mv_biomass_composition

| Column Name         | Data Type         | Description |
| :------------------ | :---------------- | :---------- |
| `id`                | bigint            |             |
| `resource_id`       | integer           |             |
| `resource_name`     | character varying |             |
| `analysis_type`     | text              |             |
| `parameter_name`    | character varying |             |
| `geoid`             | character varying |             |
| `county`            | character varying |             |
| `unit`              | character varying |             |
| `avg_value`         | numeric           |             |
| `min_value`         | numeric           |             |
| `max_value`         | numeric           |             |
| `std_dev`           | numeric           |             |
| `observation_count` | bigint            |             |

## mv_biomass_county_production

| Column Name           | Data Type         | Description |
| :-------------------- | :---------------- | :---------- |
| `id`                  | bigint            |             |
| `resource_id`         | integer           |             |
| `resource_name`       | character varying |             |
| `resource_class`      | character varying |             |
| `geoid`               | character varying |             |
| `county`              | character varying |             |
| `state`               | character varying |             |
| `scenario`            | character varying |             |
| `price_offered_usd`   | numeric           |             |
| `production`          | integer           |             |
| `production_unit`     | character varying |             |
| `energy_content`      | bigint            |             |
| `energy_unit`         | character varying |             |
| `density_dt_per_sqmi` | numeric           |             |
| `county_square_miles` | double precision  |             |
| `year`                | integer           |             |

## mv_biomass_end_uses

| Column Name             | Data Type         | Description |
| :---------------------- | :---------------- | :---------- |
| `resource_id`           | integer           |             |
| `resource_name`         | character varying |             |
| `use_case`              | character varying |             |
| `percentage_low`        | double precision  |             |
| `percentage_high`       | double precision  |             |
| `trend`                 | text              |             |
| `value_low_usd`         | double precision  |             |
| `value_high_usd`        | double precision  |             |
| `value_multiplier_low`  | double precision  |             |
| `value_multiplier_high` | double precision  |             |
| `value_notes`           | text              |             |

## mv_biomass_fermentation

| Column Name            | Data Type         | Description |
| :--------------------- | :---------------- | :---------- |
| `id`                   | bigint            |             |
| `resource_id`          | integer           |             |
| `resource_name`        | character varying |             |
| `geoid`                | character varying |             |
| `county`               | character varying |             |
| `strain_name`          | text              |             |
| `pretreatment_method`  | character varying |             |
| `enzyme_name`          | character varying |             |
| `bioconversion_method` | character varying |             |
| `elapsed_time`         | double precision  |             |
| `product_name`         | character varying |             |
| `avg_value`            | numeric           |             |
| `min_value`            | numeric           |             |
| `max_value`            | numeric           |             |
| `std_dev`              | numeric           |             |
| `observation_count`    | bigint            |             |
| `unit`                 | character varying |             |

## mv_biomass_gasification

| Column Name         | Data Type         | Description |
| :------------------ | :---------------- | :---------- |
| `id`                | bigint            |             |
| `resource_id`       | integer           |             |
| `resource_name`     | character varying |             |
| `reactor_type`      | character varying |             |
| `parameter_name`    | text              |             |
| `geoid`             | character varying |             |
| `avg_value`         | numeric           |             |
| `min_value`         | numeric           |             |
| `max_value`         | numeric           |             |
| `std_dev`           | numeric           |             |
| `observation_count` | bigint            |             |
| `unit`              | character varying |             |

## mv_biomass_pricing

| Column Name            | Data Type                   | Description |
| :--------------------- | :-------------------------- | :---------- |
| `id`                   | bigint                      |             |
| `resource_id`          | integer                     |             |
| `resource_name`        | character varying           |             |
| `geoid`                | character varying           |             |
| `county`               | character varying           |             |
| `county_fips`          | character varying           |             |
| `state`                | character varying           |             |
| `report_date`          | timestamp without time zone |             |
| `report_source`        | character varying           |             |
| `market_type_category` | character varying           |             |
| `sale_type`            | character varying           |             |
| `price_min`            | numeric                     |             |
| `price_max`            | numeric                     |             |
| `price_avg`            | numeric                     |             |
| `price_unit`           | character varying           |             |

## mv_biomass_sample_stats

| Column Name          | Data Type         | Description |
| :------------------- | :---------------- | :---------- |
| `resource_id`        | integer           |             |
| `resource_name`      | character varying |             |
| `sample_count`       | bigint            |             |
| `supplier_count`     | bigint            |             |
| `dataset_count`      | bigint            |             |
| `total_record_count` | bigint            |             |

## mv_biomass_search

| Column Name                      | Data Type                   | Description |
| :------------------------------- | :-------------------------- | :---------- |
| `id`                             | integer                     |             |
| `name`                           | character varying           |             |
| `resource_code`                  | character varying           |             |
| `description`                    | character varying           |             |
| `resource_class`                 | character varying           |             |
| `resource_subclass`              | character varying           |             |
| `primary_product`                | character varying           |             |
| `image_url`                      | character varying           |             |
| `literature_uri`                 | character varying           |             |
| `total_annual_volume`            | numeric                     |             |
| `county_count`                   | bigint                      |             |
| `volume_unit`                    | text                        |             |
| `total_annual_volume_year`       | integer                     |             |
| `moisture_percent`               | numeric                     |             |
| `sugar_content_percent`          | numeric                     |             |
| `glucan_percent`                 | numeric                     |             |
| `xylan_percent`                  | numeric                     |             |
| `ash_percent`                    | numeric                     |             |
| `lignin_percent`                 | numeric                     |             |
| `carbon_percent`                 | numeric                     |             |
| `hydrogen_percent`               | numeric                     |             |
| `cn_ratio`                       | numeric                     |             |
| `transport_notes`                | text                        |             |
| `storage_notes`                  | text                        |             |
| `tags`                           | text[]                      |             |
| `season_from_month`              | integer                     |             |
| `season_to_month`                | integer                     |             |
| `year_round`                     | boolean                     |             |
| `has_proximate`                  | boolean                     |             |
| `has_compositional`              | boolean                     |             |
| `has_ultimate`                   | boolean                     |             |
| `has_xrf`                        | boolean                     |             |
| `has_icp`                        | boolean                     |             |
| `has_calorimetry`                | boolean                     |             |
| `has_xrd`                        | boolean                     |             |
| `has_ftnir`                      | boolean                     |             |
| `has_fermentation`               | boolean                     |             |
| `has_gasification`               | boolean                     |             |
| `has_pretreatment`               | boolean                     |             |
| `has_moisture_data`              | boolean                     |             |
| `has_sugar_data`                 | boolean                     |             |
| `has_image`                      | boolean                     |             |
| `has_volume_data`                | boolean                     |             |
| `calculated_estimate_volume_min` | numeric                     |             |
| `calculated_estimate_volume_max` | numeric                     |             |
| `calculated_estimate_volume_mid` | numeric                     |             |
| `volume_estimate_year`           | integer                     |             |
| `created_at`                     | timestamp without time zone |             |
| `updated_at`                     | timestamp without time zone |             |
| `search_vector`                  | tsvector                    |             |

## mv_biomass_volume_estimate

| Column Name                    | Data Type         | Description |
| :----------------------------- | :---------------- | :---------- |
| `id`                           | bigint            |             |
| `resource_id`                  | integer           |             |
| `resource_name`                | character varying |             |
| `geoid`                        | character varying |             |
| `county`                       | character varying |             |
| `county_fips`                  | character varying |             |
| `state`                        | character varying |             |
| `dataset_year`                 | integer           |             |
| `production_volume`            | numeric           |             |
| `county_crop_acres`            | numeric           |             |
| `production_unit`              | character varying |             |
| `factor_min`                   | numeric           |             |
| `factor_mid`                   | numeric           |             |
| `factor_max`                   | numeric           |             |
| `estimated_residue_volume_min` | numeric           |             |
| `estimated_residue_volume_mid` | numeric           |             |
| `estimated_residue_volume_max` | numeric           |             |
| `volume_source`                | character varying |             |
| `biomass_unit`                 | character varying |             |

## mv_usda_county_production

| Column Name                  | Data Type         | Description |
| :--------------------------- | :---------------- | :---------- |
| `id`                         | bigint            |             |
| `resource_id`                | integer           |             |
| `resource_name`              | character varying |             |
| `primary_ag_product`         | character varying |             |
| `geoid`                      | character varying |             |
| `county`                     | character varying |             |
| `state`                      | character varying |             |
| `dataset_year`               | integer           |             |
| `primary_product_volume`     | numeric           |             |
| `volume_unit`                | text              |             |
| `production_acres`           | numeric           |             |
| `known_biomass_volume`       | text              |             |
| `calculated_estimate_volume` | double precision  |             |
| `biomass_unit`               | text              |             |
