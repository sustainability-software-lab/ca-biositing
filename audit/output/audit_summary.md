# Database Audit Summary (local)

Generated: 2026-05-05T13:25:14.347965 Database: localhost:5432

---

## Module: common_quality

### Result 1

Command executed successfully.

### Result 2

| record_type        | record_id | parameter                  | observation_count |
| ------------------ | --------- | -------------------------- | ----------------- |
| usda_census_record | 1         | area bearing               | 2                 |
| usda_census_record | 1         | area bearing & non-bearing | 2                 |
| usda_census_record | 1         | area non-bearing           | 2                 |
| usda_survey_record | 1         | production                 | 2                 |
| usda_survey_record | 1         | yield                      | 2                 |
| usda_census_record | 10        | area bearing & non-bearing | 2                 |
| usda_survey_record | 10        | production                 | 2                 |
| usda_survey_record | 10        | yield                      | 2                 |
| usda_census_record | 100       | area harvested             | 2                 |
| usda_survey_record | 100       | yield                      | 2                 |
| usda_census_record | 101       | area harvested             | 2                 |
| usda_survey_record | 101       | yield                      | 2                 |
| usda_census_record | 102       | area bearing               | 2                 |
| usda_survey_record | 102       | yield                      | 2                 |
| usda_census_record | 103       | area bearing               | 2                 |
| usda_census_record | 103       | area bearing & non-bearing | 2                 |
| usda_census_record | 103       | area non-bearing           | 2                 |
| usda_survey_record | 103       | yield                      | 2                 |
| usda_census_record | 104       | area bearing               | 2                 |
| usda_census_record | 104       | area bearing & non-bearing | 2                 |
| usda_census_record | 104       | area non-bearing           | 2                 |
| usda_survey_record | 104       | yield                      | 2                 |
| usda_census_record | 105       | area bearing & non-bearing | 2                 |
| usda_survey_record | 105       | yield                      | 2                 |
| usda_census_record | 106       | area bearing & non-bearing | 2                 |
| usda_survey_record | 106       | yield                      | 2                 |
| usda_census_record | 107       | area harvested             | 2                 |
| usda_census_record | 107       | sales                      | 2                 |
| usda_survey_record | 107       | yield                      | 2                 |
| usda_census_record | 108       | area harvested             | 2                 |
| usda_census_record | 108       | sales                      | 2                 |
| usda_survey_record | 108       | yield                      | 2                 |
| usda_census_record | 109       | area harvested             | 2                 |
| usda_census_record | 109       | sales                      | 2                 |
| usda_survey_record | 109       | yield                      | 2                 |
| usda_census_record | 11        | area harvested             | 2                 |
| usda_census_record | 11        | production                 | 2                 |
| usda_census_record | 11        | sales                      | 2                 |
| usda_survey_record | 11        | production                 | 2                 |
| usda_survey_record | 11        | yield                      | 2                 |
| usda_census_record | 110       | area harvested             | 2                 |
| usda_census_record | 110       | sales                      | 2                 |
| usda_survey_record | 110       | yield                      | 2                 |
| usda_census_record | 111       | area harvested             | 2                 |
| usda_survey_record | 111       | yield                      | 2                 |
| usda_census_record | 112       | area harvested             | 2                 |
| usda_survey_record | 112       | yield                      | 2                 |
| usda_census_record | 113       | area bearing               | 2                 |
| usda_census_record | 113       | area bearing & non-bearing | 2                 |
| usda_census_record | 113       | area non-bearing           | 2                 |

### Result 3

| parameter                  | unique_units | units                                                                           |
| -------------------------- | ------------ | ------------------------------------------------------------------------------- |
| area bearing               | 2            | acres, operations                                                               |
| area bearing & non-bearing | 2            | acres, operations                                                               |
| area harvested             | 2            | acres, operations                                                               |
| area non-bearing           | 2            | acres, operations                                                               |
| ash                        | 2            | g, % total weight                                                               |
| ca                         | 2            | pc, ppm                                                                         |
| k                          | 2            | pc, ppm                                                                         |
| mg                         | 2            | pc, ppm                                                                         |
| p                          | 2            | pc, ppm                                                                         |
| production                 | 5            | 480 lb bales, bales, bu, cwt, tons                                              |
| sales                      | 2            | $, operations                                                                   |
| yield                      | 5            | bu / acre, bu / net planted acre, lb / acre, lb / net planted acre, tons / acre |

### Result 4

| type          | fail_count |
| ------------- | ---------- |
| proximate     | 111        |
| ultimate      | 3          |
| compositional | 0          |
| icp           | 168        |
| fermentation  | 285        |

---

## Module: compositional

### Result 1

| record_type   | total_records | qc_pass_count | qc_fail_count | qc_null_count |
| ------------- | ------------- | ------------- | ------------- | ------------- |
| compositional | 968           | 737           | 0             | 231           |

### Result 2

| record_type   | total_qc_non_fail | analyst_filled | analyst_pct | method_filled | method_pct | raw_data_filled | raw_data_pct | experiment_filled | experiment_pct | dataset_filled | dataset_pct |
| ------------- | ----------------- | -------------- | ----------- | ------------- | ---------- | --------------- | ------------ | ----------------- | -------------- | -------------- | ----------- |
| compositional | 737               | 390            | 52.9        | 737           | 100.0      | 284             | 38.5         | 0                 | 0.0            | 737            | 100.0       |

### Result 3

| record_type   | unique_prepared_samples | unique_resources | unique_experiments | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ------------- | ----------------------- | ---------------- | ------------------ | -------------------- | -------------------------- | --------------------- |
| compositional | 47                      | 25               | 0                  | 47                   | 12                         | 25.5                  |

### Result 4

| parameter | obs_count | unit_count | units_used   | records_with_param | record_coverage_pct |
| --------- | --------- | ---------- | ------------ | ------------------ | ------------------- |
| xylan     | 144       | 1          | % dry weight | 144                | 19.5                |
| xylose    | 144       | 1          | % dry weight | 144                | 19.5                |
| glucan    | 144       | 1          | % dry weight | 144                | 19.5                |
| glucose   | 144       | 1          | % dry weight | 144                | 19.5                |
| lignin    | 132       | 1          | % dry weight | 132                | 17.9                |
| lignin+   | 12        | 1          | % dry weight | 12                 | 1.6                 |
| arabinan  | 9         | 1          | % dry weight | 9                  | 1.2                 |
| arabinose | 9         | 1          | % dry weight | 9                  | 1.2                 |

### Result 5

| parameter | min_val | max_val | avg_val | negative_values_count |
| --------- | ------- | ------- | ------- | --------------------- |
| arabinan  | 1.81    | 2.41    | 2.1389  | 0                     |
| arabinose | 2.06    | 2.74    | 2.4311  | 0                     |
| glucan    | 5.57    | 54.57   | 23.9038 | 0                     |
| glucose   | 6.19    | 60.64   | 26.5595 | 0                     |
| lignin    | 8.57    | 52.78   | 30.0073 | 0                     |
| lignin+   | 30.53   | 53.96   | 41.2517 | 0                     |
| xylan     | 2.92    | 25.71   | 13.8348 | 0                     |
| xylose    | 3.32    | 29.21   | 15.7221 | 0                     |

---

## Module: fermentation

### Result 1

| record_type  | total_records | qc_pass_count | qc_fail_count | qc_null_count | pass_pct |
| ------------ | ------------- | ------------- | ------------- | ------------- | -------- |
| fermentation | 4021          | 3736          | 285           | 0             | 92.9     |

### Result 2

| record_type  | total_qc_non_fail | analyst_filled | method_filled | raw_data_filled | experiment_filled | strain_filled | vessel_filled | pretreatment_method_filled | eh_method_filled | bioconversion_method_filled | well_position_filled |
| ------------ | ----------------- | -------------- | ------------- | --------------- | ----------------- | ------------- | ------------- | -------------------------- | ---------------- | --------------------------- | -------------------- |
| fermentation | 3736              | 3736           | 0             | 3736            | 0                 | 3736          | 3736          | 3505                       | 3735             | 3736                        | 3736                 |

### Result 3

| record_type  | analyst_pct | method_pct | experiment_pct | strain_pct | pretreatment_pct | eh_pct | bioconversion_pct |
| ------------ | ----------- | ---------- | -------------- | ---------- | ---------------- | ------ | ----------------- |
| fermentation | 100.0       | 0.0        | 0.0            | 100.0      | 93.8             | 100.0  | 100.0             |

### Result 4

| record_type  | unique_prepared_samples | unique_resources | unique_experiments | unique_field_samples | unique_primary_ag_products |
| ------------ | ----------------------- | ---------------- | ------------------ | -------------------- | -------------------------- |
| fermentation | 58                      | 29               | 0                  | 56                   | 13                         |

### Result 5

| parameter   | unit   | obs_count | records_with_param |
| ----------- | ------ | --------- | ------------------ |
| xylconcteof | g_l    | 340       | 340                |
| sugar_cons  | pc     | 340       | 340                |
| sugart0     | g_l    | 340       | 340                |
| sugarteof   | g_l    | 340       | 340                |
| xylconct0   | g_l    | 340       | 340                |
| gluconct0   | g_l    | 340       | 340                |
| gluconcteof | g_l    | 340       | 340                |
| od600teof   | None   | 340       | 340                |
| rel_growth  | pc     | 340       | 340                |
| 3hpyield    | mol_pc | 268       | 268                |
| 3hptiter    | g_l    | 268       | 268                |
| etohtiter   | g_l    | 72        | 72                 |
| etohyield   | mol_pc | 72        | 72                 |

---

## Module: ftnir

### Result 1

| record_type | total_records | qc_pass_count | qc_fail_count | qc_null_count |
| ----------- | ------------- | ------------- | ------------- | ------------- |
| ftnir       | 0             | 0             | 0             | 0             |

### Result 2

| record_type | total_qc_non_fail | analyst_filled | method_filled | raw_data_filled | experiment_filled | dataset_filled |
| ----------- | ----------------- | -------------- | ------------- | --------------- | ----------------- | -------------- |
| ftnir       | 0                 | 0              | 0             | 0               | 0                 | 0              |

### Result 3

| record_type | unique_prepared_samples | unique_resources | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ----------- | ----------------------- | ---------------- | -------------------- | -------------------------- | --------------------- |
| ftnir       | 0                       | 0                | 0                    | 0                          | None                  |

---

## Module: gasification

### Result 1

| record_type  | total_records | qc_pass_count | qc_fail_count | qc_null_count | pass_pct |
| ------------ | ------------- | ------------- | ------------- | ------------- | -------- |
| gasification | 611           | 382           | 194           | 35            | 62.5     |

### Result 2

| record_type  | total_qc_non_fail | analyst_filled | analyst_pct | method_filled | method_pct | experiment_filled | experiment_pct | reactor_filled | dataset_filled |
| ------------ | ----------------- | -------------- | ----------- | ------------- | ---------- | ----------------- | -------------- | -------------- | -------------- |
| gasification | 382               | 382            | 100.0       | 0             | 0.0        | 382               | 100.0          | 382            | 382            |

### Result 3

| record_type  | unique_prepared_samples | unique_resources | unique_experiments | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ------------ | ----------------------- | ---------------- | ------------------ | -------------------- | -------------------------- | --------------------- |
| gasification | 8                       | 6                | 12                 | 8                    | 5                          | 62.5                  |

### Result 4

| parameter | obs_count | unit_count | units_used | records_with_param | record_coverage_pct |
| --------- | --------- | ---------- | ---------- | ------------------ | ------------------- |
| h2        | 21        | 1          | ppm        | 21                 | 5.5                 |
| n2        | 21        | 1          | ppm        | 21                 | 5.5                 |
| o2        | 21        | 1          | ppm        | 21                 | 5.5                 |
| c3h8      | 21        | 1          | ppm        | 21                 | 5.5                 |
| c4h10(b)  | 21        | 1          | ppm        | 21                 | 5.5                 |
| c4h10(i)  | 21        | 1          | ppm        | 21                 | 5.5                 |
| c5h12     | 21        | 1          | ppm        | 21                 | 5.5                 |
| c6h14     | 21        | 1          | ppm        | 21                 | 5.5                 |
| ch4       | 21        | 1          | ppm        | 21                 | 5.5                 |
| c2h6      | 21        | 1          | ppm        | 21                 | 5.5                 |
| co        | 21        | 1          | ppm        | 21                 | 5.5                 |
| co2       | 21        | 1          | ppm        | 21                 | 5.5                 |
| wme       | 12        | 1          | %          | 12                 | 3.1                 |
| bio       | 12        | 1          | g          | 12                 | 3.1                 |
| char      | 12        | 1          | g          | 12                 | 3.1                 |
| va        | 12        | 1          | mps        | 12                 | 3.1                 |
| ash       | 12        | 1          | g          | 12                 | 3.1                 |
| ta        | 12        | 1          | c          | 12                 | 3.1                 |
| tar       | 12        | 1          | g          | 12                 | 3.1                 |
| time      | 12        | 1          | min        | 12                 | 3.1                 |
| unc-bio   | 12        | 1          | g          | 12                 | 3.1                 |
| pi        | 11        | 1          | psi        | 11                 | 2.9                 |
| pv        | 11        | 1          | psi        | 11                 | 2.9                 |

---

## Module: icp

### Result 1

| record_type | total_records | qc_pass_count | qc_fail_count | qc_null_count |
| ----------- | ------------- | ------------- | ------------- | ------------- |
| icp         | 1153          | 985           | 168           | 0             |

### Result 2

| record_type | total_qc_non_fail | analyst_filled | analyst_pct | method_filled | method_pct | raw_data_filled | raw_data_pct | experiment_filled | experiment_pct | dataset_filled | dataset_pct |
| ----------- | ----------------- | -------------- | ----------- | ------------- | ---------- | --------------- | ------------ | ----------------- | -------------- | -------------- | ----------- |
| icp         | 985               | 826            | 83.9        | 0             | 0.0        | 827             | 84.0         | 0                 | 0.0            | 985            | 100.0       |

### Result 3

| record_type | unique_prepared_samples | unique_resources | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ----------- | ----------------------- | ---------------- | -------------------- | -------------------------- | --------------------- |
| icp         | 25                      | 17               | 24                   | 6                          | 24.0                  |

### Result 4

| parameter | obs_count | unit_count | units_used | records_with_param | record_coverage_pct |
| --------- | --------- | ---------- | ---------- | ------------------ | ------------------- |
| al        | 83        | 1          | ppm        | 83                 | 8.4                 |
| nd        | 66        | 1          | ppm        | 66                 | 6.7                 |
| cu        | 64        | 1          | ppm        | 64                 | 6.5                 |
| fe        | 64        | 1          | ppm        | 64                 | 6.5                 |
| zn        | 64        | 1          | ppm        | 64                 | 6.5                 |
| ca        | 64        | 2          | pc, ppm    | 64                 | 6.5                 |
| mn        | 64        | 1          | ppm        | 64                 | 6.5                 |
| p         | 64        | 2          | pc, ppm    | 64                 | 6.5                 |
| s         | 64        | 1          | ppm        | 64                 | 6.5                 |
| mg        | 63        | 2          | pc, ppm    | 63                 | 6.4                 |
| k         | 61        | 2          | pc, ppm    | 61                 | 6.2                 |
| ti        | 60        | 1          | ppm        | 60                 | 6.1                 |
| si        | 47        | 1          | ppm        | 47                 | 4.8                 |
| na        | 45        | 1          | ppm        | 45                 | 4.6                 |
| b         | 16        | 1          | ppm        | 16                 | 1.6                 |

---

## Module: lineage

### Result 1

| total_prepared | linked_to_ag_product | integrity_pct |
| -------------- | -------------------- | ------------- |
| 296            | 296                  | 93.58         |

### Result 2

| id  | name                  |
| --- | --------------------- |
| 291 | boa-gppm053a(53)      |
| 292 | war-al037             |
| 293 | war-alf037a(b8)       |
| 294 | rho synthetic media   |
| 295 | rhodo synthetic media |
| 296 | sac synthetic media   |

---

## Module: materialized_views

### Result 1

| view_name                    | column_name         | data_type         | is_nullable |
| ---------------------------- | ------------------- | ----------------- | ----------- |
| mv_biomass_availability      | resource_id         | integer           | True        |
| mv_biomass_availability      | resource_name       | character varying | True        |
| mv_biomass_availability      | from_month          | integer           | True        |
| mv_biomass_availability      | to_month            | integer           | True        |
| mv_biomass_availability      | year_round          | boolean           | True        |
| mv_biomass_availability      | dry_tons_per_acre   | double precision  | True        |
| mv_biomass_availability      | wet_tons_per_acre   | double precision  | True        |
| mv_biomass_composition       | id                  | bigint            | True        |
| mv_biomass_composition       | resource_id         | integer           | True        |
| mv_biomass_composition       | resource_name       | character varying | True        |
| mv_biomass_composition       | analysis_type       | text              | True        |
| mv_biomass_composition       | parameter_name      | character varying | True        |
| mv_biomass_composition       | geoid               | character varying | True        |
| mv_biomass_composition       | county              | character varying | True        |
| mv_biomass_composition       | unit                | character varying | True        |
| mv_biomass_composition       | avg_value           | numeric           | True        |
| mv_biomass_composition       | min_value           | numeric           | True        |
| mv_biomass_composition       | max_value           | numeric           | True        |
| mv_biomass_composition       | std_dev             | numeric           | True        |
| mv_biomass_composition       | observation_count   | bigint            | True        |
| mv_biomass_county_production | id                  | bigint            | True        |
| mv_biomass_county_production | resource_id         | integer           | True        |
| mv_biomass_county_production | resource_name       | character varying | True        |
| mv_biomass_county_production | resource_class      | character varying | True        |
| mv_biomass_county_production | geoid               | character varying | True        |
| mv_biomass_county_production | county              | character varying | True        |
| mv_biomass_county_production | state               | character varying | True        |
| mv_biomass_county_production | scenario            | character varying | True        |
| mv_biomass_county_production | price_offered_usd   | numeric           | True        |
| mv_biomass_county_production | production          | integer           | True        |
| mv_biomass_county_production | production_unit     | character varying | True        |
| mv_biomass_county_production | energy_content      | bigint            | True        |
| mv_biomass_county_production | energy_unit         | character varying | True        |
| mv_biomass_county_production | density_dt_per_sqmi | numeric           | True        |
| mv_biomass_county_production | county_square_miles | double precision  | True        |
| mv_biomass_county_production | year                | integer           | True        |
| mv_biomass_end_uses          | resource_id         | integer           | True        |
| mv_biomass_end_uses          | resource_name       | character varying | True        |
| mv_biomass_end_uses          | use_case            | character varying | True        |
| mv_biomass_end_uses          | percentage_low      | double precision  | True        |
| mv_biomass_end_uses          | percentage_high     | double precision  | True        |
| mv_biomass_end_uses          | trend               | text              | True        |
| mv_biomass_end_uses          | value_low_usd       | double precision  | True        |
| mv_biomass_end_uses          | value_high_usd      | double precision  | True        |
| mv_biomass_end_uses          | value_notes         | text              | True        |
| mv_biomass_fermentation      | id                  | bigint            | True        |
| mv_biomass_fermentation      | resource_id         | integer           | True        |
| mv_biomass_fermentation      | resource_name       | character varying | True        |
| mv_biomass_fermentation      | geoid               | character varying | True        |
| mv_biomass_fermentation      | county              | character varying | True        |

_Truncated: showing 50 of 172 rows._

### Result 2

| schemaname  | view_name                    | indexname                                          | indexdef                                                                                                                                                       |
| ----------- | ---------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| data_portal | mv_biomass_availability      | idx_mv_biomass_availability_resource_id            | CREATE UNIQUE INDEX idx_mv_biomass_availability_resource_id ON data_portal.mv_biomass_availability USING btree (resource_id)                                   |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_analysis_type           | CREATE INDEX idx_mv_biomass_composition_analysis_type ON data_portal.mv_biomass_composition USING btree (analysis_type)                                        |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_county                  | CREATE INDEX idx_mv_biomass_composition_county ON data_portal.mv_biomass_composition USING btree (county)                                                      |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_geoid                   | CREATE INDEX idx_mv_biomass_composition_geoid ON data_portal.mv_biomass_composition USING btree (geoid)                                                        |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_id                      | CREATE UNIQUE INDEX idx_mv_biomass_composition_id ON data_portal.mv_biomass_composition USING btree (id)                                                       |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_parameter_name          | CREATE INDEX idx_mv_biomass_composition_parameter_name ON data_portal.mv_biomass_composition USING btree (parameter_name)                                      |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_resource_analysis       | CREATE INDEX idx_mv_biomass_composition_resource_analysis ON data_portal.mv_biomass_composition USING btree (resource_id, analysis_type)                       |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_resource_geoid_analysis | CREATE INDEX idx_mv_biomass_composition_resource_geoid_analysis ON data_portal.mv_biomass_composition USING btree (resource_id, geoid, analysis_type)          |
| data_portal | mv_biomass_composition       | idx_mv_biomass_composition_resource_id             | CREATE INDEX idx_mv_biomass_composition_resource_id ON data_portal.mv_biomass_composition USING btree (resource_id)                                            |
| data_portal | mv_biomass_county_production | idx_mv_biomass_county_production_id                | CREATE UNIQUE INDEX idx_mv_biomass_county_production_id ON data_portal.mv_biomass_county_production USING btree (id)                                           |
| data_portal | mv_biomass_end_uses          | idx_mv_biomass_end_uses_resource_id                | CREATE INDEX idx_mv_biomass_end_uses_resource_id ON data_portal.mv_biomass_end_uses USING btree (resource_id)                                                  |
| data_portal | mv_biomass_end_uses          | idx_mv_biomass_end_uses_resource_use_case          | CREATE UNIQUE INDEX idx_mv_biomass_end_uses_resource_use_case ON data_portal.mv_biomass_end_uses USING btree (resource_id, use_case)                           |
| data_portal | mv_biomass_fermentation      | idx_mv_biomass_fermentation_county                 | CREATE INDEX idx_mv_biomass_fermentation_county ON data_portal.mv_biomass_fermentation USING btree (county)                                                    |
| data_portal | mv_biomass_fermentation      | idx_mv_biomass_fermentation_geoid                  | CREATE INDEX idx_mv_biomass_fermentation_geoid ON data_portal.mv_biomass_fermentation USING btree (geoid)                                                      |
| data_portal | mv_biomass_fermentation      | idx_mv_biomass_fermentation_id                     | CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation USING btree (id)                                                     |
| data_portal | mv_biomass_fermentation      | idx_mv_biomass_fermentation_product_name           | CREATE INDEX idx_mv_biomass_fermentation_product_name ON data_portal.mv_biomass_fermentation USING btree (product_name)                                        |
| data_portal | mv_biomass_fermentation      | idx_mv_biomass_fermentation_resource_id            | CREATE INDEX idx_mv_biomass_fermentation_resource_id ON data_portal.mv_biomass_fermentation USING btree (resource_id)                                          |
| data_portal | mv_biomass_fermentation      | idx_mv_biomass_fermentation_strain_name            | CREATE INDEX idx_mv_biomass_fermentation_strain_name ON data_portal.mv_biomass_fermentation USING btree (strain_name)                                          |
| data_portal | mv_biomass_gasification      | idx_mv_biomass_gasification_id                     | CREATE UNIQUE INDEX idx_mv_biomass_gasification_id ON data_portal.mv_biomass_gasification USING btree (id)                                                     |
| data_portal | mv_biomass_gasification      | idx_mv_biomass_gasification_parameter_name         | CREATE INDEX idx_mv_biomass_gasification_parameter_name ON data_portal.mv_biomass_gasification USING btree (parameter_name)                                    |
| data_portal | mv_biomass_gasification      | idx_mv_biomass_gasification_reactor_type           | CREATE INDEX idx_mv_biomass_gasification_reactor_type ON data_portal.mv_biomass_gasification USING btree (reactor_type)                                        |
| data_portal | mv_biomass_gasification      | idx_mv_biomass_gasification_resource_id            | CREATE INDEX idx_mv_biomass_gasification_resource_id ON data_portal.mv_biomass_gasification USING btree (resource_id)                                          |
| data_portal | mv_biomass_gasification      | idx_mv_biomass_gasification_resource_reactor_param | CREATE INDEX idx_mv_biomass_gasification_resource_reactor_param ON data_portal.mv_biomass_gasification USING btree (resource_id, reactor_type, parameter_name) |
| data_portal | mv_biomass_pricing           | idx_mv_biomass_pricing_commodity_name              | CREATE INDEX idx_mv_biomass_pricing_commodity_name ON data_portal.mv_biomass_pricing USING btree (commodity_name)                                              |
| data_portal | mv_biomass_pricing           | idx_mv_biomass_pricing_county                      | CREATE INDEX idx_mv_biomass_pricing_county ON data_portal.mv_biomass_pricing USING btree (county)                                                              |
| data_portal | mv_biomass_pricing           | idx_mv_biomass_pricing_id                          | CREATE UNIQUE INDEX idx_mv_biomass_pricing_id ON data_portal.mv_biomass_pricing USING btree (id)                                                               |
| data_portal | mv_biomass_sample_stats      | idx_mv_biomass_sample_stats_resource_id            | CREATE UNIQUE INDEX idx_mv_biomass_sample_stats_resource_id ON data_portal.mv_biomass_sample_stats USING btree (resource_id)                                   |
| data_portal | mv_biomass_search            | idx_mv_biomass_search_id                           | CREATE UNIQUE INDEX idx_mv_biomass_search_id ON data_portal.mv_biomass_search USING btree (id)                                                                 |
| data_portal | mv_biomass_volume_estimate   | idx_mv_biomass_volume_estimate_geoid               | CREATE INDEX idx_mv_biomass_volume_estimate_geoid ON data_portal.mv_biomass_volume_estimate USING btree (geoid)                                                |
| data_portal | mv_biomass_volume_estimate   | idx_mv_biomass_volume_estimate_id                  | CREATE UNIQUE INDEX idx_mv_biomass_volume_estimate_id ON data_portal.mv_biomass_volume_estimate USING btree (id)                                               |
| data_portal | mv_biomass_volume_estimate   | idx_mv_biomass_volume_estimate_resource_id         | CREATE INDEX idx_mv_biomass_volume_estimate_resource_id ON data_portal.mv_biomass_volume_estimate USING btree (resource_id)                                    |
| data_portal | mv_biomass_volume_estimate   | idx_mv_biomass_volume_estimate_resource_year       | CREATE INDEX idx_mv_biomass_volume_estimate_resource_year ON data_portal.mv_biomass_volume_estimate USING btree (resource_id, dataset_year)                    |
| data_portal | mv_usda_county_production    | idx_mv_usda_county_production_geoid                | CREATE INDEX idx_mv_usda_county_production_geoid ON data_portal.mv_usda_county_production USING btree (geoid)                                                  |
| data_portal | mv_usda_county_production    | idx_mv_usda_county_production_id                   | CREATE UNIQUE INDEX idx_mv_usda_county_production_id ON data_portal.mv_usda_county_production USING btree (id)                                                 |
| data_portal | mv_usda_county_production    | idx_mv_usda_county_production_resource_id          | CREATE INDEX idx_mv_usda_county_production_resource_id ON data_portal.mv_usda_county_production USING btree (resource_id)                                      |

---

## Module: pretreatment

### Result 1

| record_type  | total_records | qc_pass_count | qc_fail_count | qc_null_count | pass_pct |
| ------------ | ------------- | ------------- | ------------- | ------------- | -------- |
| pretreatment | 906           | 835           | 65            | 6             | 92.2     |

### Result 2

| record_type  | total_qc_non_fail | analyst_filled | analyst_pct | method_filled | method_pct | experiment_filled | experiment_pct | vessel_filled | temperature_filled | dataset_filled |
| ------------ | ----------------- | -------------- | ----------- | ------------- | ---------- | ----------------- | -------------- | ------------- | ------------------ | -------------- |
| pretreatment | 835               | 792            | 94.9        | 835           | 100.0      | 0                 | 0.0            | 835           | 0                  | 835            |

### Result 3

| record_type  | unique_prepared_samples | unique_resources | unique_experiments | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ------------ | ----------------------- | ---------------- | ------------------ | -------------------- | -------------------------- | --------------------- |
| pretreatment | 61                      | 28               | 0                  | 61                   | 13                         | 21.3                  |

### Result 4

| parameter   | obs_count | unit_count | units_used  | records_with_param | record_coverage_pct |
| ----------- | --------- | ---------- | ----------- | ------------------ | ------------------- |
| glucose_yld | 430       | 1          | % of glucan | 430                | 51.5                |
| xylose_yld  | 405       | 1          | % of xylan  | 405                | 48.5                |

---

## Module: proximate

### Result 1

| record_type | total_records | qc_pass_count | qc_fail_count | qc_null_count | pass_pct |
| ----------- | ------------- | ------------- | ------------- | ------------- | -------- |
| proximate   | 1339          | 1223          | 111           | 1             | 91.3     |

### Result 2

| record_type | total_qc_non_fail | analyst_filled | analyst_pct | method_filled | method_pct | raw_data_filled | raw_data_pct | experiment_filled | experiment_pct | dataset_filled | dataset_pct |
| ----------- | ----------------- | -------------- | ----------- | ------------- | ---------- | --------------- | ------------ | ----------------- | -------------- | -------------- | ----------- |
| proximate   | 1227              | 442            | 36.0        | 1227          | 100.0      | 0               | 0.0          | 0                 | 0.0            | 1227           | 100.0       |

### Result 3

| record_type | unique_prepared_samples | unique_resources | unique_experiments | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ----------- | ----------------------- | ---------------- | ------------------ | -------------------- | -------------------------- | --------------------- |
| proximate   | 97                      | 40               | 0                  | 86                   | 14                         | 14.4                  |

### Result 4

| parameter       | obs_count | unit_count | units_used     | records_with_param | record_coverage_pct |
| --------------- | --------- | ---------- | -------------- | ------------------ | ------------------- |
| total solids    | 318       | 1          | % total weight | 318                | 25.9                |
| ash             | 317       | 1          | % total weight | 317                | 25.8                |
| volatile solids | 316       | 1          | % total weight | 316                | 25.8                |
| moisture        | 276       | 1          | % total weight | 276                | 22.5                |

### Result 5

| parameter       | min_val | max_val | avg_val | median_val         | negative_values_count |
| --------------- | ------- | ------- | ------- | ------------------ | --------------------- |
| ash             | 0.03    | 72.31   | 6.5611  | 4.3                | 0                     |
| moisture        | 0.36    | 97.56   | 30.0870 | 14.275             | 0                     |
| total solids    | 2.44    | 99.73   | 70.9086 | 86.41              | 0                     |
| volatile solids | 1.54    | 98.62   | 50.8773 | 55.605000000000004 | 0                     |

---

## Module: ultimate

### Result 1

| record_type | total_records | qc_pass_count | qc_fail_count | qc_null_count | pass_pct |
| ----------- | ------------- | ------------- | ------------- | ------------- | -------- |
| ultimate    | 84            | 66            | 3             | 15            | 78.6     |

### Result 2

| record_type | total_qc_non_fail | analyst_filled | method_filled | raw_data_filled | experiment_filled | dataset_filled |
| ----------- | ----------------- | -------------- | ------------- | --------------- | ----------------- | -------------- |
| ultimate    | 66                | 0              | 66            | 2               | 0                 | 66             |

### Result 3

| record_type | unique_prepared_samples | unique_resources | unique_experiments | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ----------- | ----------------------- | ---------------- | ------------------ | -------------------- | -------------------------- | --------------------- |
| ultimate    | 14                      | 10               | 0                  | 12                   | 5                          | 35.7                  |

### Result 4

| parameter | obs_count | unit_count | units_used | records_with_param | record_coverage_pct |
| --------- | --------- | ---------- | ---------- | ------------------ | ------------------- |
| adf-r     | 17        | 1          | pc         | 17                 | 25.8                |
| cf        | 17        | 1          | pc         | 17                 | 25.8                |
| nitrogen  | 17        | 1          | pc         | 17                 | 25.8                |
| dm        | 14        | 1          | pc         | 14                 | 21.2                |
| sulfur    | 1         | 1          | pc         | 1                  | 1.5                 |

### Result 5

| parameter | min_val | max_val | avg_val  | negative_values_count |
| --------- | ------- | ------- | -------- | --------------------- |
| adf-r     | 12.1    | 82.9    | 44.4353  | 0                     |
| cf        | 0.5     | 10.0    | 4.1071   | 0                     |
| dm        | 81.3    | 97.3    | 91.2000  | 0                     |
| nitrogen  | 0.23    | 3.06    | 1.5659   | 0                     |
| sulfur    | 270.0   | 270.0   | 270.0000 | 0                     |

---

## Module: xrd

### Result 1

| record_type | total_records | qc_pass_count | qc_fail_count | qc_null_count |
| ----------- | ------------- | ------------- | ------------- | ------------- |
| xrd         | 28            | 27            | 0             | 1             |

### Result 2

| record_type | total_qc_non_fail | analyst_filled | method_filled | raw_data_filled | experiment_filled | dataset_filled |
| ----------- | ----------------- | -------------- | ------------- | --------------- | ----------------- | -------------- |
| xrd         | 27                | 27             | 27            | 0               | 0                 | 27             |

### Result 3

| record_type | unique_prepared_samples | unique_resources | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ----------- | ----------------------- | ---------------- | -------------------- | -------------------------- | --------------------- |
| xrd         | 10                      | 6                | 9                    | 2                          | 20.0                  |

### Result 4

| parameter     | obs_count | unit_count | units_used | records_with_param | record_coverage_pct |
| ------------- | --------- | ---------- | ---------- | ------------------ | ------------------- |
| crystallinity | 27        | 1          | %          | 27                 | 100.0               |

---

## Module: xrf

### Result 1

| record_type | total_records | qc_pass_count | qc_fail_count | qc_null_count |
| ----------- | ------------- | ------------- | ------------- | ------------- |
| xrf         | 390           | 0             | 0             | 0             |

### Result 2

| record_type | total_qc_non_fail | analyst_filled | method_filled | raw_data_filled | experiment_filled | dataset_filled |
| ----------- | ----------------- | -------------- | ------------- | --------------- | ----------------- | -------------- |
| xrf         | 390               | 390            | 390           | 1               | 0                 | 390            |

### Result 3

| record_type | unique_prepared_samples | unique_resources | unique_field_samples | unique_primary_ag_products | lineage_integrity_pct |
| ----------- | ----------------------- | ---------------- | -------------------- | -------------------------- | --------------------- |
| xrf         | 10                      | 8                | 10                   | 3                          | 30.0                  |

### Result 4

| parameter | obs_count | unit_count | units_used | records_with_param | record_coverage_pct |
| --------- | --------- | ---------- | ---------- | ------------------ | ------------------- |
| zn        | 10        | 1          | ppm        | 10                 | 2.6                 |
| u         | 10        | 1          | ppm        | 10                 | 2.6                 |
| th        | 10        | 1          | ppm        | 10                 | 2.6                 |
| ca        | 10        | 1          | ppm        | 10                 | 2.6                 |
| sr        | 10        | 1          | ppm        | 10                 | 2.6                 |
| cu        | 10        | 1          | ppm        | 10                 | 2.6                 |
| fe        | 10        | 1          | ppm        | 10                 | 2.6                 |
| k         | 10        | 1          | ppm        | 10                 | 2.6                 |
| si        | 10        | 1          | ppm        | 10                 | 2.6                 |
| s         | 9         | 1          | ppm        | 9                  | 2.3                 |
| mn        | 9         | 1          | ppm        | 9                  | 2.3                 |
| p         | 9         | 1          | ppm        | 9                  | 2.3                 |
| mo        | 7         | 1          | ppm        | 7                  | 1.8                 |
| al        | 6         | 1          | ppm        | 6                  | 1.5                 |
| rb        | 6         | 1          | ppm        | 6                  | 1.5                 |
| ti        | 6         | 1          | ppm        | 6                  | 1.5                 |
| nd        | 5         | 1          | ppm        | 5                  | 1.3                 |
| la        | 4         | 1          | ppm        | 4                  | 1.0                 |
| ce        | 4         | 1          | ppm        | 4                  | 1.0                 |
| pr        | 4         | 1          | ppm        | 4                  | 1.0                 |
| ba        | 4         | 1          | ppm        | 4                  | 1.0                 |
| zr        | 2         | 1          | ppm        | 2                  | 0.5                 |
| pb        | 2         | 1          | ppm        | 2                  | 0.5                 |
| ag        | 1         | 1          | ppm        | 1                  | 0.3                 |

---
