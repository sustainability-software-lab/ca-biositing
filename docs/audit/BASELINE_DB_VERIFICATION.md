# Baseline Database Verification Report (`biocirv_db`)

> [!IMPORTANT] **100% Programmatically Generated from Live PostgreSQL
> (`biocirv_db`)** Every SQL query and result table in this document was
> executed directly against
> `postgresql://biocirv_user:***@localhost:5432/biocirv_db` via
> `verify_live_db.py` at **`2026-10-16T19:14:11.441378+00:00`** and rendered
> directly from `verified_db_results.json` without manual editing.
>
> - **Zero Hardcoded Primary Key IDs Rule**: All integer primary key IDs
>   (`unit.id`, `parameter.id`, `resource.id`, `primary_ag_product.id`,
>   `carr_id`, `rpr_id`) shown in the tables below are **point-in-time
>   diagnostic snapshot values** from the current `biocirv_db` instance. Because
>   lookup tables are populated dynamically at ETL runtime via
>   [`name_id_swap.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/pipeline/ca_biositing/pipeline/utils/name_id_swap.py),
>   integer IDs can change whenever the database is rebuilt or refreshed. **No
>   SQL view, migration, or ETL transform may hardcode integer IDs—all joins and
>   filters must match on immutable `func.lower(name)`.**

---

## 1. Schema Inventory & Materialized Views (`public` & `data_portal`)

### 1.1 Tables & Views in `public` and `data_portal`

Note that **`public.calag_raw` does not exist** in `biocirv_db`. County Ag
Commissioner report data are stored in `public.county_ag_report_record` and
`public.observation` (`record_type = 'county_ag_report_record'`), while the
Almond NSJV historical sheet (`2017–2024`) is stored in
`public.resource_production_record` and `public.observation`
(`record_type = 'resource_production_record'`).

```sql
SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema IN ('public', 'data_portal')
        ORDER BY table_schema, table_name;
```

| table_schema | table_name                                       | table_type |
| ------------ | ------------------------------------------------ | ---------- |
| public       | ag_treatment                                     | BASE TABLE |
| public       | alembic_version                                  | BASE TABLE |
| public       | analysis_type                                    | BASE TABLE |
| public       | api_key                                          | BASE TABLE |
| public       | api_user                                         | BASE TABLE |
| public       | autoclave_record                                 | BASE TABLE |
| public       | billion_ton2023_record                           | BASE TABLE |
| public       | bioconversion_method                             | BASE TABLE |
| public       | calorimetry_record                               | BASE TABLE |
| public       | collection_method                                | BASE TABLE |
| public       | compositional_record                             | BASE TABLE |
| public       | contact                                          | BASE TABLE |
| public       | county_ag_report_record                          | BASE TABLE |
| public       | data_source                                      | BASE TABLE |
| public       | data_source_type                                 | BASE TABLE |
| public       | dataset                                          | BASE TABLE |
| public       | decon_vessel                                     | BASE TABLE |
| public       | dimension_type                                   | BASE TABLE |
| public       | entity_lineage                                   | BASE TABLE |
| public       | enz_hydr_method                                  | BASE TABLE |
| public       | equipment                                        | BASE TABLE |
| public       | etl_run                                          | BASE TABLE |
| public       | experiment                                       | BASE TABLE |
| public       | experiment_analysis                              | BASE TABLE |
| public       | experiment_equipment                             | BASE TABLE |
| public       | experiment_method                                | BASE TABLE |
| public       | experiment_prepared_sample                       | BASE TABLE |
| public       | facility_record                                  | BASE TABLE |
| public       | fermentation_record                              | BASE TABLE |
| public       | field_sample                                     | BASE TABLE |
| public       | field_sample_condition                           | BASE TABLE |
| public       | field_storage_method                             | BASE TABLE |
| public       | file_object_metadata                             | BASE TABLE |
| public       | ftnir_record                                     | BASE TABLE |
| public       | gasification_record                              | BASE TABLE |
| public       | gasification_timeseries                          | BASE TABLE |
| public       | geography_columns                                | VIEW       |
| public       | geometry_columns                                 | VIEW       |
| public       | harvest_method                                   | BASE TABLE |
| public       | icp_record                                       | BASE TABLE |
| public       | infrastructure_biodiesel_plants                  | BASE TABLE |
| public       | infrastructure_biosolids_facilities              | BASE TABLE |
| public       | infrastructure_cafo_manure_locations             | BASE TABLE |
| public       | infrastructure_combustion_plants                 | BASE TABLE |
| public       | infrastructure_district_energy_systems           | BASE TABLE |
| public       | infrastructure_ethanol_biorefineries             | BASE TABLE |
| public       | infrastructure_food_processing_facilities        | BASE TABLE |
| public       | infrastructure_landfills                         | BASE TABLE |
| public       | infrastructure_livestock_anaerobic_digesters     | BASE TABLE |
| public       | infrastructure_msw_to_energy_anaerobic_digesters | BASE TABLE |
| public       | infrastructure_petroleum_pipelines               | BASE TABLE |
| public       | infrastructure_saf_and_renewable_diesel_plants   | BASE TABLE |
| public       | infrastructure_wastewater_treatment_plants       | BASE TABLE |
| public       | landiq_record                                    | BASE TABLE |
| public       | landiq_resource_mapping                          | BASE TABLE |
| public       | lineage_group                                    | BASE TABLE |
| public       | location_address                                 | BASE TABLE |
| public       | location_resolution                              | BASE TABLE |
| public       | location_soil_type                               | BASE TABLE |
| public       | method                                           | BASE TABLE |
| public       | method_abbrev                                    | BASE TABLE |
| public       | method_assumption                                | BASE TABLE |
| public       | method_category                                  | BASE TABLE |
| public       | method_standard                                  | BASE TABLE |
| public       | multilinestring                                  | BASE TABLE |
| public       | observation                                      | BASE TABLE |
| public       | parameter                                        | BASE TABLE |
| public       | parameter_category                               | BASE TABLE |
| public       | parameter_category_parameter                     | BASE TABLE |
| public       | parameter_unit                                   | BASE TABLE |
| public       | physical_characteristic                          | BASE TABLE |
| public       | place                                            | BASE TABLE |
| public       | polygon                                          | BASE TABLE |
| public       | preparation_method                               | BASE TABLE |
| public       | preparation_method_abbreviation                  | BASE TABLE |
| public       | prepared_sample                                  | BASE TABLE |
| public       | pretreatment_record                              | BASE TABLE |
| public       | pretreatment_setup                               | BASE TABLE |
| public       | primary_ag_product                               | BASE TABLE |
| public       | processing_method                                | BASE TABLE |
| public       | provider                                         | BASE TABLE |
| public       | proximate_record                                 | BASE TABLE |
| public       | residue_factor                                   | BASE TABLE |
| public       | resource                                         | BASE TABLE |
| public       | resource_availability                            | BASE TABLE |
| public       | resource_class                                   | BASE TABLE |
| public       | resource_counterfactual                          | BASE TABLE |
| public       | resource_end_use_record                          | BASE TABLE |
| public       | resource_image                                   | BASE TABLE |
| public       | resource_morphology                              | BASE TABLE |
| public       | resource_price_record                            | BASE TABLE |
| public       | resource_production_record                       | BASE TABLE |
| public       | resource_storage_record                          | BASE TABLE |
| public       | resource_subclass                                | BASE TABLE |
| public       | resource_transport_record                        | BASE TABLE |
| public       | resource_usda_commodity_map                      | BASE TABLE |
| public       | rgb_record                                       | BASE TABLE |
| public       | soil_type                                        | BASE TABLE |
| public       | source_type                                      | BASE TABLE |
| public       | spatial_ref_sys                                  | BASE TABLE |
| public       | strain                                           | BASE TABLE |
| public       | technical_assumption                             | BASE TABLE |
| public       | ultimate_record                                  | BASE TABLE |
| public       | unit                                             | BASE TABLE |
| public       | usda_census_record                               | BASE TABLE |
| public       | usda_commodity                                   | BASE TABLE |
| public       | usda_domain                                      | BASE TABLE |
| public       | usda_market_record                               | BASE TABLE |
| public       | usda_market_report                               | BASE TABLE |
| public       | usda_statistic_category                          | BASE TABLE |
| public       | usda_survey_program                              | BASE TABLE |
| public       | usda_survey_record                               | BASE TABLE |
| public       | usda_term_map                                    | BASE TABLE |
| public       | use_case                                         | BASE TABLE |
| public       | xrd_record                                       | BASE TABLE |
| public       | xrf_record                                       | BASE TABLE |

_Total rows: 116_

### 1.2 Materialized Views in `data_portal`

```sql
SELECT schemaname, matviewname
        FROM pg_matviews
        WHERE schemaname = 'data_portal'
        ORDER BY matviewname;
```

| schemaname  | matviewname                  |
| ----------- | ---------------------------- |
| data_portal | mv_biomass_availability      |
| data_portal | mv_biomass_composition       |
| data_portal | mv_biomass_county_production |
| data_portal | mv_biomass_end_uses          |
| data_portal | mv_biomass_fermentation      |
| data_portal | mv_biomass_gasification      |
| data_portal | mv_biomass_pricing           |
| data_portal | mv_biomass_sample_stats      |
| data_portal | mv_biomass_search            |
| data_portal | mv_biomass_volume_estimate   |
| data_portal | mv_usda_county_production    |

_Total rows: 11_

### 1.3 Observation Record Types (`public.observation`)

```sql
SELECT record_type, COUNT(*) AS cnt, MIN(record_id) AS sample_min_id, MAX(record_id) AS sample_max_id
        FROM public.observation
        GROUP BY record_type
        ORDER BY record_type;
```

| record_type                | cnt   | sample_min_id      | sample_max_id          |
| -------------------------- | ----- | ------------------ | ---------------------- |
| compositional analysis     | 1044  | (03)1e07           | (ff)e3c5               |
| county_ag_report_record    | 235   | pc-002-merced-2023 | pc-136-stanislaus-2024 |
| fermentation               | 4023  | proc04-d2c4        | proco34-fee0           |
| gasification               | 797   | almo163-9eeb       | walnr81-fbdf           |
| icp analysis               | 826   | (03)0e23           | (fe)fe17               |
| pretreatment               | 884   | buty007-8d08       | no p842-d541           |
| proximate analysis         | 1347  | (03)00da           | (ff)fc00               |
| resource_end_use_record    | 137   | 1                  | 9                      |
| resource_price_record      | 73    | 1                  | 9                      |
| resource_production_record | 73    | 1                  | 9                      |
| ultimate analysis          | 72    | 7ud442d4           | )ufc42fc               |
| usda_census_record         | 19893 | 1                  | 999                    |
| usda_survey_record         | 30375 | 1                  | 999                    |
| xrd analysis               | 27    | (28)5879           | (e8)896d               |
| xrf analysis               | 2778  | (03)0161           | (f7)ffc2               |
| NULL                       | 102   | -                  | walnr82-6e08           |

_Total rows: 16_

---

## 2. Lookup Tables: `public.unit`, `public.parameter`, and `public.place`

### 2.1 `public.unit` (Verification of Hardcoded `_acreage_unit_id = 18` `'bushels'` Bug vs. Name-Based Join on `'acres'`)

In
[`mv_biomass_volume_estimate.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L42),
line 42 hardcodes `_acreage_unit_id = 18`. As shown in the snapshot below,
`id = 18` is **`bushels`**, whereas **`acres` is `id = 19`** (`id = 1` is
`tons`, `id = 2` is `week`). This hardcoded-ID bug (`18` instead of joining
`Unit` on `func.lower(Unit.name) == 'acres'`) causes both **Path B
(`census_based_volumes`, line 170)** and **Path D (`acreage_based_volumes`,
line 342)** to fail their `LEFT JOIN` against `public.observation` and return
`NULL` acreage and `NULL` residue volumes. **Remediation (Sub-Issue #1) deletes
`_acreage_unit_id` completely and replaces it with
`func.lower(Unit.name) == 'acres'`.**

```sql
SELECT id, name, description
        FROM public.unit
        ORDER BY id;
```

| id  | name                      | description                                 |
| --- | ------------------------- | ------------------------------------------- |
| 1   | tons                      | NULL                                        |
| 2   | week                      | NULL                                        |
| 3   | hours                     | NULL                                        |
| 4   | year                      | NULL                                        |
| 5   | weeks                     | NULL                                        |
| 6   | months                    | NULL                                        |
| 7   | days                      | NULL                                        |
| 8   | minutes                   | NULL                                        |
| 9   | hour                      | NULL                                        |
| 10  | core                      | NULL                                        |
| 11  | paper shopping bag        | NULL                                        |
| 12  | plastic bag (trash size)  | NULL                                        |
| 13  | bucket (2 gal.)           | NULL                                        |
| 14  | bale                      | NULL                                        |
| 15  | mesh sack                 | NULL                                        |
| 16  | bucket (5 gal.)           | NULL                                        |
| 17  | large paper bag (10 gal.) | NULL                                        |
| 18  | bushels                   | US bushels                                  |
| 19  | acres                     | US acres                                    |
| 20  | dollars                   | US dollars                                  |
| 21  | dollars per bushel        | US dollars per bushel                       |
| 22  | dollars per ton           | US dollars per ton                          |
| 23  | operations                | Number of farming operations/establishments |
| 24  | bu                        | US bushels (abbreviated)                    |
| 25  | $                         | US dollars (symbol)                         |
| 26  | lb                        | Pounds                                      |
| 27  | bu / acre                 | Bushels per acre (yield)                    |
| 28  | bu / net planted acre     | Bushels per net planted acre                |
| 29  | tons / acre               | Tons per acre (yield)                       |
| 30  | lb / acre                 | Pounds per acre (yield)                     |
| 31  | lb / net planted acre     | Pounds per net planted acre                 |
| 32  | bales                     | Cotton bales                                |
| 33  | 480 lb bales              | Cotton bales (480 lb standard)              |
| 34  | running bales             | Running bales (cotton)                      |
| 35  | lb / bale, avg            | Average pounds per bale                     |
| 36  | number                    | Count/number                                |
| 37  | cwt                       | Hundredweight (100 pounds)                  |
| 38  | sq ft                     | Square feet                                 |
| 39  | dollars per ton delivered | NULL                                        |
| 40  | multiplier                | NULL                                        |
| 41  | %                         | NULL                                        |
| 42  | % total weight            | NULL                                        |
| 43  | pc                        | NULL                                        |
| 44  | % dry weight              | NULL                                        |
| 45  | ppm                       | NULL                                        |
| 46  | mj/kg                     | NULL                                        |
| 47  | % of glucan               | NULL                                        |
| 48  | % of xylan                | NULL                                        |
| 49  | pc_g_g                    | NULL                                        |
| 50  | mol_pc                    | NULL                                        |
| 51  | g_l                       | NULL                                        |
| 52  | g                         | NULL                                        |
| 53  | psi                       | NULL                                        |
| 54  | min                       | NULL                                        |
| 55  | c                         | NULL                                        |
| 56  | mps                       | NULL                                        |

_Total rows: 56_

### 2.2 `public.parameter` (Verification of Hardcoded `_param_*_id` Constants)

In
[`mv_biomass_volume_estimate.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L40-L45),
lines 43–45 hardcode:

- `_param_bearing_id = 5` (`area bearing`)
- `_param_bnb_id = 7` (`area bearing & non-bearing`)
- `_param_harvested_id = 3` (`area harvested`)

Although these three IDs currently match `public.parameter` in the snapshot
below, **Sub-Issue #1 deletes `_param_bearing_id`, `_param_bnb_id`, and
`_param_harvested_id` completely and replaces them with
`func.lower(Parameter.name)` joins** so that parameter IDs can never drift on a
future database rebuild.

```sql
SELECT id, name, description
        FROM public.parameter
        ORDER BY id;
```

| id  | name                              | description                                                                                                                  |
| --- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1   | production                        | NULL                                                                                                                         |
| 2   | yield                             | Yield per unit area                                                                                                          |
| 3   | area harvested                    | Area harvested                                                                                                               |
| 4   | area planted                      | Area planted                                                                                                                 |
| 5   | area bearing                      | Area with bearing trees/vines (fruit/nut specific)                                                                           |
| 6   | area non-bearing                  | Area with non-bearing trees/vines (fruit/nut specific)                                                                       |
| 7   | area bearing & non-bearing        | Total area with bearing and non-bearing trees/vines                                                                          |
| 8   | operations                        | Number of farming operations/establishments                                                                                  |
| 9   | price received                    | Price received by farmer                                                                                                     |
| 10  | price paid                        | Price paid by farmer                                                                                                         |
| 11  | sales                             | Sales value or operations with sales                                                                                         |
| 12  | area planted, net                 | Net area planted                                                                                                             |
| 13  | active gins                       | Number of active cotton gins                                                                                                 |
| 14  | ginned bales                      | Cotton bales ginned                                                                                                          |
| 15  | area in production                | Area in production                                                                                                           |
| 16  | price production weighted avg     | average price across a region weighted by the share of resource production in constituent counties                           |
| 17  | price production weighted average | Price production weighted average                                                                                            |
| 18  | resource value high               | upper estimate of the financial value of a resource for a given use case. negative values indicate cost.                     |
| 19  | resource use perc high            | upper estimate of resource use as percent of total resource material stream                                                  |
| 20  | resource value low                | lower estimate of financial value of resource for a given use case. negative values indicate cost.                           |
| 21  | resource value multiplier high    | approximate increase in value relative to the primary product                                                                |
| 22  | resource use perc low             | lower estimate of resource use as percent of total resource material stream                                                  |
| 23  | resource value multiplier low     | approximate increase in value relative to the primary product                                                                |
| 24  | resource use trend                | trend of the resource use case (increasing, decreasing, steady) over time.                                                   |
| 25  | prim ag production                | tonnage of primary crop harvested                                                                                            |
| 26  | resource production               | tonnage of resource produced. calculated from production multiplied by residue factor.                                       |
| 27  | price avg                         | price in a given region by average of constituent county prices. not weighted by resource production fraction of the county. |
| 28  | moisture                          | NULL                                                                                                                         |
| 29  | total solids                      | NULL                                                                                                                         |
| 30  | volatile solids                   | NULL                                                                                                                         |
| 31  | ash                               | NULL                                                                                                                         |
| 32  | sulfur                            | NULL                                                                                                                         |
| 33  | cf                                | NULL                                                                                                                         |
| 34  | hydrogen                          | NULL                                                                                                                         |
| 35  | adf-r                             | NULL                                                                                                                         |
| 36  | carbon                            | NULL                                                                                                                         |
| 37  | oxygen                            | NULL                                                                                                                         |
| 38  | nitrogen                          | NULL                                                                                                                         |
| 39  | dm                                | NULL                                                                                                                         |
| 40  | xylan                             | NULL                                                                                                                         |
| 41  | lignin                            | NULL                                                                                                                         |
| 42  | glucan                            | NULL                                                                                                                         |
| 43  | glucose                           | NULL                                                                                                                         |
| 44  | xylose                            | NULL                                                                                                                         |
| 45  | arabinan                          | NULL                                                                                                                         |
| 46  | arabinose                         | NULL                                                                                                                         |
| 47  | lignin+                           | NULL                                                                                                                         |
| 48  | ca                                | NULL                                                                                                                         |
| 49  | si                                | NULL                                                                                                                         |
| 50  | p                                 | NULL                                                                                                                         |
| 51  | cu                                | NULL                                                                                                                         |
| 52  | fe                                | NULL                                                                                                                         |
| 53  | b                                 | NULL                                                                                                                         |
| 54  | al                                | NULL                                                                                                                         |
| 55  | mg                                | NULL                                                                                                                         |
| 56  | na                                | NULL                                                                                                                         |
| 57  | s                                 | NULL                                                                                                                         |
| 58  | ti                                | NULL                                                                                                                         |
| 59  | zn                                | NULL                                                                                                                         |
| 60  | mn                                | NULL                                                                                                                         |
| 61  | nd                                | NULL                                                                                                                         |
| 62  | k                                 | NULL                                                                                                                         |
| 63  | nb                                | NULL                                                                                                                         |
| 64  | cd                                | NULL                                                                                                                         |
| 65  | as                                | NULL                                                                                                                         |
| 66  | th                                | NULL                                                                                                                         |
| 67  | sn                                | NULL                                                                                                                         |
| 68  | co                                | NULL                                                                                                                         |
| 69  | rb                                | NULL                                                                                                                         |
| 70  | hg                                | NULL                                                                                                                         |
| 71  | bi                                | NULL                                                                                                                         |
| 72  | zr                                | NULL                                                                                                                         |
| 73  | u                                 | NULL                                                                                                                         |
| 74  | ag                                | NULL                                                                                                                         |
| 75  | w                                 | NULL                                                                                                                         |
| 76  | pr                                | NULL                                                                                                                         |
| 77  | mo                                | NULL                                                                                                                         |
| 78  | la                                | NULL                                                                                                                         |
| 79  | cr                                | NULL                                                                                                                         |
| 80  | y                                 | NULL                                                                                                                         |
| 81  | ba                                | NULL                                                                                                                         |
| 82  | sb                                | NULL                                                                                                                         |
| 83  | se                                | NULL                                                                                                                         |
| 84  | ni                                | NULL                                                                                                                         |
| 85  | v                                 | NULL                                                                                                                         |
| 86  | ce                                | NULL                                                                                                                         |
| 87  | pb                                | NULL                                                                                                                         |
| 88  | sr                                | NULL                                                                                                                         |
| 89  | crystallinity                     | NULL                                                                                                                         |
| 90  | glucose_yld                       | NULL                                                                                                                         |
| 91  | xylose_yld                        | NULL                                                                                                                         |
| 92  | xylconcteof                       | NULL                                                                                                                         |
| 93  | rel_growth                        | NULL                                                                                                                         |
| 94  | sugart0                           | NULL                                                                                                                         |
| 95  | sugar_cons                        | NULL                                                                                                                         |
| 96  | etohtiter                         | NULL                                                                                                                         |
| 97  | sugarteof                         | NULL                                                                                                                         |
| 98  | 3hpyield                          | NULL                                                                                                                         |
| 99  | od600teof                         | NULL                                                                                                                         |
| 100 | 3hptiter                          | NULL                                                                                                                         |
| 101 | gluconct0                         | NULL                                                                                                                         |
| 102 | gluconcteof                       | NULL                                                                                                                         |
| 103 | xylconct0                         | NULL                                                                                                                         |
| 104 | etohyield                         | NULL                                                                                                                         |
| 105 | ch4                               | NULL                                                                                                                         |
| 106 | co2                               | NULL                                                                                                                         |
| 107 | tar                               | NULL                                                                                                                         |
| 108 | c4h10(b)                          | NULL                                                                                                                         |
| 109 | pv                                | NULL                                                                                                                         |
| 110 | ufl                               | NULL                                                                                                                         |
| 111 | wme                               | NULL                                                                                                                         |
| 112 | c4h10(i)                          | NULL                                                                                                                         |
| 113 | bio                               | NULL                                                                                                                         |
| 114 | c2h6                              | NULL                                                                                                                         |
| 115 | comb                              | NULL                                                                                                                         |
| 116 | o2                                | NULL                                                                                                                         |
| 117 | c5h12                             | NULL                                                                                                                         |
| 118 | char                              | NULL                                                                                                                         |
| 119 | lfl                               | NULL                                                                                                                         |
| 120 | time                              | NULL                                                                                                                         |
| 121 | unc-bio                           | NULL                                                                                                                         |
| 122 | n2                                | NULL                                                                                                                         |
| 123 | c6h14                             | NULL                                                                                                                         |
| 124 | pi                                | NULL                                                                                                                         |
| 125 | h2                                | NULL                                                                                                                         |
| 126 | ta                                | NULL                                                                                                                         |
| 127 | va                                | NULL                                                                                                                         |
| 128 | combfrac                          | NULL                                                                                                                         |
| 129 | c3h8                              | NULL                                                                                                                         |

_Total rows: 129_

### 2.3 `public.place` (Verification of Zero Duplicate `geoid`s or County Names)

All five `Place` joins in
[`mv_biomass_volume_estimate.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py)
join on **`geoid` equality**:

- Line 79 (Path A): `.join(Place, CountyAgReportRecord.geoid == Place.geoid)`
- Line 166 (Path B): `.join(Place, UsdaCensusRecord.geoid == Place.geoid)`
- Line 247 (Path C): `.join(Place, CountyAgReportRecord.geoid == Place.geoid)`
- Line 338 (Path D): `.join(Place, UsdaCensusRecord.geoid == Place.geoid)`
- Line 398 (Path E): `.join(Place, UsdaCensusRecord.geoid == Place.geoid)`

As verified below, `public.place` has **exactly 1 row** for each NSJV county
(`06047` `'merced'`, `06077` `'san joaquin'`, `06099` `'stanislaus'`), zero
duplicate `geoid`s, and zero duplicate non-null `county_name` values (the only 2
rows with `county_name IS NULL` are state/regional placeholders
`geoid = '06000'` and `geoid = 'NSJV'`).

```sql
SELECT geoid, state_name, county_name, county_fips, region_name, agg_level_desc
        FROM public.place
        WHERE geoid IN ('06047', '06077', '06099')
           OR lower(county_name) IN ('merced', 'san joaquin', 'stanislaus')
        ORDER BY geoid;
```

| geoid | state_name | county_name | county_fips | region_name              | agg_level_desc |
| ----- | ---------- | ----------- | ----------- | ------------------------ | -------------- |
| 06047 | california | merced      | 047         | north san joaquin valley | county         |
| 06077 | california | san joaquin | 077         | north san joaquin valley | county         |
| 06099 | california | stanislaus  | 099         | north san joaquin valley | county         |

_Total rows: 3_

```sql
SELECT county_name, COUNT(*) AS cnt
        FROM public.place
        GROUP BY county_name
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC;
```

| county_name | cnt |
| ----------- | --- |
| NULL        | 2   |

_Total rows: 1_

```sql
SELECT geoid, state_name, county_name, county_fips, region_name, agg_level_desc
        FROM public.place
        WHERE county_name IS NULL
        ORDER BY geoid;
```

| geoid | state_name | county_name | county_fips | region_name | agg_level_desc  |
| ----- | ---------- | ----------- | ----------- | ----------- | --------------- |
| 06000 | NULL       | NULL        | 000         | NULL        | NULL            |
| NSJV  | california | NULL        | NULL        | NULL        | IN-STATE REGION |

_Total rows: 2_

```sql
SELECT geoid, COUNT(*) AS cnt
        FROM public.place
        GROUP BY geoid
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC;
```

_0 rows returned._

---

## 3. `public.primary_ag_product` Granularity & Commodity Splits

The table below shows every row in `public.primary_ag_product`, the count of
`public.resource` rows linked to it (`linked_resources`), and the count of
`public.county_ag_report_record` rows (`carr_records`).

Key findings for downstream remediation:

1. **Corn (`id = 16` `'corn - all'` vs. `id = 45` `'corn - grain'` vs. `id = 56`
   `'silage - corn'`)**:
   - The 4 corn stover resources (`id = 12, 21, 26, 33`) are currently linked to
     `primary_ag_product_id = 16` (`'corn - all'`), which has **`0` rows** in
     `county_ag_report_record`. Because Path A produces 0 rows for
     `id = 12, 21, 26, 33`, the anti-join in Path E (`~Resource.id.in_(...)` at
     lines 408–412) routes them to USDA Census `CORN` (`commodity_code = 6`),
     where the only `production` observation in `tons` (`unit_id = 1`) is **wet
     corn silage** (`4,517,173.0 t` in 2017; `5,216,315.0 t` in 2022).
   - Meanwhile, **`primary_ag_product_id = 45` (`'corn - grain'`) already
     exists** and has **`4` rows** in `public.county_ag_report_record`
     (`Merced 2023 = 19,243.0 t`, `San Joaquin 2023 = 87,000.0 t`,
     `Merced 2024 = 21,305.0 t`, `San Joaquin 2024 = 101,000.0 t`), distinct
     from `id = 56` (`'silage - corn'`, 6 rows) and `id = 42` (`'corn - sweet'`,
     2 rows). Repointing `Resource.primary_ag_product_id` for
     `id = 12, 21, 26, 33` from `16` (`'corn - all'`) to **`45`
     (`'corn - grain'`)** routes corn stover directly through **Path A** on
     grain corn tonnage and automatically excludes it from Path E's silage bug.
2. **Tomatoes (`id = 29` `'tomatoes for processing'` vs. `id = 67`
   `'tomatoes for market'`)**:
   - This split **already exists** in `public.primary_ag_product`, and
     `tomato pomace` (`resource_id = 19`) is already linked exclusively to
     `id = 29` (`'tomatoes for processing'`, 6 rows in
     `county_ag_report_record`).
3. **Grapes (`id = 23` `'grapes'`) and Peaches (`id = 12` `'peaches'`)**:
   - `public.primary_ag_product` has only a single undifferentiated `'grapes'`
     row (`id = 23`, 10 linked resources, 6 `county_ag_report_record` rows) and
     a single active `'peaches'` row (`id = 12`, 8 linked resources, 6
     `county_ag_report_record` rows; `id = 78` `'peaches/nectarines'` has 0
     records). There is **no** wine vs. table/raisin grape split or clingstone
     vs. freestone peach split in `public.primary_ag_product`.

```sql
SELECT
            pap.id,
            pap.name,
            COUNT(DISTINCT r.id) AS linked_resources,
            COUNT(DISTINCT carr.id) AS carr_records
        FROM public.primary_ag_product pap
        LEFT JOIN public.resource r ON r.primary_ag_product_id = pap.id
        LEFT JOIN public.county_ag_report_record carr ON carr.primary_ag_product_id = pap.id
        GROUP BY pap.id, pap.name
        ORDER BY pap.id;
```

| id  | name                                   | linked_resources | carr_records |
| --- | -------------------------------------- | ---------------- | ------------ |
| 1   | rice                                   | 2                | 2            |
| 2   | almonds                                | 7                | 0            |
| 3   | hay - alfalfa                          | 1                | 6            |
| 4   | melons - watermelon                    | 1                | 2            |
| 5   | sargassum                              | 1                | 0            |
| 6   | walnuts                                | 7                | 6            |
| 7   | plums & prunes                         | 7                | 2            |
| 8   | pistachios                             | 3                | 6            |
| 9   | sweet potatoes                         | 1                | 4            |
| 10  | cucumbers and pickles                  | 1                | 2            |
| 11  | oranges                                | 2                | 0            |
| 12  | peaches                                | 8                | 6            |
| 13  | plum-apricot hybrids                   | 7                | 0            |
| 14  | manure                                 | 1                | 6            |
| 15  | pears                                  | 7                | 2            |
| 16  | corn - all                             | 4                | 0            |
| 17  | nectarines                             | 7                | 0            |
| 18  | woody biomass                          | 1                | 6            |
| 19  | potatoes                               | 4                | 0            |
| 20  | olives - processing                    | 3                | 4            |
| 21  | dairy - other not elsewhere classified | 2                | 0            |
| 22  | cherries                               | 2                | 4            |
| 23  | grapes                                 | 10               | 6            |
| 24  | municipal solid waste paper rich       | 1                | 0            |
| 25  | winter wheat                           | 2                | 4            |
| 26  | cotton                                 | 1                | 1            |
| 27  | apricots                               | 7                | 4            |
| 28  | compost overs                          | 1                | 0            |
| 29  | tomatoes for processing                | 1                | 6            |
| 30  | silage - sorghum                       | 0                | 2            |
| 31  | silage - triticale                     | 0                | 2            |
| 32  | safflower                              | 0                | 2            |
| 33  | hogs & pigs                            | 0                | 2            |
| 34  | cattle - all                           | 0                | 6            |
| 35  | almond meats                           | 0                | 6            |
| 36  | eggs - hens                            | 0                | 6            |
| 37  | almond shells                          | 0                | 6            |
| 38  | onions                                 | 0                | 2            |
| 39  | silage - other                         | 0                | 6            |
| 40  | melons - other                         | 0                | 6            |
| 41  | blueberries                            | 0                | 2            |
| 42  | corn - sweet                           | 0                | 2            |
| 43  | silage - sudangrass                    | 0                | 2            |
| 44  | garlic                                 | 0                | 2            |
| 45  | corn - grain                           | 0                | 4            |
| 46  | cotton - acala                         | 0                | 1            |
| 47  | apples                                 | 0                | 2            |
| 48  | silage - alfalfa                       | 0                | 2            |
| 49  | barley                                 | 0                | 1            |
| 50  | beans - other                          | 0                | 4            |
| 51  | melons - cantaloupe                    | 0                | 2            |
| 52  | broccoli                               | 0                | 1            |
| 53  | pumpkins                               | 0                | 4            |
| 54  | sheep & lambs                          | 0                | 6            |
| 55  | goats                                  | 0                | 3            |
| 56  | silage - corn                          | 0                | 6            |
| 57  | beans - lima                           | 0                | 4            |
| 58  | cotton - pima                          | 0                | 1            |
| 59  | livestock -- miscellaneous             | 0                | 2            |
| 60  | peppers                                | 0                | 2            |
| 61  | turkeys                                | 0                | 4            |
| 62  | squash                                 | 0                | 2            |
| 63  | wool                                   | 0                | 5            |
| 64  | milk - goat's                          | 0                | 2            |
| 65  | hay - other                            | 0                | 6            |
| 66  | silage - oat                           | 0                | 2            |
| 67  | tomatoes for market                    | 0                | 4            |
| 68  | poultry                                | 0                | 2            |
| 69  | silage - wheat                         | 0                | 2            |
| 70  | straw                                  | 0                | 2            |
| 71  | almond hulls                           | 0                | 6            |
| 72  | chickens                               | 0                | 6            |
| 73  | milk - cow's                           | 0                | 6            |
| 74  | cotton - seed (unginned)               | 0                | 2            |
| 75  | honey                                  | 0                | 6            |
| 76  | miscellaneous deciduous                | 0                | 0            |
| 77  | alfalfa & mixtures                     | 0                | 0            |
| 78  | peaches/nectarines                     | 0                | 0            |
| 79  | plums                                  | 0                | 0            |
| 80  | no match                               | 0                | 0            |
| 81  | corn, sorghum                          | 0                | 0            |
| 82  | melons/squash                          | 0                | 0            |
| 83  | olives                                 | 0                | 0            |
| 84  | wheat                                  | 0                | 0            |

_Total rows: 84_

---

## 4. Forensics of `public.county_ag_report_record` vs. `public.resource_production_record`

### 4.1 `public.county_ag_report_record` Schema & Almond Hull/Shell/Meat Comparison (Used by Path C)

Path C (`commodity_direct_volumes`, lines 220–268 of
[`mv_biomass_volume_estimate.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L220-L268))
queries `public.county_ag_report_record` joined to `public.primary_ag_product`
(`func.lower(PrimaryAgProduct.name) == func.lower(Resource.name)`), which
matches `almond shells` (`resource_id = 5`, `pap_id = 37`) and `almond hulls`
(`resource_id = 32`, `pap_id = 71`).

In **3 of the 6 county-year records** (`san joaquin 2023`, `stanislaus 2023`,
and `stanislaus 2024`), `almond_shells_tons` (`pap_id = 37`, `pc-132`) is
**numerically identical (`1.000×`) to `almond_meats_tons`** (`pap_id = 35`,
`pc-131`), whereas in the other 3 county-year records (`merced 2023 = 0.840×`,
`merced 2024 = 0.611×`, `san joaquin 2024 = 0.609×`) it reflects actual shell
tonnage:

```sql
SELECT
            p.county_name,
            carr.geoid,
            carr.data_year,
            MAX(CASE WHEN lower(pap.name) = 'almond meats' AND param.name = 'production' THEN obs.value END) AS almond_meats_tons,
            MAX(CASE WHEN lower(pap.name) = 'almond shells' AND param.name = 'production' THEN obs.value END) AS almond_shells_tons,
            MAX(CASE WHEN lower(pap.name) = 'almond hulls' AND param.name = 'production' THEN obs.value END) AS almond_hulls_tons,
            MAX(CASE WHEN lower(pap.name) = 'almond meats' AND param.name = 'harvested acres' THEN obs.value END) AS almond_meats_acres
        FROM public.county_ag_report_record carr
        JOIN public.primary_ag_product pap ON carr.primary_ag_product_id = pap.id
        JOIN public.place p ON carr.geoid = p.geoid
        JOIN public.observation obs ON obs.record_id = carr.record_id AND obs.record_type = 'county_ag_report_record'
        JOIN public.parameter param ON obs.parameter_id = param.id
        WHERE lower(pap.name) IN ('almond meats', 'almond shells', 'almond hulls')
        GROUP BY p.county_name, carr.geoid, carr.data_year
        ORDER BY p.county_name, carr.data_year;
```

| county_name | geoid | data_year | almond_meats_tons | almond_shells_tons | almond_hulls_tons | almond_meats_acres |
| ----------- | ----- | --------- | ----------------- | ------------------ | ----------------- | ------------------ |
| merced      | 06047 | 2023      | 143,774.0         | 120,743.0          | 318,554.0         | NULL               |
| merced      | 06047 | 2024      | 149,234.0         | 91,194.0           | 279,484.0         | NULL               |
| san joaquin | 06077 | 2023      | 110,200.0         | 110,200.0          | 220,000.0         | NULL               |
| san joaquin | 06077 | 2024      | 111,900.0         | 68,100.0           | 243,000.0         | NULL               |
| stanislaus  | 06099 | 2023      | 235,431.0         | 235,431.0          | 470,862.0         | NULL               |
| stanislaus  | 06099 | 2024      | 241,260.0         | 241,260.0          | 453,570.0         | NULL               |

_Total rows: 6_

### 4.2 Complete `public.county_ag_report_record` Production & Notes Table

```sql
SELECT
            carr.id AS carr_id,
            carr.record_id,
            carr.geoid,
            p.county_name,
            carr.data_year,
            carr.primary_ag_product_id AS pap_id,
            pap.name AS pap_name,
            carr.description,
            carr.resource_type,
            carr.note,
            carr.prodn_value_note,
            MAX(CASE WHEN param.name = 'production' THEN obs.value END) AS prod_tons,
            MAX(CASE WHEN param.name = 'value' THEN obs.value END) AS value_m
        FROM public.county_ag_report_record carr
        LEFT JOIN public.primary_ag_product pap ON carr.primary_ag_product_id = pap.id
        LEFT JOIN public.place p ON carr.geoid = p.geoid
        LEFT JOIN public.observation obs ON obs.record_id = carr.record_id AND obs.record_type = 'county_ag_report_record'
        LEFT JOIN public.parameter param ON obs.parameter_id = param.id
        GROUP BY carr.id, carr.record_id, carr.geoid, p.county_name, carr.data_year,
                 carr.primary_ag_product_id, pap.name, carr.description, carr.resource_type, carr.note, carr.prodn_value_note
        ORDER BY carr.primary_ag_product_id, carr.geoid, carr.data_year;
```

| carr_id | record_id              | geoid | county_name | data_year | pap_id | pap_name                   | description                              | resource_type      | note                                                                                                    | prodn_value_note                                                                                                                                                                                                                                         | prod_tons     | value_m |
| ------- | ---------------------- | ----- | ----------- | --------- | ------ | -------------------------- | ---------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------- |
| 159     | pc-015-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 1      | rice                       | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 55,800.0      | NULL    |
| 160     | pc-015-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 1      | rice                       | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 58,600.0      | NULL    |
| 83      | pc-010-merced-2023     | 06047 | merced      | 2023      | 3      | hay - alfalfa              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 269,724.0     | NULL    |
| 86      | pc-010-merced-2024     | 06047 | merced      | 2024      | 3      | hay - alfalfa              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 240,183.0     | NULL    |
| 84      | pc-010-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 3      | hay - alfalfa              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 213,000.0     | NULL    |
| 87      | pc-010-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 3      | hay - alfalfa              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 204,000.0     | NULL    |
| 85      | pc-010-stanislaus-2023 | 06099 | stanislaus  | 2023      | 3      | hay - alfalfa              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 87,231.0      | NULL    |
| 88      | pc-010-stanislaus-2024 | 06099 | stanislaus  | 2024      | 3      | hay - alfalfa              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 76,846.0      | NULL    |
| 119     | pc-134-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 4      | melons - watermelon        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 60,800.0      | NULL    |
| 120     | pc-134-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 4      | melons - watermelon        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 43,900.0      | NULL    |
| 215     | pc-004-merced-2023     | 06047 | merced      | 2023      | 6      | walnuts                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 15,984.0      | NULL    |
| 218     | pc-004-merced-2024     | 06047 | merced      | 2024      | 6      | walnuts                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 15,315.0      | NULL    |
| 216     | pc-004-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 6      | walnuts                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 160,000.0     | NULL    |
| 219     | pc-004-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 6      | walnuts                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 111,000.0     | NULL    |
| 217     | pc-004-stanislaus-2023 | 06099 | stanislaus  | 2023      | 6      | walnuts                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 66,334.0      | NULL    |
| 220     | pc-004-stanislaus-2024 | 06099 | stanislaus  | 2024      | 6      | walnuts                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 56,009.0      | NULL    |
| 151     | pc-067-merced-2023     | 06047 | merced      | 2023      | 7      | plums & prunes             | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 3,874.0       | NULL    |
| 152     | pc-067-merced-2024     | 06047 | merced      | 2024      | 7      | plums & prunes             | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,230.0       | NULL    |
| 145     | pc-003-merced-2023     | 06047 | merced      | 2023      | 8      | pistachios                 | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 30,177.0      | NULL    |
| 148     | pc-003-merced-2024     | 06047 | merced      | 2024      | 8      | pistachios                 | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 26,057.0      | NULL    |
| 146     | pc-003-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 8      | pistachios                 | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 3,700.0       | NULL    |
| 149     | pc-003-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 8      | pistachios                 | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,230.0       | NULL    |
| 147     | pc-003-stanislaus-2023 | 06099 | stanislaus  | 2023      | 8      | pistachios                 | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,870.0       | NULL    |
| 150     | pc-003-stanislaus-2024 | 06099 | stanislaus  | 2024      | 8      | pistachios                 | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,924.0       | NULL    |
| 197     | pc-011-merced-2023     | 06047 | merced      | 2023      | 9      | sweet potatoes             | NULL                                     | crop               | NULL                                                                                                    | ds001: quantity given in 40-lb cartons, converted to tons.                                                                                                                                                                                               | 298,013.0     | NULL    |
| 199     | pc-011-merced-2024     | 06047 | merced      | 2024      | 9      | sweet potatoes             | NULL                                     | crop               | NULL                                                                                                    | ds005: quantity given in 40-lb cartons, converted to tons.                                                                                                                                                                                               | 227,600.0     | NULL    |
| 198     | pc-011-stanislaus-2023 | 06099 | stanislaus  | 2023      | 9      | sweet potatoes             | NULL                                     | crop               | NULL                                                                                                    | ds001: quantity given in 40-lb cartons, converted to tons.                                                                                                                                                                                               | 34,541.0      | NULL    |
| 200     | pc-011-stanislaus-2024 | 06099 | stanislaus  | 2024      | 9      | sweet potatoes             | NULL                                     | crop               | NULL                                                                                                    | ds005: quantity given in 40-lb cartons, converted to tons.                                                                                                                                                                                               | 31,774.0      | NULL    |
| 64      | pc-042-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 10     | cucumbers and pickles      | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 26,600.0      | NULL    |
| 65      | pc-042-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 10     | cucumbers and pickles      | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 27,100.0      | NULL    |
| 135     | pc-017-merced-2023     | 06047 | merced      | 2023      | 12     | peaches                    | NULL                                     | crop               | NULL                                                                                                    | ds003: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 49,061.0      | NULL    |
| 138     | pc-017-merced-2024     | 06047 | merced      | 2024      | 12     | peaches                    | NULL                                     | crop               | NULL                                                                                                    | ds007: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 54,916.0      | NULL    |
| 136     | pc-017-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 12     | peaches                    | NULL                                     | crop               | NULL                                                                                                    | ds003: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 25,300.0      | NULL    |
| 139     | pc-017-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 12     | peaches                    | NULL                                     | crop               | NULL                                                                                                    | ds007: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 24,000.0      | NULL    |
| 137     | pc-017-stanislaus-2023 | 06099 | stanislaus  | 2023      | 12     | peaches                    | NULL                                     | crop               | NULL                                                                                                    | ds003: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 58,868.0      | NULL    |
| 140     | pc-017-stanislaus-2024 | 06099 | stanislaus  | 2024      | 12     | peaches                    | NULL                                     | crop               | NULL                                                                                                    | ds007: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 38,002.0      | NULL    |
| 105     | pc-108-merced-2023     | 06047 | merced      | 2023      | 14     | manure                     | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 1,774,095.0   | NULL    |
| 108     | pc-108-merced-2024     | 06047 | merced      | 2024      | 14     | manure                     | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 1,775,849.0   | NULL    |
| 106     | pc-108-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 14     | manure                     | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 241,000.0     | NULL    |
| 109     | pc-108-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 14     | manure                     | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 329,000.0     | NULL    |
| 107     | pc-108-stanislaus-2023 | 06099 | stanislaus  | 2023      | 14     | manure                     | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 530,526.0     | NULL    |
| 110     | pc-108-stanislaus-2024 | 06099 | stanislaus  | 2024      | 14     | manure                     | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 465,697.0     | NULL    |
| 141     | pc-061-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 15     | pears                      | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 1,140.0       | NULL    |
| 142     | pc-061-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 15     | pears                      | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 1,060.0       | NULL    |
| 225     | pc-089-merced-2023     | 06047 | merced      | 2023      | 18     | woody biomass              | NULL                                     | orchard by-product | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 26,524.0      | NULL    |
| 228     | pc-089-merced-2024     | 06047 | merced      | 2024      | 18     | woody biomass              | NULL                                     | orchard by-product | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 28,106.0      | NULL    |
| 226     | pc-089-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 18     | woody biomass              | NULL                                     | orchard by-product | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 77,000.0      | NULL    |
| 229     | pc-089-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 18     | woody biomass              | NULL                                     | orchard by-product | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 53,920.0      | NULL    |
| 227     | pc-089-stanislaus-2023 | 06099 | stanislaus  | 2023      | 18     | woody biomass              | NULL                                     | orchard by-product | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 43,943.0      | NULL    |
| 230     | pc-089-stanislaus-2024 | 06099 | stanislaus  | 2024      | 18     | woody biomass              | NULL                                     | orchard by-product | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 44,990.0      | NULL    |
| 129     | pc-014-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 20     | olives - processing        | NULL                                     | crop               | olives for processing into olive oil etc.                                                               | NULL                                                                                                                                                                                                                                                     | 10,000.0      | NULL    |
| 131     | pc-014-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 20     | olives - processing        | NULL                                     | crop               | olives for processing into olive oil etc.                                                               | NULL                                                                                                                                                                                                                                                     | 19,400.0      | NULL    |
| 130     | pc-014-stanislaus-2023 | 06099 | stanislaus  | 2023      | 20     | olives - processing        | NULL                                     | crop               | olives for processing into olive oil etc.                                                               | NULL                                                                                                                                                                                                                                                     | 5,170.0       | NULL    |
| 132     | pc-014-stanislaus-2024 | 06099 | stanislaus  | 2024      | 20     | olives - processing        | NULL                                     | crop               | olives for processing into olive oil etc.                                                               | NULL                                                                                                                                                                                                                                                     | 8,835.0       | NULL    |
| 43      | pc-016-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 22     | cherries                   | NULL                                     | crop               | NULL                                                                                                    | ds003: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 54,500.0      | NULL    |
| 45      | pc-016-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 22     | cherries                   | NULL                                     | crop               | NULL                                                                                                    | ds007: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 51,400.0      | NULL    |
| 44      | pc-016-stanislaus-2023 | 06099 | stanislaus  | 2023      | 22     | cherries                   | NULL                                     | crop               | NULL                                                                                                    | ds003: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 11,665.0      | NULL    |
| 46      | pc-016-stanislaus-2024 | 06099 | stanislaus  | 2024      | 22     | cherries                   | NULL                                     | crop               | NULL                                                                                                    | ds007: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 10,314.0      | NULL    |
| 77      | pc-005-merced-2023     | 06047 | merced      | 2023      | 23     | grapes                     | NULL                                     | crop               | NULL                                                                                                    | ds003: divided into red and white grapes.                                                                                                                                                                                                                | 167,718.0     | NULL    |
| 80      | pc-005-merced-2024     | 06047 | merced      | 2024      | 23     | grapes                     | NULL                                     | crop               | NULL                                                                                                    | ds007: divided into red and white grapes.                                                                                                                                                                                                                | 156,618.0     | NULL    |
| 78      | pc-005-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 23     | grapes                     | NULL                                     | crop               | NULL                                                                                                    | ds003: divided into red and white grapes.                                                                                                                                                                                                                | 640,000.0     | NULL    |
| 81      | pc-005-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 23     | grapes                     | NULL                                     | crop               | NULL                                                                                                    | ds007: divided into red and white grapes.                                                                                                                                                                                                                | 535,000.0     | NULL    |
| 79      | pc-005-stanislaus-2023 | 06099 | stanislaus  | 2023      | 23     | grapes                     | NULL                                     | crop               | NULL                                                                                                    | ds003: divided into red and white grapes.                                                                                                                                                                                                                | 69,062.0      | NULL    |
| 82      | pc-005-stanislaus-2024 | 06099 | stanislaus  | 2024      | 23     | grapes                     | NULL                                     | crop               | NULL                                                                                                    | ds007: divided into red and white grapes.                                                                                                                                                                                                                | 65,528.0      | NULL    |
| 221     | pc-002-merced-2023     | 06047 | merced      | 2023      | 25     | winter wheat               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 31,247.0      | NULL    |
| 223     | pc-002-merced-2024     | 06047 | merced      | 2024      | 25     | winter wheat               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 19,718.0      | NULL    |
| 222     | pc-002-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 25     | winter wheat               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 48,200.0      | NULL    |
| 224     | pc-002-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 25     | winter wheat               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 49,700.0      | NULL    |
| 59      | pc-008-merced-2024     | 06047 | merced      | 2024      | 26     | cotton                     | NULL                                     | crop               | any part of cotton plant, not differentiated into unginned or ginned cotton.                            | ds005: includes all varieties.                                                                                                                                                                                                                           | 26,225.0      | NULL    |
| 21      | pc-018-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 27     | apricots                   | NULL                                     | crop               | NULL                                                                                                    | ds003: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 3,050.0       | NULL    |
| 23      | pc-018-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 27     | apricots                   | NULL                                     | crop               | NULL                                                                                                    | ds007: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 4,470.0       | NULL    |
| 22      | pc-018-stanislaus-2023 | 06099 | stanislaus  | 2023      | 27     | apricots                   | NULL                                     | crop               | NULL                                                                                                    | ds003: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 10,194.0      | NULL    |
| 24      | pc-018-stanislaus-2024 | 06099 | stanislaus  | 2024      | 27     | apricots                   | NULL                                     | crop               | NULL                                                                                                    | ds007: quantity not given so inferred from acreage and san joaquin production.                                                                                                                                                                           | 16,238.0      | NULL    |
| 205     | pc-006-merced-2023     | 06047 | merced      | 2023      | 29     | tomatoes for processing    | NULL                                     | crop               | NULL                                                                                                    | ds003: "tomatoes - all" assumed to be mostly processing tomatoes. quantity not given, so inferred from acreage (merced).                                                                                                                                 | 1,439,519.0   | NULL    |
| 208     | pc-006-merced-2024     | 06047 | merced      | 2024      | 29     | tomatoes for processing    | NULL                                     | crop               | NULL                                                                                                    | ds007: "tomatoes - all" assumed to be mostly processing tomatoes. quantity not given, so inferred from acreage (merced).                                                                                                                                 | 1,027,270.0   | NULL    |
| 206     | pc-006-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 29     | tomatoes for processing    | NULL                                     | crop               | NULL                                                                                                    | ds003: "tomatoes - all" assumed to be mostly processing tomatoes. quantity not given, so inferred from acreage (merced).                                                                                                                                 | 866,000.0     | NULL    |
| 209     | pc-006-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 29     | tomatoes for processing    | NULL                                     | crop               | NULL                                                                                                    | ds007: "tomatoes - all" assumed to be mostly processing tomatoes. quantity not given, so inferred from acreage (merced).                                                                                                                                 | 800,000.0     | NULL    |
| 207     | pc-006-stanislaus-2023 | 06099 | stanislaus  | 2023      | 29     | tomatoes for processing    | NULL                                     | crop               | NULL                                                                                                    | ds003: "tomatoes - all" assumed to be mostly processing tomatoes. quantity not given, so inferred from acreage (merced).                                                                                                                                 | 611,510.0     | NULL    |
| 210     | pc-006-stanislaus-2024 | 06099 | stanislaus  | 2024      | 29     | tomatoes for processing    | NULL                                     | crop               | NULL                                                                                                    | ds007: "tomatoes - all" assumed to be mostly processing tomatoes. quantity not given, so inferred from acreage (merced).                                                                                                                                 | 443,685.0     | NULL    |
| 185     | pc-125-stanislaus-2023 | 06099 | stanislaus  | 2023      | 30     | silage - sorghum           | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 44,053.0      | NULL    |
| 186     | pc-125-stanislaus-2024 | 06099 | stanislaus  | 2024      | 30     | silage - sorghum           | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 44,686.0      | NULL    |
| 189     | pc-127-stanislaus-2023 | 06099 | stanislaus  | 2023      | 31     | silage - triticale         | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 48,284.0      | NULL    |
| 190     | pc-127-stanislaus-2024 | 06099 | stanislaus  | 2024      | 31     | silage - triticale         | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 44,025.0      | NULL    |
| 161     | pc-019-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 32     | safflower                  | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 3,970.0       | NULL    |
| 162     | pc-019-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 32     | safflower                  | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,000.0       | NULL    |
| 95      | pc-094-stanislaus-2023 | 06099 | stanislaus  | 2023      | 33     | hogs & pigs                | NULL                                     | livestock          | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 23,610.0      | NULL    |
| 96      | pc-094-stanislaus-2024 | 06099 | stanislaus  | 2024      | 33     | hogs & pigs                | NULL                                     | livestock          | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 23,795.0      | NULL    |
| 37      | pc-111-merced-2023     | 06047 | merced      | 2023      | 34     | cattle - all               | NULL                                     | livestock          | NULL                                                                                                    | ds001: includes calves, cull bulls (dairy & beef), cull cows (dairy & beef), replacement heifers (dairy & beef) & stocker cattle. ds003: quantity not given, so inferred from no. head (san joaquin).                                                    | 3,475,090.0   | NULL    |
| 40      | pc-111-merced-2024     | 06047 | merced      | 2024      | 34     | cattle - all               | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given, so inferred from no. head (san joaquin).                                                                                                                                                                                      | 3,489,108.0   | NULL    |
| 38      | pc-111-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 34     | cattle - all               | NULL                                     | livestock          | NULL                                                                                                    | ds001: includes calves, cull bulls (dairy & beef), cull cows (dairy & beef), replacement heifers (dairy & beef) & stocker cattle. ds003: quantity not given, so inferred from no. head (san joaquin).                                                    | 1,103,000.0   | NULL    |
| 41      | pc-111-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 34     | cattle - all               | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given, so inferred from no. head (san joaquin).                                                                                                                                                                                      | 1,261,170.0   | NULL    |
| 39      | pc-111-stanislaus-2023 | 06099 | stanislaus  | 2023      | 34     | cattle - all               | NULL                                     | livestock          | NULL                                                                                                    | ds001: includes calves, cull bulls (dairy & beef), cull cows (dairy & beef), replacement heifers (dairy & beef) & stocker cattle. ds003: quantity not given, so inferred from no. head (san joaquin).                                                    | 2,207,838.0   | NULL    |
| 42      | pc-111-stanislaus-2024 | 06099 | stanislaus  | 2024      | 34     | cattle - all               | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given, so inferred from no. head (san joaquin).                                                                                                                                                                                      | 2,097,469.0   | NULL    |
| 7       | pc-131-merced-2023     | 06047 | merced      | 2023      | 35     | almond meats               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 143,774.0     | NULL    |
| 10      | pc-131-merced-2024     | 06047 | merced      | 2024      | 35     | almond meats               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 149,234.0     | NULL    |
| 8       | pc-131-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 35     | almond meats               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 110,200.0     | NULL    |
| 11      | pc-131-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 35     | almond meats               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 111,900.0     | NULL    |
| 9       | pc-131-stanislaus-2023 | 06099 | stanislaus  | 2023      | 35     | almond meats               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 235,431.0     | NULL    |
| 12      | pc-131-stanislaus-2024 | 06099 | stanislaus  | 2024      | 35     | almond meats               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 241,260.0     | NULL    |
| 66      | pc-100-merced-2023     | 06047 | merced      | 2023      | 36     | eggs - hens                | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 81,970,020.0  | NULL    |
| 69      | pc-100-merced-2024     | 06047 | merced      | 2024      | 36     | eggs - hens                | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 59,803,290.0  | NULL    |
| 67      | pc-100-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 36     | eggs - hens                | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 56,330,000.0  | NULL    |
| 70      | pc-100-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 36     | eggs - hens                | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 49,634,000.0  | NULL    |
| 68      | pc-100-stanislaus-2023 | 06099 | stanislaus  | 2023      | 36     | eggs - hens                | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 30,171,114.0  | NULL    |
| 71      | pc-100-stanislaus-2024 | 06099 | stanislaus  | 2024      | 36     | eggs - hens                | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 19,622,135.0  | NULL    |
| 13      | pc-132-merced-2023     | 06047 | merced      | 2023      | 37     | almond shells              | NULL                                     | crop               | NULL                                                                                                    | ds001: includes almond hash.                                                                                                                                                                                                                             | 120,743.0     | NULL    |
| 16      | pc-132-merced-2024     | 06047 | merced      | 2024      | 37     | almond shells              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 91,194.0      | NULL    |
| 14      | pc-132-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 37     | almond shells              | NULL                                     | crop               | NULL                                                                                                    | ds001: includes almond hash.                                                                                                                                                                                                                             | 110,200.0     | NULL    |
| 17      | pc-132-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 37     | almond shells              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 68,100.0      | NULL    |
| 15      | pc-132-stanislaus-2023 | 06099 | stanislaus  | 2023      | 37     | almond shells              | NULL                                     | crop               | NULL                                                                                                    | ds001: includes almond hash.                                                                                                                                                                                                                             | 235,431.0     | NULL    |
| 18      | pc-132-stanislaus-2024 | 06099 | stanislaus  | 2024      | 37     | almond shells              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 241,260.0     | NULL    |
| 133     | pc-057-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 38     | onions                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 31,300.0      | NULL    |
| 134     | pc-057-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 38     | onions                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 41,900.0      | NULL    |
| 179     | pc-124-merced-2023     | 06047 | merced      | 2023      | 39     | silage - other             | NULL                                     | crop               | NULL                                                                                                    | ds001: includes forage mix, oat, rye, sorghum, sudangrass and wheat. ds002: includes green chop. ds003: 'other' includes alfalfa, barley, forage and ryegrass. quantity not given, so inferred from quantities and acreages of other silages.            | 1,204,791.0   | NULL    |
| 182     | pc-124-merced-2024     | 06047 | merced      | 2024      | 39     | silage - other             | NULL                                     | crop               | NULL                                                                                                    | ds001: includes forage mix, oat, rye, sorghum, sudangrass, triticale and wheat. ds002: includes green chop. ds003: 'other' includes alfalfa, barley, forage and ryegrass. quantity not given, so inferred from quantities and acreages of other silages. | 1,113,022.0   | NULL    |
| 180     | pc-124-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 39     | silage - other             | NULL                                     | crop               | NULL                                                                                                    | ds001: includes forage mix, oat, rye, sorghum, sudangrass and wheat. ds002: includes green chop. ds003: 'other' includes alfalfa, barley, forage and ryegrass. quantity not given, so inferred from quantities and acreages of other silages.            | 642,000.0     | NULL    |
| 183     | pc-124-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 39     | silage - other             | NULL                                     | crop               | NULL                                                                                                    | ds001: includes forage mix, oat, rye, sorghum, sudangrass, triticale and wheat. ds002: includes green chop. ds003: 'other' includes alfalfa, barley, forage and ryegrass. quantity not given, so inferred from quantities and acreages of other silages. | 664,000.0     | NULL    |
| 181     | pc-124-stanislaus-2023 | 06099 | stanislaus  | 2023      | 39     | silage - other             | NULL                                     | crop               | NULL                                                                                                    | ds001: includes forage mix, oat, rye, sorghum, sudangrass and wheat. ds002: includes green chop. ds003: 'other' includes alfalfa, barley, forage and ryegrass. quantity not given, so inferred from quantities and acreages of other silages.            | 42,048.0      | NULL    |
| 184     | pc-124-stanislaus-2024 | 06099 | stanislaus  | 2024      | 39     | silage - other             | NULL                                     | crop               | NULL                                                                                                    | ds001: includes forage mix, oat, rye, sorghum, sudangrass, triticale and wheat. ds002: includes green chop. ds003: 'other' includes alfalfa, barley, forage and ryegrass. quantity not given, so inferred from quantities and acreages of other silages. | 42,724.0      | NULL    |
| 113     | pc-105-merced-2023     | 06047 | merced      | 2023      | 40     | melons - other             | NULL                                     | crop               | melons not elsewhere classified.                                                                        | ds003: quantity not given, so inferred from acreage and san joaquin production.                                                                                                                                                                          | 28,403.0      | NULL    |
| 116     | pc-105-merced-2024     | 06047 | merced      | 2024      | 40     | melons - other             | NULL                                     | crop               | melons not elsewhere classified.                                                                        | ds005, ds007: quantity not given, so inferred from acreage and san joaquin production.                                                                                                                                                                   | 60,737.0      | NULL    |
| 114     | pc-105-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 40     | melons - other             | NULL                                     | crop               | melons not elsewhere classified.                                                                        | ds003: quantity not given, so inferred from acreage and san joaquin production.                                                                                                                                                                          | 23,500.0      | NULL    |
| 117     | pc-105-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 40     | melons - other             | NULL                                     | crop               | melons not elsewhere classified.                                                                        | ds005, ds007: quantity not given, so inferred from acreage and san joaquin production.                                                                                                                                                                   | 23,500.0      | NULL    |
| 115     | pc-105-stanislaus-2023 | 06099 | stanislaus  | 2023      | 40     | melons - other             | NULL                                     | crop               | melons not elsewhere classified.                                                                        | ds003: quantity not given, so inferred from acreage and san joaquin production.                                                                                                                                                                          | 73,545.0      | NULL    |
| 118     | pc-105-stanislaus-2024 | 06099 | stanislaus  | 2024      | 40     | melons - other             | NULL                                     | crop               | melons not elsewhere classified.                                                                        | ds005, ds007: quantity not given, so inferred from acreage and san joaquin production.                                                                                                                                                                   | 34,863.0      | NULL    |
| 34      | pc-031-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 41     | blueberries                | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 15,950.0      | NULL    |
| 35      | pc-031-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 41     | blueberries                | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 13,080.0      | NULL    |
| 57      | pc-080-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 42     | corn - sweet               | 'corn' in the sense of maize, not wheat. | crop               | corn harvested before maturity at so-called 'milk' stage for market consumption.                        | NULL                                                                                                                                                                                                                                                     | 22,800.0      | NULL    |
| 58      | pc-080-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 42     | corn - sweet               | 'corn' in the sense of maize, not wheat. | crop               | corn harvested before maturity at so-called 'milk' stage for market consumption.                        | NULL                                                                                                                                                                                                                                                     | 24,200.0      | NULL    |
| 187     | pc-126-stanislaus-2023 | 06099 | stanislaus  | 2023      | 43     | silage - sudangrass        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 219,477.0     | NULL    |
| 188     | pc-126-stanislaus-2024 | 06099 | stanislaus  | 2024      | 43     | silage - sudangrass        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 187,604.0     | NULL    |
| 72      | pc-047-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 44     | garlic                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 22,700.0      | NULL    |
| 73      | pc-047-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 44     | garlic                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 29,300.0      | NULL    |
| 53      | pc-114-merced-2023     | 06047 | merced      | 2023      | 45     | corn - grain               | 'corn' in the sense of maize, not wheat. | crop               | corn grown till mature (dry) for animal feed, corn syrup, biofuels etc. a.k.a. field corn or dent corn. | NULL                                                                                                                                                                                                                                                     | 19,243.0      | NULL    |
| 55      | pc-114-merced-2024     | 06047 | merced      | 2024      | 45     | corn - grain               | 'corn' in the sense of maize, not wheat. | crop               | corn grown till mature (dry) for animal feed, corn syrup, biofuels etc. a.k.a. field corn or dent corn. | NULL                                                                                                                                                                                                                                                     | 21,305.0      | NULL    |
| 54      | pc-114-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 45     | corn - grain               | 'corn' in the sense of maize, not wheat. | crop               | corn grown till mature (dry) for animal feed, corn syrup, biofuels etc. a.k.a. field corn or dent corn. | NULL                                                                                                                                                                                                                                                     | 87,000.0      | NULL    |
| 56      | pc-114-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 45     | corn - grain               | 'corn' in the sense of maize, not wheat. | crop               | corn grown till mature (dry) for animal feed, corn syrup, biofuels etc. a.k.a. field corn or dent corn. | NULL                                                                                                                                                                                                                                                     | 101,000.0     | NULL    |
| 60      | pc-116-merced-2023     | 06047 | merced      | 2023      | 46     | cotton - acala             | NULL                                     | crop               | san joaquin valley acala                                                                                | NULL                                                                                                                                                                                                                                                     | 14,908.0      | NULL    |
| 19      | pc-024-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 47     | apples                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 16,800.0      | NULL    |
| 20      | pc-024-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 47     | apples                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 10,900.0      | NULL    |
| 169     | pc-121-merced-2023     | 06047 | merced      | 2023      | 48     | silage - alfalfa           | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 232,016.0     | NULL    |
| 170     | pc-121-merced-2024     | 06047 | merced      | 2024      | 48     | silage - alfalfa           | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 155,250.0     | NULL    |
| 25      | pc-027-merced-2023     | 06047 | merced      | 2023      | 49     | barley                     | NULL                                     | crop               | NULL                                                                                                    | ds001: 2023 amount not available so used 2022 amount.                                                                                                                                                                                                    | 2,112.0       | NULL    |
| 30      | pc-135-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 50     | beans - other              | NULL                                     | crop               | NULL                                                                                                    | ds003: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 3,000.0       | NULL    |
| 32      | pc-135-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 50     | beans - other              | NULL                                     | crop               | NULL                                                                                                    | ds007: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 4,452.0       | NULL    |
| 31      | pc-135-stanislaus-2023 | 06099 | stanislaus  | 2023      | 50     | beans - other              | NULL                                     | crop               | NULL                                                                                                    | ds003: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 100.0         | NULL    |
| 33      | pc-135-stanislaus-2024 | 06099 | stanislaus  | 2024      | 50     | beans - other              | NULL                                     | crop               | NULL                                                                                                    | ds007: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 15,091.0      | NULL    |
| 111     | pc-034-merced-2023     | 06047 | merced      | 2023      | 51     | melons - cantaloupe        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,343,051.0   | NULL    |
| 112     | pc-034-merced-2024     | 06047 | merced      | 2024      | 51     | melons - cantaloupe        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 3,028,270.0   | NULL    |
| 36      | pc-033-merced-2024     | 06047 | merced      | 2024      | 52     | broccoli                   | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 26,057.0      | NULL    |
| 155     | pc-069-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 53     | pumpkins                   | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 73,300.0      | NULL    |
| 157     | pc-069-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 53     | pumpkins                   | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 37,500.0      | NULL    |
| 156     | pc-069-stanislaus-2023 | 06099 | stanislaus  | 2023      | 53     | pumpkins                   | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 7,408.0       | NULL    |
| 158     | pc-069-stanislaus-2024 | 06099 | stanislaus  | 2024      | 53     | pumpkins                   | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 17,803.0      | NULL    |
| 163     | pc-095-merced-2023     | 06047 | merced      | 2023      | 54     | sheep & lambs              | NULL                                     | livestock          | NULL                                                                                                    | ds002: weight given in 'hd' which is an unknown unit. taken to be cwt. since value is in the right range. ds003: quantity not given, so inferred from no. head (merced).                                                                                 | 24,575.0      | NULL    |
| 166     | pc-095-merced-2024     | 06047 | merced      | 2024      | 54     | sheep & lambs              | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given, so inferred from no. head (merced).                                                                                                                                                                                           | 24,490.0      | NULL    |
| 164     | pc-095-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 54     | sheep & lambs              | NULL                                     | livestock          | NULL                                                                                                    | ds002: weight given in 'hd' which is an unknown unit. taken to be cwt. since value is in the right range. ds003: quantity not given, so inferred from no. head (merced).                                                                                 | 16,900.0      | NULL    |
| 167     | pc-095-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 54     | sheep & lambs              | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given, so inferred from no. head (merced).                                                                                                                                                                                           | 16,300.0      | NULL    |
| 165     | pc-095-stanislaus-2023 | 06099 | stanislaus  | 2023      | 54     | sheep & lambs              | NULL                                     | livestock          | NULL                                                                                                    | ds002: weight given in 'hd' which is an unknown unit. taken to be cwt. since value is in the right range. ds003: quantity not given, so inferred from no. head (merced).                                                                                 | 4,054.0       | NULL    |
| 168     | pc-095-stanislaus-2024 | 06099 | stanislaus  | 2024      | 54     | sheep & lambs              | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given, so inferred from no. head (merced).                                                                                                                                                                                           | 3,709.0       | NULL    |
| 74      | pc-096-merced-2023     | 06047 | merced      | 2023      | 55     | goats                      | NULL                                     | livestock          | NULL                                                                                                    | ds001: 'miscellaneous livestock' includes dairy and meat goats sold for meat. ds001, ds003: qty is number of head, each of which is ~1 cwt., on average.                                                                                                 | 26,619.0      | NULL    |
| 75      | pc-096-stanislaus-2023 | 06099 | stanislaus  | 2023      | 55     | goats                      | NULL                                     | livestock          | NULL                                                                                                    | ds001: 'miscellaneous livestock' includes dairy and meat goats sold for meat. ds001, ds003: qty is number of head, each of which is ~1 cwt., on average.                                                                                                 | 18,730.0      | NULL    |
| 76      | pc-096-stanislaus-2024 | 06099 | stanislaus  | 2024      | 55     | goats                      | NULL                                     | livestock          | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 19,935.0      | NULL    |
| 171     | pc-122-merced-2023     | 06047 | merced      | 2023      | 56     | silage - corn              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,470,029.0   | NULL    |
| 174     | pc-122-merced-2024     | 06047 | merced      | 2024      | 56     | silage - corn              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,978,152.0   | NULL    |
| 172     | pc-122-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 56     | silage - corn              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 1,136,000.0   | NULL    |
| 175     | pc-122-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 56     | silage - corn              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 865,000.0     | NULL    |
| 173     | pc-122-stanislaus-2023 | 06099 | stanislaus  | 2023      | 56     | silage - corn              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 1,422,508.0   | NULL    |
| 176     | pc-122-stanislaus-2024 | 06099 | stanislaus  | 2024      | 56     | silage - corn              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 1,465,625.0   | NULL    |
| 26      | pc-052-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 57     | beans - lima               | NULL                                     | crop               | NULL                                                                                                    | ds003: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 1,620.0       | NULL    |
| 28      | pc-052-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 57     | beans - lima               | NULL                                     | crop               | NULL                                                                                                    | ds007: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 1,927.0       | NULL    |
| 27      | pc-052-stanislaus-2023 | 06099 | stanislaus  | 2023      | 57     | beans - lima               | NULL                                     | crop               | NULL                                                                                                    | ds003: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 3,642.0       | NULL    |
| 29      | pc-052-stanislaus-2024 | 06099 | stanislaus  | 2024      | 57     | beans - lima               | NULL                                     | crop               | NULL                                                                                                    | ds007: stanislaus harvest volume not provided, so inferred by proportion from acreage using san joaquin production.                                                                                                                                      | 6,532.0       | NULL    |
| 61      | pc-118-merced-2023     | 06047 | merced      | 2023      | 58     | cotton - pima              | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 45,763.0      | NULL    |
| 103     | pc-113-merced-2023     | 06047 | merced      | 2023      | 59     | livestock -- miscellaneous | NULL                                     | livestock          | NULL                                                                                                    | ds001: includes dairy and meat goats sold for meat.                                                                                                                                                                                                      | 26,619.0      | NULL    |
| 104     | pc-113-merced-2024     | 06047 | merced      | 2024      | 59     | livestock -- miscellaneous | NULL                                     | livestock          | NULL                                                                                                    | ds005: includes dairy and meat goats sold for meat.                                                                                                                                                                                                      | 27,636.0      | NULL    |
| 143     | pc-064-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 60     | peppers                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 10,000.0      | NULL    |
| 144     | pc-064-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 60     | peppers                    | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 7,760.0       | NULL    |
| 211     | pc-106-merced-2023     | 06047 | merced      | 2023      | 61     | turkeys                    | NULL                                     | livestock          | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 36,457,450.0  | NULL    |
| 213     | pc-106-merced-2024     | 06047 | merced      | 2024      | 61     | turkeys                    | NULL                                     | livestock          | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 27,683,090.0  | NULL    |
| 212     | pc-106-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 61     | turkeys                    | NULL                                     | livestock          | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 5,163,000.0   | NULL    |
| 214     | pc-106-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 61     | turkeys                    | NULL                                     | livestock          | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 6,202,000.0   | NULL    |
| 193     | pc-077-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 62     | squash                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 10,100.0      | NULL    |
| 194     | pc-077-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 62     | squash                     | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 8,700.0       | NULL    |
| 231     | pc-110-merced-2023     | 06047 | merced      | 2023      | 63     | wool                       | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 62,467.0      | NULL    |
| 234     | pc-110-merced-2024     | 06047 | merced      | 2024      | 63     | wool                       | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 64,480.0      | NULL    |
| 232     | pc-110-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 63     | wool                       | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 72,000.0      | NULL    |
| 233     | pc-110-stanislaus-2023 | 06099 | stanislaus  | 2023      | 63     | wool                       | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 15,151.0      | NULL    |
| 235     | pc-110-stanislaus-2024 | 06099 | stanislaus  | 2024      | 63     | wool                       | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 14,210.0      | NULL    |
| 127     | pc-103-merced-2023     | 06047 | merced      | 2023      | 64     | milk - goat's              | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 61,836.0      | NULL    |
| 128     | pc-103-merced-2024     | 06047 | merced      | 2024      | 64     | milk - goat's              | NULL                                     | dairy product      | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 64,317.0      | NULL    |
| 89      | pc-120-merced-2023     | 06047 | merced      | 2023      | 65     | hay - other                | NULL                                     | crop               | NULL                                                                                                    | ds001: includes barley, forage mix, oat, teff grass, triticale, wheat and sudangrass. ds003: includes oat, wheat, forage and sudangrass.                                                                                                                 | 228,750.0     | NULL    |
| 92      | pc-120-merced-2024     | 06047 | merced      | 2024      | 65     | hay - other                | NULL                                     | crop               | NULL                                                                                                    | ds005: includes grain and sudan varieties. ds007: includes oat, wheat, forage, sudangrass and teff.                                                                                                                                                      | 246,536.0     | NULL    |
| 90      | pc-120-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 65     | hay - other                | NULL                                     | crop               | NULL                                                                                                    | ds001: includes barley, forage mix, oat, teff grass, triticale, wheat and sudangrass. ds003: includes oat, wheat, forage and sudangrass.                                                                                                                 | 19,900.0      | NULL    |
| 93      | pc-120-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 65     | hay - other                | NULL                                     | crop               | NULL                                                                                                    | ds005: includes grain and sudan varieties. ds007: includes oat, wheat, forage, sudangrass and teff.                                                                                                                                                      | 12,000.0      | NULL    |
| 91      | pc-120-stanislaus-2023 | 06099 | stanislaus  | 2023      | 65     | hay - other                | NULL                                     | crop               | NULL                                                                                                    | ds001: includes barley, forage mix, oat, teff grass, triticale, wheat and sudangrass. ds003: includes oat, wheat, forage and sudangrass.                                                                                                                 | 125,380.0     | NULL    |
| 94      | pc-120-stanislaus-2024 | 06099 | stanislaus  | 2024      | 65     | hay - other                | NULL                                     | crop               | NULL                                                                                                    | ds005: includes grain and sudan varieties. ds007: includes oat, wheat, forage, sudangrass and teff.                                                                                                                                                      | 127,320.0     | NULL    |
| 177     | pc-123-stanislaus-2023 | 06099 | stanislaus  | 2023      | 66     | silage - oat               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 150,904.0     | NULL    |
| 178     | pc-123-stanislaus-2024 | 06099 | stanislaus  | 2024      | 66     | silage - oat               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 150,497.0     | NULL    |
| 201     | pc-109-merced-2023     | 06047 | merced      | 2023      | 67     | tomatoes for market        | NULL                                     | crop               | NULL                                                                                                    | ds001: harvest given in 25-lb cartons, converted to tons.                                                                                                                                                                                                | 74,485.0      | NULL    |
| 203     | pc-109-merced-2024     | 06047 | merced      | 2024      | 67     | tomatoes for market        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 63,112.0      | NULL    |
| 202     | pc-109-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 67     | tomatoes for market        | NULL                                     | crop               | NULL                                                                                                    | ds001: harvest given in 25-lb cartons, converted to tons.                                                                                                                                                                                                | 46,600.0      | NULL    |
| 204     | pc-109-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 67     | tomatoes for market        | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 16,400.0      | NULL    |
| 153     | pc-097-merced-2023     | 06047 | merced      | 2023      | 68     | poultry                    | NULL                                     | livestock          | NULL                                                                                                    | ds001: 'poultry & fish'.                                                                                                                                                                                                                                 | 248,599.0     | NULL    |
| 154     | pc-097-merced-2024     | 06047 | merced      | 2024      | 68     | poultry                    | NULL                                     | livestock          | NULL                                                                                                    | ds005: 'poultry & fish'.                                                                                                                                                                                                                                 | 558,680.0     | NULL    |
| 191     | pc-128-stanislaus-2023 | 06099 | stanislaus  | 2023      | 69     | silage - wheat             | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 299,475.0     | NULL    |
| 192     | pc-128-stanislaus-2024 | 06099 | stanislaus  | 2024      | 69     | silage - wheat             | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 369,315.0     | NULL    |
| 195     | pc-129-merced-2023     | 06047 | merced      | 2023      | 70     | straw                      | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 8,080.0       | NULL    |
| 196     | pc-129-merced-2024     | 06047 | merced      | 2024      | 70     | straw                      | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 5,170.0       | NULL    |
| 1       | pc-130-merced-2023     | 06047 | merced      | 2023      | 71     | almond hulls               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 318,554.0     | NULL    |
| 4       | pc-130-merced-2024     | 06047 | merced      | 2024      | 71     | almond hulls               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 279,484.0     | NULL    |
| 2       | pc-130-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 71     | almond hulls               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 220,000.0     | NULL    |
| 5       | pc-130-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 71     | almond hulls               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 243,000.0     | NULL    |
| 3       | pc-130-stanislaus-2023 | 06099 | stanislaus  | 2023      | 71     | almond hulls               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 470,862.0     | NULL    |
| 6       | pc-130-stanislaus-2024 | 06099 | stanislaus  | 2024      | 71     | almond hulls               | NULL                                     | crop               | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 453,570.0     | NULL    |
| 47      | pc-112-merced-2023     | 06047 | merced      | 2023      | 72     | chickens                   | NULL                                     | livestock          | NULL                                                                                                    | ds003: quantity not given so inferred from no. head (merced).                                                                                                                                                                                            | 353,656,805.0 | NULL    |
| 50      | pc-112-merced-2024     | 06047 | merced      | 2024      | 72     | chickens                   | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given so inferred from no. head (merced).                                                                                                                                                                                            | 395,581,760.0 | NULL    |
| 48      | pc-112-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 72     | chickens                   | NULL                                     | livestock          | NULL                                                                                                    | ds003: quantity not given so inferred from no. head (merced).                                                                                                                                                                                            | 1,473,000.0   | NULL    |
| 51      | pc-112-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 72     | chickens                   | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given so inferred from no. head (merced).                                                                                                                                                                                            | 1,356,000.0   | NULL    |
| 49      | pc-112-stanislaus-2023 | 06099 | stanislaus  | 2023      | 72     | chickens                   | NULL                                     | livestock          | NULL                                                                                                    | ds003: quantity not given so inferred from no. head (merced).                                                                                                                                                                                            | 729,480,985.0 | NULL    |
| 52      | pc-112-stanislaus-2024 | 06099 | stanislaus  | 2024      | 72     | chickens                   | NULL                                     | livestock          | NULL                                                                                                    | ds007: quantity not given so inferred from no. head (merced).                                                                                                                                                                                            | 844,076,954.0 | NULL    |
| 121     | pc-102-merced-2023     | 06047 | merced      | 2023      | 73     | milk - cow's               | NULL                                     | dairy product      | NULL                                                                                                    | ds002: "milk - all" assumed to be mostly cow's milk.                                                                                                                                                                                                     | 66,460,000.0  | NULL    |
| 124     | pc-102-merced-2024     | 06047 | merced      | 2024      | 73     | milk - cow's               | NULL                                     | dairy product      | NULL                                                                                                    | ds006, ds007: "milk - all" assumed to be mostly cow's milk.                                                                                                                                                                                              | 65,490,000.0  | NULL    |
| 122     | pc-102-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 73     | milk - cow's               | NULL                                     | dairy product      | NULL                                                                                                    | ds002: "milk - all" assumed to be mostly cow's milk.                                                                                                                                                                                                     | 31,070,000.0  | NULL    |
| 125     | pc-102-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 73     | milk - cow's               | NULL                                     | dairy product      | NULL                                                                                                    | ds006, ds007: "milk - all" assumed to be mostly cow's milk.                                                                                                                                                                                              | 27,936,760.0  | NULL    |
| 123     | pc-102-stanislaus-2023 | 06099 | stanislaus  | 2023      | 73     | milk - cow's               | NULL                                     | dairy product      | NULL                                                                                                    | ds002: "milk - all" assumed to be mostly cow's milk.                                                                                                                                                                                                     | 38,067,141.0  | NULL    |
| 126     | pc-102-stanislaus-2024 | 06099 | stanislaus  | 2024      | 73     | milk - cow's               | NULL                                     | dairy product      | NULL                                                                                                    | ds006, ds007: "milk - all" assumed to be mostly cow's milk.                                                                                                                                                                                              | 37,582,360.0  | NULL    |
| 62      | pc-115-merced-2023     | 06047 | merced      | 2023      | 74     | cotton - seed (unginned)   | NULL                                     | crop               | raw cotton that includes fiber and seeds prior to ginning.                                              | NULL                                                                                                                                                                                                                                                     | 47,077.0      | NULL    |
| 63      | pc-115-merced-2024     | 06047 | merced      | 2024      | 74     | cotton - seed (unginned)   | NULL                                     | crop               | raw cotton that includes fiber and seeds prior to ginning.                                              | NULL                                                                                                                                                                                                                                                     | 47,394.0      | NULL    |
| 97      | pc-136-merced-2023     | 06047 | merced      | 2023      | 75     | honey                      | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 3,154,578.0   | NULL    |
| 100     | pc-136-merced-2024     | 06047 | merced      | 2024      | 75     | honey                      | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 2,336,190.0   | NULL    |
| 98      | pc-136-sanjoaquin-2023 | 06077 | san joaquin | 2023      | 75     | honey                      | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 4,871,000.0   | NULL    |
| 101     | pc-136-sanjoaquin-2024 | 06077 | san joaquin | 2024      | 75     | honey                      | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 4,480,000.0   | NULL    |
| 99      | pc-136-stanislaus-2023 | 06099 | stanislaus  | 2023      | 75     | honey                      | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 6,086,433.0   | NULL    |
| 102     | pc-136-stanislaus-2024 | 06099 | stanislaus  | 2024      | 75     | honey                      | NULL                                     | animal by-product  | NULL                                                                                                    | NULL                                                                                                                                                                                                                                                     | 5,534,547.0   | NULL    |

_Total rows: 235_

### 4.3 `public.resource_production_record` Schema, Rows, and Observations (Populated by `almond_nsjv.py`, Used by `mv_biomass_search`)

Separately from `county_ag_report_record`,
[`almond_nsjv.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/almond_nsjv.py#L26-L31)
loads 73 rows into `public.resource_production_record` (referenced by
[`mv_biomass_search.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py#L202)).

- `primary_ag_product_id` is `NULL` on all 73 rows, and there is no
  `almond_variety` column.
- Because `almond_nsjv.py` line 29 maps the spreadsheet's regional total column
  (`"nsjv": "NSJV"`) alongside the three county columns (`06047`, `06077`,
  `06099`), **21 of the 73 rows have `geoid = 'NSJV'`** (`id = 2, 4, 6, 8, 10`
  for `almond hash`; `id = 14, 18, 22, 26, 30, 34, 38, 42` for `almond hulls`;
  `id = 46, 50, 54, 58, 62, 66, 70, 73` for `almond shells`).
- In addition, `rpr_id = 20` (`06077` San Joaquin `2019-01-01` `almond hulls` =
  `18,000.0 t`) and `rpr_id = 40` (`06077` San Joaquin `2024-01-01`
  `almond hulls` = `24,300.0 t` vs. `243,000.0 t` in `carr_id = 5`) have 10×
  missing-zero transcription errors in the Almond NSJV sheet, and `06047` Merced
  `2024-01-01` `almond shells` is missing from `resource_production_record`.

```sql
SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'resource_production_record'
        ORDER BY ordinal_position;
```

| column_name           | data_type                   |
| --------------------- | --------------------------- |
| id                    | integer                     |
| created_at            | timestamp without time zone |
| updated_at            | timestamp without time zone |
| etl_run_id            | integer                     |
| lineage_group_id      | integer                     |
| dataset_id            | integer                     |
| method_id             | integer                     |
| geoid                 | character varying           |
| primary_ag_product_id | integer                     |
| resource_id           | integer                     |
| report_date           | date                        |
| scenario              | character varying           |
| note                  | character varying           |

_Total rows: 13_

```sql
SELECT
            rpr.id AS rpr_id,
            rpr.geoid,
            rpr.resource_id,
            r.name AS resource_name,
            rpr.primary_ag_product_id,
            rpr.report_date,
            obs.id AS obs_id,
            obs.record_id,
            param.name AS param_name,
            obs.value,
            u.name AS unit_name,
            obs.note
        FROM public.resource_production_record rpr
        LEFT JOIN public.resource r ON rpr.resource_id = r.id
        LEFT JOIN public.observation obs ON obs.record_type = 'resource_production_record'
            AND (obs.record_id = CAST(rpr.id AS VARCHAR) OR obs.record_id LIKE '%' || CAST(rpr.id AS VARCHAR) || '%')
        LEFT JOIN public.parameter param ON obs.parameter_id = param.id
        LEFT JOIN public.unit u ON obs.unit_id = u.id
        ORDER BY rpr.id, obs.id;
```

| rpr_id | geoid | resource_id | resource_name | primary_ag_product_id | report_date | obs_id | record_id | param_name | value       | unit_name | note |
| ------ | ----- | ----------- | ------------- | --------------------- | ----------- | ------ | --------- | ---------- | ----------- | --------- | ---- |
| 1      | 06047 | 100         | almond hash   | NULL                  | 2019-01-01  | 50506  | 1         | production | 1,350.0     | tons      | NULL |
| 2      | NSJV  | 100         | almond hash   | NULL                  | 2019-01-01  | 50507  | 2         | production | 1,350.0     | tons      | NULL |
| 3      | 06047 | 100         | almond hash   | NULL                  | 2020-01-01  | 50510  | 3         | production | 1,339.0     | tons      | NULL |
| 4      | NSJV  | 100         | almond hash   | NULL                  | 2020-01-01  | 50511  | 4         | production | 1,339.0     | tons      | NULL |
| 5      | 06047 | 100         | almond hash   | NULL                  | 2021-01-01  | 50514  | 5         | production | 1,296.0     | tons      | NULL |
| 6      | NSJV  | 100         | almond hash   | NULL                  | 2021-01-01  | 50515  | 6         | production | 1,296.0     | tons      | NULL |
| 7      | 06047 | 100         | almond hash   | NULL                  | 2022-01-01  | 50518  | 7         | production | 1,641.0     | tons      | NULL |
| 8      | NSJV  | 100         | almond hash   | NULL                  | 2022-01-01  | 50519  | 8         | production | 1,641.0     | tons      | NULL |
| 9      | 06047 | 100         | almond hash   | NULL                  | 2023-01-01  | 50522  | 9         | production | 1,828.0     | tons      | NULL |
| 10     | NSJV  | 100         | almond hash   | NULL                  | 2023-01-01  | 50523  | 10        | production | 1,828.0     | tons      | NULL |
| 11     | 06047 | 32          | almond hulls  | NULL                  | 2017-01-01  | 50528  | 11        | production | 198,288.0   | tons      | NULL |
| 12     | 06077 | 32          | almond hulls  | NULL                  | 2017-01-01  | 50529  | 12        | production | 151,000.0   | tons      | NULL |
| 13     | 06099 | 32          | almond hulls  | NULL                  | 2017-01-01  | 50530  | 13        | production | 424,000.0   | tons      | NULL |
| 14     | NSJV  | 32          | almond hulls  | NULL                  | 2017-01-01  | 50531  | 14        | production | 773,288.0   | tons      | NULL |
| 15     | 06047 | 32          | almond hulls  | NULL                  | 2018-01-01  | 50536  | 15        | production | 174,593.0   | tons      | NULL |
| 16     | 06077 | 32          | almond hulls  | NULL                  | 2018-01-01  | 50537  | 16        | production | 219,000.0   | tons      | NULL |
| 17     | 06099 | 32          | almond hulls  | NULL                  | 2018-01-01  | 50538  | 17        | production | 452,000.0   | tons      | NULL |
| 18     | NSJV  | 32          | almond hulls  | NULL                  | 2018-01-01  | 50539  | 18        | production | 845,593.0   | tons      | NULL |
| 19     | 06047 | 32          | almond hulls  | NULL                  | 2019-01-01  | 50544  | 19        | production | 147,361.0   | tons      | NULL |
| 20     | 06077 | 32          | almond hulls  | NULL                  | 2019-01-01  | 50545  | 20        | production | 18,000.0    | tons      | NULL |
| 21     | 06099 | 32          | almond hulls  | NULL                  | 2019-01-01  | 50546  | 21        | production | 476,000.0   | tons      | NULL |
| 22     | NSJV  | 32          | almond hulls  | NULL                  | 2019-01-01  | 50547  | 22        | production | 641,361.0   | tons      | NULL |
| 23     | 06047 | 32          | almond hulls  | NULL                  | 2020-01-01  | 50552  | 23        | production | 227,605.0   | tons      | NULL |
| 24     | 06077 | 32          | almond hulls  | NULL                  | 2020-01-01  | 50553  | 24        | production | 365,000.0   | tons      | NULL |
| 25     | 06099 | 32          | almond hulls  | NULL                  | 2020-01-01  | 50554  | 25        | production | 579,000.0   | tons      | NULL |
| 26     | NSJV  | 32          | almond hulls  | NULL                  | 2020-01-01  | 50555  | 26        | production | 1,171,605.0 | tons      | NULL |
| 27     | 06047 | 32          | almond hulls  | NULL                  | 2021-01-01  | 50560  | 27        | production | 244,523.0   | tons      | NULL |
| 28     | 06077 | 32          | almond hulls  | NULL                  | 2021-01-01  | 50561  | 28        | production | 251,000.0   | tons      | NULL |
| 29     | 06099 | 32          | almond hulls  | NULL                  | 2021-01-01  | 50562  | 29        | production | 524,698.0   | tons      | NULL |
| 30     | NSJV  | 32          | almond hulls  | NULL                  | 2021-01-01  | 50563  | 30        | production | 1,020,221.0 | tons      | NULL |
| 31     | 06047 | 32          | almond hulls  | NULL                  | 2022-01-01  | 50568  | 31        | production | 309,401.0   | tons      | NULL |
| 32     | 06077 | 32          | almond hulls  | NULL                  | 2022-01-01  | 50569  | 32        | production | 242,000.0   | tons      | NULL |
| 33     | 06099 | 32          | almond hulls  | NULL                  | 2022-01-01  | 50570  | 33        | production | 444,174.0   | tons      | NULL |
| 34     | NSJV  | 32          | almond hulls  | NULL                  | 2022-01-01  | 50571  | 34        | production | 995,575.0   | tons      | NULL |
| 35     | 06047 | 32          | almond hulls  | NULL                  | 2023-01-01  | 50576  | 35        | production | 318,554.0   | tons      | NULL |
| 36     | 06077 | 32          | almond hulls  | NULL                  | 2023-01-01  | 50577  | 36        | production | 220,000.0   | tons      | NULL |
| 37     | 06099 | 32          | almond hulls  | NULL                  | 2023-01-01  | 50578  | 37        | production | 470,862.0   | tons      | NULL |
| 38     | NSJV  | 32          | almond hulls  | NULL                  | 2023-01-01  | 50579  | 38        | production | 1,009,416.0 | tons      | NULL |
| 39     | 06047 | 32          | almond hulls  | NULL                  | 2024-01-01  | 50584  | 39        | production | 279,484.0   | tons      | NULL |
| 40     | 06077 | 32          | almond hulls  | NULL                  | 2024-01-01  | 50585  | 40        | production | 24,300.0    | tons      | NULL |
| 41     | 06099 | 32          | almond hulls  | NULL                  | 2024-01-01  | 50586  | 41        | production | 453,570.0   | tons      | NULL |
| 42     | NSJV  | 32          | almond hulls  | NULL                  | 2024-01-01  | 50587  | 42        | production | 757,354.0   | tons      | NULL |
| 43     | 06047 | 5           | almond shells | NULL                  | 2017-01-01  | 50592  | 43        | production | 53,490.0    | tons      | NULL |
| 44     | 06077 | 5           | almond shells | NULL                  | 2017-01-01  | 50593  | 44        | production | 75,400.0    | tons      | NULL |
| 45     | 06099 | 5           | almond shells | NULL                  | 2017-01-01  | 50594  | 45        | production | 212,000.0   | tons      | NULL |
| 46     | NSJV  | 5           | almond shells | NULL                  | 2017-01-01  | 50595  | 46        | production | 340,890.0   | tons      | NULL |
| 47     | 06047 | 5           | almond shells | NULL                  | 2018-01-01  | 50600  | 47        | production | 55,820.0    | tons      | NULL |
| 48     | 06077 | 5           | almond shells | NULL                  | 2018-01-01  | 50601  | 48        | production | 109,500.0   | tons      | NULL |
| 49     | 06099 | 5           | almond shells | NULL                  | 2018-01-01  | 50602  | 49        | production | 226,000.0   | tons      | NULL |
| 50     | NSJV  | 5           | almond shells | NULL                  | 2018-01-01  | 50603  | 50        | production | 391,320.0   | tons      | NULL |
| 51     | 06047 | 5           | almond shells | NULL                  | 2019-01-01  | 50608  | 51        | production | 64,325.0    | tons      | NULL |
| 52     | 06077 | 5           | almond shells | NULL                  | 2019-01-01  | 50609  | 52        | production | 89,900.0    | tons      | NULL |
| 53     | 06099 | 5           | almond shells | NULL                  | 2019-01-01  | 50610  | 53        | production | 238,000.0   | tons      | NULL |
| 54     | NSJV  | 5           | almond shells | NULL                  | 2019-01-01  | 50611  | 54        | production | 392,225.0   | tons      | NULL |
| 55     | 06047 | 5           | almond shells | NULL                  | 2020-01-01  | 50616  | 55        | production | 69,152.0    | tons      | NULL |
| 56     | 06077 | 5           | almond shells | NULL                  | 2020-01-01  | 50617  | 56        | production | 182,600.0   | tons      | NULL |
| 57     | 06099 | 5           | almond shells | NULL                  | 2020-01-01  | 50618  | 57        | production | 289,000.0   | tons      | NULL |
| 58     | NSJV  | 5           | almond shells | NULL                  | 2020-01-01  | 50619  | 58        | production | 540,752.0   | tons      | NULL |
| 59     | 06047 | 5           | almond shells | NULL                  | 2021-01-01  | 50624  | 59        | production | 74,237.0    | tons      | NULL |
| 60     | 06077 | 5           | almond shells | NULL                  | 2021-01-01  | 50625  | 60        | production | 125,600.0   | tons      | NULL |
| 61     | 06099 | 5           | almond shells | NULL                  | 2021-01-01  | 50626  | 61        | production | 262,349.0   | tons      | NULL |
| 62     | NSJV  | 5           | almond shells | NULL                  | 2021-01-01  | 50627  | 62        | production | 462,186.0   | tons      | NULL |
| 63     | 06047 | 5           | almond shells | NULL                  | 2022-01-01  | 50632  | 63        | production | 109,189.0   | tons      | NULL |
| 64     | 06077 | 5           | almond shells | NULL                  | 2022-01-01  | 50633  | 64        | production | 120,900.0   | tons      | NULL |
| 65     | 06099 | 5           | almond shells | NULL                  | 2022-01-01  | 50634  | 65        | production | 222,087.0   | tons      | NULL |
| 66     | NSJV  | 5           | almond shells | NULL                  | 2022-01-01  | 50635  | 66        | production | 452,176.0   | tons      | NULL |
| 67     | 06047 | 5           | almond shells | NULL                  | 2023-01-01  | 50640  | 67        | production | 228,915.0   | tons      | NULL |
| 68     | 06077 | 5           | almond shells | NULL                  | 2023-01-01  | 50641  | 68        | production | 110,200.0   | tons      | NULL |
| 69     | 06099 | 5           | almond shells | NULL                  | 2023-01-01  | 50642  | 69        | production | 235,431.0   | tons      | NULL |
| 70     | NSJV  | 5           | almond shells | NULL                  | 2023-01-01  | 50643  | 70        | production | 574,546.0   | tons      | NULL |
| 71     | 06077 | 5           | almond shells | NULL                  | 2024-01-01  | 50647  | 71        | production | 68,100.0    | tons      | NULL |
| 72     | 06099 | 5           | almond shells | NULL                  | 2024-01-01  | 50648  | 72        | production | 241,260.0   | tons      | NULL |
| 73     | NSJV  | 5           | almond shells | NULL                  | 2024-01-01  | 50649  | 73        | production | 309,360.0   | tons      | NULL |

_Total rows: 73_

---

## 5. Verification of Path B & Path D with `unit_id = 19` (`acres`)

### 5.1 Path D (`acreage_based_volumes`) Simulation with `unit_id = 19`

When `_acreage_unit_id` at line 42 of
[`mv_biomass_volume_estimate.py`](file:///Users/pjsmitty301/ca-biositing/src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L42)
is changed from `18` (`bushels`) to `19` (`acres`):

- **19 of the 20 county-year rows** in Path D immediately populate via the
  existing `COALESCE(bnb_acres, harvested_acres)` expression
  (`coalesce_bnb_harv`).
- For the **1 remaining row** — `walnut tree sticks` (`resource_id = 15`) in
  `06047` (`merced`) for `2022` — `bnb_acres` (`parameter_id = 7`,
  `area bearing & non-bearing`) is **`NULL`** (withheld `(D)` in the 2022 USDA
  Census), whereas `bearing_acres` (`parameter_id = 5`, `area bearing`) is
  **`11,359.0` acres**. Adding `_param_bearing_id` (`5`) to
  `Observation.parameter_id.in_([_param_bnb_id, _param_bearing_id, _param_harvested_id])`
  (line 343) and `func.coalesce(bnb_acres, bearing_acres, harvested_acres)`
  (lines 285–291) recovers `11,359.0 ac × 0.6 = 6,815.4 dry_tons`
  (`coalesce_bnb_bear_harv`).
- Note that `factor_mid` for `grape stem` (`id = 23`) is `NULL` in
  `public.residue_factor`, so `est_vol_mid` is `NULL` until `grape stem` is
  moved to weight-based `Case 1B`.

```sql
SELECT
            r.id AS resource_id,
            r.name AS resource_name,
            ucr.geoid,
            p.county_name AS county,
            ucr.year AS dataset_year,
            AVG(CASE WHEN obs.parameter_id = 7 THEN obs.value END) AS bnb_acres,
            AVG(CASE WHEN obs.parameter_id = 5 THEN obs.value END) AS bearing_acres,
            AVG(CASE WHEN obs.parameter_id = 3 THEN obs.value END) AS harvested_acres,
            COALESCE(
                AVG(CASE WHEN obs.parameter_id = 7 THEN obs.value END),
                AVG(CASE WHEN obs.parameter_id = 3 THEN obs.value END)
            ) AS coalesce_bnb_harv,
            COALESCE(
                AVG(CASE WHEN obs.parameter_id = 7 THEN obs.value END),
                AVG(CASE WHEN obs.parameter_id = 5 THEN obs.value END),
                AVG(CASE WHEN obs.parameter_id = 3 THEN obs.value END)
            ) AS coalesce_bnb_bear_harv,
            COALESCE(rf.prune_trim_yield, rf.factor_mid) AS factor_mid,
            COALESCE(
                AVG(CASE WHEN obs.parameter_id = 7 THEN obs.value END),
                AVG(CASE WHEN obs.parameter_id = 5 THEN obs.value END),
                AVG(CASE WHEN obs.parameter_id = 3 THEN obs.value END)
            ) * COALESCE(rf.prune_trim_yield, rf.factor_mid) AS est_vol_mid
        FROM public.usda_census_record ucr
        JOIN public.resource_usda_commodity_map m ON m.usda_commodity_id = ucr.commodity_code
        JOIN public.resource r ON r.id = m.resource_id
        JOIN public.residue_factor rf ON rf.resource_id = r.id AND rf.factor_type = 'area'
        JOIN public.place p ON ucr.geoid = p.geoid
        LEFT JOIN public.observation obs ON
            obs.record_id = CAST(ucr.id AS VARCHAR)
            AND obs.record_type = 'usda_census_record'
            AND obs.unit_id = 19
            AND obs.parameter_id IN (7, 5, 3)
        WHERE lower(p.county_name) IN ('san joaquin', 'stanislaus', 'merced')
          AND ucr.year >= 2015
        GROUP BY r.id, r.name, ucr.geoid, p.county_name, ucr.year, ucr.id, rf.prune_trim_yield, rf.factor_mid
        ORDER BY r.id, ucr.geoid, ucr.year;
```

| resource_id | resource_name      | geoid | county      | dataset_year | bnb_acres | bearing_acres | harvested_acres | coalesce_bnb_harv | coalesce_bnb_bear_harv | factor_mid | est_vol_mid |
| ----------- | ------------------ | ----- | ----------- | ------------ | --------- | ------------- | --------------- | ----------------- | ---------------------- | ---------- | ----------- |
| 6           | cotton stem mix    | 06047 | merced      | 2017         | NULL      | NULL          | 47,766.0        | 47,766.0          | 47,766.0               | 1.2        | 57,319.2    |
| 6           | cotton stem mix    | 06047 | merced      | 2022         | NULL      | NULL          | 33,318.0        | 33,318.0          | 33,318.0               | 1.2        | 39,981.6    |
| 15          | walnut tree sticks | 06047 | merced      | 2017         | 10,117.0  | 8,358.0       | NULL            | 10,117.0          | 10,117.0               | 0.6        | 6,070.2     |
| 15          | walnut tree sticks | 06047 | merced      | 2022         | NULL      | 11,359.0      | NULL            | NULL              | 11,359.0               | 0.6        | 6,815.4     |
| 15          | walnut tree sticks | 06077 | san joaquin | 2017         | 59,468.0  | 47,892.0      | NULL            | 59,468.0          | 59,468.0               | 0.6        | 35,680.8    |
| 15          | walnut tree sticks | 06077 | san joaquin | 2022         | 72,248.0  | 65,741.0      | NULL            | 72,248.0          | 72,248.0               | 0.6        | 43,348.8    |
| 15          | walnut tree sticks | 06099 | stanislaus  | 2017         | 37,299.0  | 29,668.0      | NULL            | 37,299.0          | 37,299.0               | 0.6        | 22,379.4    |
| 15          | walnut tree sticks | 06099 | stanislaus  | 2022         | 34,171.0  | 30,389.0      | NULL            | 34,171.0          | 34,171.0               | 0.6        | 20,502.6    |
| 16          | almond branches    | 06047 | merced      | 2017         | 139,565.0 | 116,967.0     | NULL            | 139,565.0         | 139,565.0              | 1.5        | 209,347.5   |
| 16          | almond branches    | 06047 | merced      | 2022         | 163,831.0 | 141,467.0     | NULL            | 163,831.0         | 163,831.0              | 1.5        | 245,746.5   |
| 16          | almond branches    | 06077 | san joaquin | 2017         | 70,903.0  | 59,620.0      | NULL            | 70,903.0          | 70,903.0               | 1.5        | 106,354.5   |
| 16          | almond branches    | 06077 | san joaquin | 2022         | 120,358.0 | 94,970.0      | NULL            | 120,358.0         | 120,358.0              | 1.5        | 180,537.0   |
| 16          | almond branches    | 06099 | stanislaus  | 2017         | 183,882.0 | 162,963.0     | NULL            | 183,882.0         | 183,882.0              | 1.5        | 275,823.0   |
| 16          | almond branches    | 06099 | stanislaus  | 2022         | 238,190.0 | 198,594.0     | NULL            | 238,190.0         | 238,190.0              | 1.5        | 357,285.0   |
| 23          | grape stem         | 06047 | merced      | 2017         | 15,071.0  | 13,988.0      | NULL            | 15,071.0          | 15,071.0               | NULL       | NULL        |
| 23          | grape stem         | 06047 | merced      | 2022         | 15,050.0  | 12,890.0      | NULL            | 15,050.0          | 15,050.0               | NULL       | NULL        |
| 23          | grape stem         | 06077 | san joaquin | 2017         | 104,922.0 | 97,895.0      | NULL            | 104,922.0         | 104,922.0              | NULL       | NULL        |
| 23          | grape stem         | 06077 | san joaquin | 2022         | 111,972.0 | 107,018.0     | NULL            | 111,972.0         | 111,972.0              | NULL       | NULL        |
| 23          | grape stem         | 06099 | stanislaus  | 2017         | 10,559.0  | 10,066.0      | NULL            | 10,559.0          | 10,559.0               | NULL       | NULL        |
| 23          | grape stem         | 06099 | stanislaus  | 2022         | 11,748.0  | 11,094.0      | NULL            | 11,748.0          | 11,748.0               | NULL       | NULL        |

_Total rows: 20_

### 5.2 Path B (`census_based_volumes`) Simulation with `unit_id = 19`

Path B (lines 125–214) also uses `_acreage_unit_id = 18` at line 170
(`Observation.unit_id == _acreage_unit_id`) for `grape vines`
(`resource_id = 7`, `factor_type = 'weight'`, `prune_trim_yield = 1.1`).
Changing `_acreage_unit_id` from `18` to `19` fixes **both** Path B and Path D
simultaneously:

```sql
SELECT
            r.id AS resource_id,
            r.name AS resource_name,
            ucr.geoid,
            p.county_name AS county,
            ucr.year AS dataset_year,
            AVG(CASE WHEN obs.parameter_id = 7 THEN obs.value END) AS bnb_acres,
            AVG(CASE WHEN obs.parameter_id = 5 THEN obs.value END) AS bearing_acres,
            COALESCE(
                AVG(CASE WHEN obs.parameter_id = 7 THEN obs.value END),
                AVG(CASE WHEN obs.parameter_id = 5 THEN obs.value END)
            ) AS chosen_acres,
            rf.prune_trim_yield,
            COALESCE(
                AVG(CASE WHEN obs.parameter_id = 7 THEN obs.value END),
                AVG(CASE WHEN obs.parameter_id = 5 THEN obs.value END)
            ) * rf.prune_trim_yield AS est_vol_mid
        FROM public.usda_census_record ucr
        JOIN public.usda_commodity uc ON ucr.commodity_code = uc.id
        JOIN public.resource_usda_commodity_map m ON m.usda_commodity_id = uc.id
        JOIN public.resource r ON r.id = m.resource_id
        JOIN public.residue_factor rf ON rf.resource_id = r.id
        JOIN public.place p ON ucr.geoid = p.geoid
        LEFT JOIN public.observation obs ON
            obs.record_id = CAST(ucr.id AS VARCHAR)
            AND obs.record_type = 'usda_census_record'
            AND obs.unit_id = 19
            AND obs.parameter_id IN (7, 5)
        WHERE rf.prune_trim_yield IS NOT NULL
          AND rf.factor_type != 'area'
          AND lower(p.county_name) IN ('san joaquin', 'stanislaus', 'merced')
          AND ucr.year >= 2015
          AND lower(r.name) NOT IN ('alfalfa', 'almond woodchips', 'almond shells and hulls mix')
        GROUP BY r.id, r.name, ucr.geoid, p.county_name, ucr.year, ucr.id, rf.prune_trim_yield
        ORDER BY r.id, ucr.geoid, ucr.year;
```

| resource_id | resource_name | geoid | county      | dataset_year | bnb_acres | bearing_acres | chosen_acres | prune_trim_yield | est_vol_mid |
| ----------- | ------------- | ----- | ----------- | ------------ | --------- | ------------- | ------------ | ---------------- | ----------- |
| 7           | grape vines   | 06047 | merced      | 2017         | 15,071.0  | 13,988.0      | 15,071.0     | 1.1              | 16,578.1    |
| 7           | grape vines   | 06047 | merced      | 2022         | 15,050.0  | 12,890.0      | 15,050.0     | 1.1              | 16,555.0    |
| 7           | grape vines   | 06077 | san joaquin | 2017         | 104,922.0 | 97,895.0      | 104,922.0    | 1.1              | 115,414.2   |
| 7           | grape vines   | 06077 | san joaquin | 2022         | 111,972.0 | 107,018.0     | 111,972.0    | 1.1              | 123,169.2   |
| 7           | grape vines   | 06099 | stanislaus  | 2017         | 10,559.0  | 10,066.0      | 10,559.0     | 1.1              | 11,614.9    |
| 7           | grape vines   | 06099 | stanislaus  | 2022         | 11,748.0  | 11,094.0      | 11,748.0     | 1.1              | 12,922.8    |

_Total rows: 6_

---

## 6. Live Materialized View Outputs (`mv_biomass_volume_estimate` & `mv_usda_county_production`)

### 6.1 `data_portal.mv_biomass_volume_estimate` by Resource, Volume Source, and Year

Note that:

- `production_based` (Path A, from `public.county_ag_report_record`) and
  `commodity_direct` (Path C, from `public.county_ag_report_record`) have rows
  for **`2023` and `2024`**.
- `prune_acres` (Path B, from `public.usda_census_record`), `acreage_based`
  (Path D, from `public.usda_census_record`), and `census_production_based`
  (Path E, from `public.usda_census_record`) have rows for **`2017` and
  `2022`**.

```sql
SELECT
            resource_id,
            resource_name,
            volume_source,
            production_unit,
            biomass_unit,
            dataset_year,
            COUNT(*) AS row_count,
            COUNT(DISTINCT geoid) AS county_count,
            ROUND(AVG(factor_min)::numeric, 4) AS factor_min,
            ROUND(AVG(factor_mid)::numeric, 4) AS factor_mid,
            ROUND(AVG(factor_max)::numeric, 4) AS factor_max,
            ROUND(SUM(production_volume)::numeric, 2) AS sum_production_vol,
            ROUND(SUM(county_crop_acres)::numeric, 2) AS sum_crop_acres,
            ROUND(SUM(estimated_residue_volume_min)::numeric, 2) AS sum_res_min,
            ROUND(SUM(estimated_residue_volume_mid)::numeric, 2) AS sum_res_mid,
            ROUND(SUM(estimated_residue_volume_max)::numeric, 2) AS sum_res_max
        FROM data_portal.mv_biomass_volume_estimate
        GROUP BY resource_id, resource_name, volume_source, production_unit, biomass_unit, dataset_year
        ORDER BY resource_id, volume_source, dataset_year;
```

| resource_id | resource_name            | volume_source           | production_unit | biomass_unit | dataset_year | row_count | county_count | factor_min | factor_mid | factor_max | sum_production_vol | sum_crop_acres | sum_res_min  | sum_res_mid  | sum_res_max  |
| ----------- | ------------------------ | ----------------------- | --------------- | ------------ | ------------ | --------- | ------------ | ---------- | ---------- | ---------- | ------------------ | -------------- | ------------ | ------------ | ------------ |
| 2           | rice straw               | production_based        | tons            | dry_tons     | 2023         | 1         | 1            | 0.7        | 1.05       | 1.4        | 55,800.0           | NULL           | 39,060.0     | 58,590.0     | 78,120.0     |
| 2           | rice straw               | production_based        | tons            | dry_tons     | 2024         | 1         | 1            | 0.7        | 1.05       | 1.4        | 58,600.0           | NULL           | 41,020.0     | 61,530.0     | 82,040.0     |
| 5           | almond shells            | commodity_direct        | tons            | tons         | 2023         | 3         | 3            | NULL       | 1.0        | NULL       | 466,374.0          | NULL           | 466,374.0    | 466,374.0    | 466,374.0    |
| 5           | almond shells            | commodity_direct        | tons            | tons         | 2024         | 3         | 3            | NULL       | 1.0        | NULL       | 400,554.0          | NULL           | 400,554.0    | 400,554.0    | 400,554.0    |
| 6           | cotton stem mix          | acreage_based           | acres           | dry_tons     | 2017         | 1         | 1            | 1.2        | 1.2        | 1.2        | NULL               | NULL           | NULL         | NULL         | NULL         |
| 6           | cotton stem mix          | acreage_based           | acres           | dry_tons     | 2022         | 1         | 1            | 1.2        | 1.2        | 1.2        | NULL               | NULL           | NULL         | NULL         | NULL         |
| 7           | grape vines              | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | NULL       | NULL       | 876,780.0          | NULL           | NULL         | NULL         | NULL         |
| 7           | grape vines              | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | NULL       | NULL       | 757,146.0          | NULL           | NULL         | NULL         | NULL         |
| 7           | grape vines              | prune_acres             | acres           | dry_tons     | 2017         | 3         | 3            | NULL       | NULL       | NULL       | NULL               | NULL           | NULL         | NULL         | NULL         |
| 7           | grape vines              | prune_acres             | acres           | dry_tons     | 2022         | 3         | 3            | NULL       | NULL       | NULL       | NULL               | NULL           | NULL         | NULL         | NULL         |
| 8           | walnut shelling fines    | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | 1.494      | NULL       | 242,318.0          | NULL           | NULL         | 362,023.09   | NULL         |
| 8           | walnut shelling fines    | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | 1.494      | NULL       | 182,324.0          | NULL           | NULL         | 272,392.06   | NULL         |
| 10          | pistachio shells         | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | 0.15       | NULL       | 36,747.0           | NULL           | NULL         | 5,512.05     | NULL         |
| 10          | pistachio shells         | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | 0.15       | NULL       | 31,211.0           | NULL           | NULL         | 4,681.65     | NULL         |
| 12          | corn stover whole        | census_production_based | tons            | dry_tons     | 2017         | 3         | 3            | 0.818      | 1.02       | 1.222      | 4,517,173.0        | NULL           | 3,695,047.51 | 4,607,516.46 | 5,519,985.41 |
| 12          | corn stover whole        | census_production_based | tons            | dry_tons     | 2022         | 3         | 3            | 0.818      | 1.02       | 1.222      | 5,216,315.0        | NULL           | 4,266,945.67 | 5,320,641.3  | 6,374,336.93 |
| 14          | walnut hulls             | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | 0.524      | NULL       | 242,318.0          | NULL           | NULL         | 126,974.63   | NULL         |
| 14          | walnut hulls             | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | 0.524      | NULL       | 182,324.0          | NULL           | NULL         | 95,537.78    | NULL         |
| 15          | walnut tree sticks       | acreage_based           | acres           | dry_tons     | 2017         | 3         | 3            | 0.6        | 0.6        | 0.6        | NULL               | NULL           | NULL         | NULL         | NULL         |
| 15          | walnut tree sticks       | acreage_based           | acres           | dry_tons     | 2022         | 3         | 3            | 0.6        | 0.6        | 0.6        | NULL               | NULL           | NULL         | NULL         | NULL         |
| 16          | almond branches          | acreage_based           | acres           | dry_tons     | 2017         | 3         | 3            | 1.5        | 1.5        | 1.5        | NULL               | NULL           | NULL         | NULL         | NULL         |
| 16          | almond branches          | acreage_based           | acres           | dry_tons     | 2022         | 3         | 3            | 1.5        | 1.5        | 1.5        | NULL               | NULL           | NULL         | NULL         | NULL         |
| 17          | olive stems / leaves     | production_based        | tons            | dry_tons     | 2023         | 2         | 2            | NULL       | NULL       | NULL       | 15,170.0           | NULL           | NULL         | NULL         | NULL         |
| 17          | olive stems / leaves     | production_based        | tons            | dry_tons     | 2024         | 2         | 2            | NULL       | NULL       | NULL       | 28,235.0           | NULL           | NULL         | NULL         | NULL         |
| 18          | peach screening waste    | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | NULL       | NULL       | 133,229.0          | NULL           | NULL         | NULL         | NULL         |
| 18          | peach screening waste    | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | NULL       | NULL       | 116,918.0          | NULL           | NULL         | NULL         | NULL         |
| 19          | tomato pomace            | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | 0.03       | 0.04       | 0.05       | 2,917,029.0        | NULL           | 87,510.87    | 116,681.16   | 145,851.45   |
| 19          | tomato pomace            | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | 0.03       | 0.04       | 0.05       | 2,270,955.0        | NULL           | 68,128.65    | 90,838.2     | 113,547.75   |
| 21          | corn stover cobs         | census_production_based | tons            | dry_tons     | 2017         | 3         | 3            | 0.123      | 0.153      | 0.183      | 4,517,173.0        | NULL           | 555,612.28   | 691,127.47   | 826,642.66   |
| 21          | corn stover cobs         | census_production_based | tons            | dry_tons     | 2022         | 3         | 3            | 0.123      | 0.153      | 0.183      | 5,216,315.0        | NULL           | 641,606.75   | 798,096.2    | 954,585.65   |
| 22          | grape pomace             | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | 0.2        | 0.25       | 0.3        | 876,780.0          | NULL           | 175,356.0    | 219,195.0    | 263,034.0    |
| 22          | grape pomace             | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | 0.2        | 0.25       | 0.3        | 757,146.0          | NULL           | 151,429.2    | 189,286.5    | 227,143.8    |
| 23          | grape stem               | acreage_based           | acres           | dry_tons     | 2017         | 3         | 3            | NULL       | NULL       | NULL       | NULL               | NULL           | NULL         | NULL         | NULL         |
| 23          | grape stem               | acreage_based           | acres           | dry_tons     | 2022         | 3         | 3            | NULL       | NULL       | NULL       | NULL               | NULL           | NULL         | NULL         | NULL         |
| 24          | pistachio stems & leaves | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | NULL       | NULL       | 36,747.0           | NULL           | NULL         | NULL         | NULL         |
| 24          | pistachio stems & leaves | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | NULL       | NULL       | 31,211.0           | NULL           | NULL         | NULL         | NULL         |
| 26          | corn stover stalks       | census_production_based | tons            | dry_tons     | 2017         | 3         | 3            | 0.458      | 0.571      | 0.684      | 4,517,173.0        | NULL           | 2,068,865.23 | 2,579,305.78 | 3,089,746.33 |
| 26          | corn stover stalks       | census_production_based | tons            | dry_tons     | 2022         | 3         | 3            | 0.458      | 0.571      | 0.684      | 5,216,315.0        | NULL           | 2,389,072.27 | 2,978,515.87 | 3,567,959.46 |
| 27          | walnut shells            | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | 1.494      | NULL       | 242,318.0          | NULL           | NULL         | 362,023.09   | NULL         |
| 27          | walnut shells            | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | 1.494      | NULL       | 182,324.0          | NULL           | NULL         | 272,392.06   | NULL         |
| 28          | sweet potato culls       | production_based        | tons            | dry_tons     | 2023         | 2         | 2            | 0.25       | 0.406      | 0.563      | 332,554.0          | NULL           | 83,138.5     | 135,016.92   | 187,227.9    |
| 28          | sweet potato culls       | production_based        | tons            | dry_tons     | 2024         | 2         | 2            | 0.25       | 0.406      | 0.563      | 259,374.0          | NULL           | 64,843.5     | 105,305.84   | 146,027.56   |
| 29          | peach pomace             | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | 0.24       | NULL       | 133,229.0          | NULL           | NULL         | 31,974.96    | NULL         |
| 29          | peach pomace             | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | 0.24       | NULL       | 116,918.0          | NULL           | NULL         | 28,060.32    | NULL         |
| 30          | olive pomace             | production_based        | tons            | dry_tons     | 2023         | 2         | 2            | NULL       | 0.35       | NULL       | 15,170.0           | NULL           | NULL         | 5,309.5      | NULL         |
| 30          | olive pomace             | production_based        | tons            | dry_tons     | 2024         | 2         | 2            | NULL       | 0.35       | NULL       | 28,235.0           | NULL           | NULL         | 9,882.25     | NULL         |
| 31          | peach stems / leaves     | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | NULL       | NULL       | 133,229.0          | NULL           | NULL         | NULL         | NULL         |
| 31          | peach stems / leaves     | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | NULL       | NULL       | 116,918.0          | NULL           | NULL         | NULL         | NULL         |
| 32          | almond hulls             | commodity_direct        | tons            | tons         | 2023         | 3         | 3            | NULL       | 1.0        | NULL       | 1,009,416.0        | NULL           | 1,009,416.0  | 1,009,416.0  | 1,009,416.0  |
| 32          | almond hulls             | commodity_direct        | tons            | tons         | 2024         | 3         | 3            | NULL       | 1.0        | NULL       | 976,054.0          | NULL           | 976,054.0    | 976,054.0    | 976,054.0    |
| 33          | corn stover husks        | census_production_based | tons            | dry_tons     | 2017         | 3         | 3            | 0.065      | 0.082      | 0.098      | 4,517,173.0        | NULL           | 293,616.25   | 370,408.19   | 442,682.95   |
| 33          | corn stover husks        | census_production_based | tons            | dry_tons     | 2022         | 3         | 3            | 0.065      | 0.082      | 0.098      | 5,216,315.0        | NULL           | 339,060.48   | 427,737.83   | 511,198.87   |
| 35          | pistachio hulls          | production_based        | tons            | dry_tons     | 2023         | 3         | 3            | NULL       | 0.147      | NULL       | 36,747.0           | NULL           | NULL         | 5,401.81     | NULL         |
| 35          | pistachio hulls          | production_based        | tons            | dry_tons     | 2024         | 3         | 3            | NULL       | 0.147      | NULL       | 31,211.0           | NULL           | NULL         | 4,588.02     | NULL         |
| 36          | rice hulls               | production_based        | tons            | dry_tons     | 2023         | 1         | 1            | 0.18       | 0.235      | 0.29       | 55,800.0           | NULL           | 10,044.0     | 13,113.0     | 16,182.0     |
| 36          | rice hulls               | production_based        | tons            | dry_tons     | 2024         | 1         | 1            | 0.18       | 0.235      | 0.29       | 58,600.0           | NULL           | 10,548.0     | 13,771.0     | 16,994.0     |

_Total rows: 56_

### 6.2 `data_portal.mv_biomass_volume_estimate` Totals & Per-Year Columns by Resource and Volume Source

```sql
SELECT
            resource_id,
            resource_name,
            volume_source,
            production_unit,
            biomass_unit,
            COUNT(*) AS total_rows,
            COUNT(estimated_residue_volume_mid) AS non_null_rows,
            MIN(dataset_year) AS min_year,
            MAX(dataset_year) AS max_year,
            ROUND(SUM(production_volume)::numeric, 2) AS total_prod_vol,
            ROUND(SUM(estimated_residue_volume_mid)::numeric, 2) AS total_res_mid,
            ROUND(SUM(CASE WHEN dataset_year = 2017 THEN estimated_residue_volume_mid END)::numeric, 2) AS res_mid_2017,
            ROUND(SUM(CASE WHEN dataset_year = 2022 THEN estimated_residue_volume_mid END)::numeric, 2) AS res_mid_2022,
            ROUND(SUM(CASE WHEN dataset_year = 2023 THEN estimated_residue_volume_mid END)::numeric, 2) AS res_mid_2023,
            ROUND(SUM(CASE WHEN dataset_year = 2024 THEN estimated_residue_volume_mid END)::numeric, 2) AS res_mid_2024,
            ROUND(SUM(CASE WHEN dataset_year = 2023 THEN production_volume END)::numeric, 2) AS prod_vol_2023,
            ROUND(SUM(CASE WHEN dataset_year = 2024 THEN production_volume END)::numeric, 2) AS prod_vol_2024
        FROM data_portal.mv_biomass_volume_estimate
        GROUP BY resource_id, resource_name, volume_source, production_unit, biomass_unit
        ORDER BY resource_id, volume_source;
```

| resource_id | resource_name            | volume_source           | production_unit | biomass_unit | total_rows | non_null_rows | min_year | max_year | total_prod_vol | total_res_mid | res_mid_2017 | res_mid_2022 | res_mid_2023 | res_mid_2024 | prod_vol_2023 | prod_vol_2024 |
| ----------- | ------------------------ | ----------------------- | --------------- | ------------ | ---------- | ------------- | -------- | -------- | -------------- | ------------- | ------------ | ------------ | ------------ | ------------ | ------------- | ------------- |
| 2           | rice straw               | production_based        | tons            | dry_tons     | 2          | 2             | 2023     | 2024     | 114,400.0      | 120,120.0     | NULL         | NULL         | 58,590.0     | 61,530.0     | 55,800.0      | 58,600.0      |
| 5           | almond shells            | commodity_direct        | tons            | tons         | 6          | 6             | 2023     | 2024     | 866,928.0      | 866,928.0     | NULL         | NULL         | 466,374.0    | 400,554.0    | 466,374.0     | 400,554.0     |
| 6           | cotton stem mix          | acreage_based           | acres           | dry_tons     | 2          | 0             | 2017     | 2022     | NULL           | NULL          | NULL         | NULL         | NULL         | NULL         | NULL          | NULL          |
| 7           | grape vines              | production_based        | tons            | dry_tons     | 6          | 0             | 2023     | 2024     | 1,633,926.0    | NULL          | NULL         | NULL         | NULL         | NULL         | 876,780.0     | 757,146.0     |
| 7           | grape vines              | prune_acres             | acres           | dry_tons     | 6          | 0             | 2017     | 2022     | NULL           | NULL          | NULL         | NULL         | NULL         | NULL         | NULL          | NULL          |
| 8           | walnut shelling fines    | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 424,642.0      | 634,415.15    | NULL         | NULL         | 362,023.09   | 272,392.06   | 242,318.0     | 182,324.0     |
| 10          | pistachio shells         | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 67,958.0       | 10,193.7      | NULL         | NULL         | 5,512.05     | 4,681.65     | 36,747.0      | 31,211.0      |
| 12          | corn stover whole        | census_production_based | tons            | dry_tons     | 6          | 6             | 2017     | 2022     | 9,733,488.0    | 9,928,157.76  | 4,607,516.46 | 5,320,641.3  | NULL         | NULL         | NULL          | NULL          |
| 14          | walnut hulls             | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 424,642.0      | 222,512.41    | NULL         | NULL         | 126,974.63   | 95,537.78    | 242,318.0     | 182,324.0     |
| 15          | walnut tree sticks       | acreage_based           | acres           | dry_tons     | 6          | 0             | 2017     | 2022     | NULL           | NULL          | NULL         | NULL         | NULL         | NULL         | NULL          | NULL          |
| 16          | almond branches          | acreage_based           | acres           | dry_tons     | 6          | 0             | 2017     | 2022     | NULL           | NULL          | NULL         | NULL         | NULL         | NULL         | NULL          | NULL          |
| 17          | olive stems / leaves     | production_based        | tons            | dry_tons     | 4          | 0             | 2023     | 2024     | 43,405.0       | NULL          | NULL         | NULL         | NULL         | NULL         | 15,170.0      | 28,235.0      |
| 18          | peach screening waste    | production_based        | tons            | dry_tons     | 6          | 0             | 2023     | 2024     | 250,147.0      | NULL          | NULL         | NULL         | NULL         | NULL         | 133,229.0     | 116,918.0     |
| 19          | tomato pomace            | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 5,187,984.0    | 207,519.36    | NULL         | NULL         | 116,681.16   | 90,838.2     | 2,917,029.0   | 2,270,955.0   |
| 21          | corn stover cobs         | census_production_based | tons            | dry_tons     | 6          | 6             | 2017     | 2022     | 9,733,488.0    | 1,489,223.66  | 691,127.47   | 798,096.2    | NULL         | NULL         | NULL          | NULL          |
| 22          | grape pomace             | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 1,633,926.0    | 408,481.5     | NULL         | NULL         | 219,195.0    | 189,286.5    | 876,780.0     | 757,146.0     |
| 23          | grape stem               | acreage_based           | acres           | dry_tons     | 6          | 0             | 2017     | 2022     | NULL           | NULL          | NULL         | NULL         | NULL         | NULL         | NULL          | NULL          |
| 24          | pistachio stems & leaves | production_based        | tons            | dry_tons     | 6          | 0             | 2023     | 2024     | 67,958.0       | NULL          | NULL         | NULL         | NULL         | NULL         | 36,747.0      | 31,211.0      |
| 26          | corn stover stalks       | census_production_based | tons            | dry_tons     | 6          | 6             | 2017     | 2022     | 9,733,488.0    | 5,557,821.65  | 2,579,305.78 | 2,978,515.87 | NULL         | NULL         | NULL          | NULL          |
| 27          | walnut shells            | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 424,642.0      | 634,415.15    | NULL         | NULL         | 362,023.09   | 272,392.06   | 242,318.0     | 182,324.0     |
| 28          | sweet potato culls       | production_based        | tons            | dry_tons     | 4          | 4             | 2023     | 2024     | 591,928.0      | 240,322.77    | NULL         | NULL         | 135,016.92   | 105,305.84   | 332,554.0     | 259,374.0     |
| 29          | peach pomace             | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 250,147.0      | 60,035.28     | NULL         | NULL         | 31,974.96    | 28,060.32    | 133,229.0     | 116,918.0     |
| 30          | olive pomace             | production_based        | tons            | dry_tons     | 4          | 4             | 2023     | 2024     | 43,405.0       | 15,191.75     | NULL         | NULL         | 5,309.5      | 9,882.25     | 15,170.0      | 28,235.0      |
| 31          | peach stems / leaves     | production_based        | tons            | dry_tons     | 6          | 0             | 2023     | 2024     | 250,147.0      | NULL          | NULL         | NULL         | NULL         | NULL         | 133,229.0     | 116,918.0     |
| 32          | almond hulls             | commodity_direct        | tons            | tons         | 6          | 6             | 2023     | 2024     | 1,985,470.0    | 1,985,470.0   | NULL         | NULL         | 1,009,416.0  | 976,054.0    | 1,009,416.0   | 976,054.0     |
| 33          | corn stover husks        | census_production_based | tons            | dry_tons     | 6          | 6             | 2017     | 2022     | 9,733,488.0    | 798,146.02    | 370,408.19   | 427,737.83   | NULL         | NULL         | NULL          | NULL          |
| 35          | pistachio hulls          | production_based        | tons            | dry_tons     | 6          | 6             | 2023     | 2024     | 67,958.0       | 9,989.83      | NULL         | NULL         | 5,401.81     | 4,588.02     | 36,747.0      | 31,211.0      |
| 36          | rice hulls               | production_based        | tons            | dry_tons     | 2          | 2             | 2023     | 2024     | 114,400.0      | 26,884.0      | NULL         | NULL         | 13,113.0     | 13,771.0     | 55,800.0      | 58,600.0      |

_Total rows: 28_

### 6.3 `data_portal.mv_usda_county_production` by Resource and Year (5 Counties vs. 3 NSJV Counties)

In `data_portal.mv_usda_county_production` (`2017` and `2022`), 5 counties are
present (`06019` Fresno, `06029` Kern, `06047` Merced, `06077` San Joaquin,
`06099` Stanislaus).

```sql
SELECT
            resource_id,
            resource_name,
            primary_ag_product,
            volume_unit,
            biomass_unit,
            dataset_year,
            COUNT(DISTINCT geoid) AS all_counties,
            ROUND(SUM(primary_product_volume)::numeric, 2) AS all_5co_prod_vol,
            ROUND(SUM(production_acres)::numeric, 2) AS all_5co_acres,
            ROUND(SUM(calculated_estimate_volume)::numeric, 2) AS all_5co_est_vol,
            ROUND(SUM(CASE WHEN geoid IN ('06047', '06077', '06099') THEN primary_product_volume END)::numeric, 2) AS nsjv_3co_prod_vol,
            ROUND(SUM(CASE WHEN geoid IN ('06047', '06077', '06099') THEN production_acres END)::numeric, 2) AS nsjv_3co_acres,
            ROUND(SUM(CASE WHEN geoid IN ('06047', '06077', '06099') THEN calculated_estimate_volume END)::numeric, 2) AS nsjv_3co_est_vol
        FROM data_portal.mv_usda_county_production
        GROUP BY resource_id, resource_name, primary_ag_product, volume_unit, biomass_unit, dataset_year
        ORDER BY resource_id, dataset_year;
```

| resource_id | resource_name                      | primary_ag_product    | volume_unit | biomass_unit  | dataset_year | all_counties | all_5co_prod_vol | all_5co_acres | all_5co_est_vol | nsjv_3co_prod_vol | nsjv_3co_acres | nsjv_3co_est_vol |
| ----------- | ---------------------------------- | --------------------- | ----------- | ------------- | ------------ | ------------ | ---------------- | ------------- | --------------- | ----------------- | -------------- | ---------------- |
| 1           | almond woodchips                   | almonds               | NULL        | dry_tons_acre | 2017         | 44           | NULL             | 1,046,928.0   | 1,570,392.0     | NULL              | 339,550.0      | 509,325.0        |
| 1           | almond woodchips                   | almonds               | NULL        | dry_tons_acre | 2022         | 40           | NULL             | 1,363,420.0   | 2,045,130.0     | NULL              | 435,031.0      | 652,546.5        |
| 2           | rice straw                         | rice                  | cwt         | dry_tons_acre | 2017         | 13           | 33,954,061.0     | 434,714.0     | 695,542.4       | 385,501.0         | 4,353.0        | 6,964.8          |
| 2           | rice straw                         | rice                  | NULL        | dry_tons_acre | 2017         | 4            | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 2           | rice straw                         | rice                  | cwt         | dry_tons_acre | 2022         | 10           | 23,076,765.0     | 262,063.0     | 419,300.8       | 820,639.0         | 8,852.0        | 14,163.2         |
| 2           | rice straw                         | rice                  | NULL        | dry_tons_acre | 2022         | 2            | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 5           | almond shells                      | almonds               | NULL        | dry_tons_acre | 2017         | 44           | NULL             | 1,046,928.0   | NULL            | NULL              | 339,550.0      | NULL             |
| 5           | almond shells                      | almonds               | NULL        | dry_tons_acre | 2022         | 40           | NULL             | 1,363,420.0   | NULL            | NULL              | 435,031.0      | NULL             |
| 6           | cotton stem mix                    | cotton                | bales       | dry_tons_acre | 2017         | 9            | 859,200.0        | 301,031.0     | 391,340.3       | 139,394.0         | 47,766.0       | 62,095.8         |
| 6           | cotton stem mix                    | cotton                | NULL        | dry_tons_acre | 2017         | 2            | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 6           | cotton stem mix                    | cotton                | bales       | dry_tons_acre | 2022         | 6            | 455,822.0        | 137,683.0     | 178,987.9       | 108,438.0         | 33,318.0       | 43,313.4         |
| 6           | cotton stem mix                    | cotton                | NULL        | dry_tons_acre | 2022         | 5            | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 7           | grape vines                        | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | 956,420.3       | NULL              | 121,949.0      | 134,143.9        |
| 7           | grape vines                        | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | 909,008.1       | NULL              | 131,002.0      | 144,102.2        |
| 8           | walnut shelling fines              | walnuts               | NULL        | dry_tons_acre | 2017         | 46           | NULL             | 266,957.0     | NULL            | NULL              | 85,918.0       | NULL             |
| 8           | walnut shelling fines              | walnuts               | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 299,513.0     | NULL            | NULL              | 107,489.0      | NULL             |
| 9           | almond shells and hulls mix        | almonds               | NULL        | dry_tons_acre | 2017         | 44           | NULL             | 1,046,928.0   | NULL            | NULL              | 339,550.0      | NULL             |
| 9           | almond shells and hulls mix        | almonds               | NULL        | dry_tons_acre | 2022         | 40           | NULL             | 1,363,420.0   | NULL            | NULL              | 435,031.0      | NULL             |
| 10          | pistachio shells                   | pistachios            | NULL        | dry_tons_acre | 2017         | 36           | NULL             | 234,774.0     | NULL            | NULL              | 7,682.0        | NULL             |
| 10          | pistachio shells                   | pistachios            | NULL        | dry_tons_acre | 2022         | 31           | NULL             | 355,085.0     | NULL            | NULL              | 17,333.0       | NULL             |
| 12          | corn stover whole                  | corn - all            | bu          | dry_tons_acre | 2017         | 6            | 2,635,549.0      | 16,618.0      | 38,221.4        | NULL              | NULL           | NULL             |
| 12          | corn stover whole                  | corn - all            | lb          | dry_tons_acre | 2017         | 1            | 10,800.0         | NULL          | NULL            | NULL              | NULL           | NULL             |
| 12          | corn stover whole                  | corn - all            | tons        | dry_tons_acre | 2017         | 19           | 11,122,549.33    | 75,761.0      | 174,250.3       | 5,070,490.0       | 32,399.0       | 74,517.7         |
| 12          | corn stover whole                  | corn - all            | NULL        | dry_tons_acre | 2017         | 12           | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 12          | corn stover whole                  | corn - all            | bu          | dry_tons_acre | 2022         | 12           | 967,509.0        | 5,518.0       | 12,691.4        | NULL              | NULL           | NULL             |
| 12          | corn stover whole                  | corn - all            | lb          | dry_tons_acre | 2022         | 1            | 2,422.0          | 6.0           | 13.8            | NULL              | NULL           | NULL             |
| 12          | corn stover whole                  | corn - all            | tons        | dry_tons_acre | 2022         | 17           | 9,524,305.0      | 88,789.0      | 204,214.7       | 4,346,334.0       | 18,472.0       | 42,485.6         |
| 12          | corn stover whole                  | corn - all            | NULL        | dry_tons_acre | 2022         | 8            | NULL             | 89.0          | 204.7           | NULL              | NULL           | NULL             |
| 13          | unused oak stick                   | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | NULL            | NULL              | 121,949.0      | NULL             |
| 13          | unused oak stick                   | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | NULL            | NULL              | 131,002.0      | NULL             |
| 14          | walnut hulls                       | walnuts               | NULL        | dry_tons_acre | 2017         | 46           | NULL             | 266,957.0     | NULL            | NULL              | 85,918.0       | NULL             |
| 14          | walnut hulls                       | walnuts               | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 299,513.0     | NULL            | NULL              | 107,489.0      | NULL             |
| 15          | walnut tree sticks                 | walnuts               | NULL        | dry_tons_acre | 2017         | 46           | NULL             | 266,957.0     | 160,174.2       | NULL              | 85,918.0       | 51,550.8         |
| 15          | walnut tree sticks                 | walnuts               | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 299,513.0     | 179,707.8       | NULL              | 107,489.0      | 64,493.4         |
| 16          | almond branches                    | almonds               | NULL        | dry_tons_acre | 2017         | 44           | NULL             | 1,046,928.0   | 1,570,392.0     | NULL              | 339,550.0      | 509,325.0        |
| 16          | almond branches                    | almonds               | NULL        | dry_tons_acre | 2022         | 40           | NULL             | 1,363,420.0   | 2,045,130.0     | NULL              | 435,031.0      | 652,546.5        |
| 17          | olive stems / leaves               | olives - processing   | NULL        | dry_tons_acre | 2017         | 47           | NULL             | 27,258.0      | NULL            | NULL              | 3,004.0        | NULL             |
| 17          | olive stems / leaves               | olives - processing   | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 33,386.0      | NULL            | NULL              | 3,183.0        | NULL             |
| 18          | peach screening waste              | peaches               | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 39,028.0      | NULL            | NULL              | 6,880.0        | NULL             |
| 18          | peach screening waste              | peaches               | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 37,804.0      | NULL            | NULL              | 5,593.0        | NULL             |
| 20          | spent yeast                        | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | NULL            | NULL              | 121,949.0      | NULL             |
| 20          | spent yeast                        | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | NULL            | NULL              | 131,002.0      | NULL             |
| 21          | corn stover cobs                   | corn - all            | bu          | dry_tons_acre | 2017         | 6            | 2,635,549.0      | 16,618.0      | NULL            | NULL              | NULL           | NULL             |
| 21          | corn stover cobs                   | corn - all            | lb          | dry_tons_acre | 2017         | 1            | 10,800.0         | NULL          | NULL            | NULL              | NULL           | NULL             |
| 21          | corn stover cobs                   | corn - all            | tons        | dry_tons_acre | 2017         | 19           | 11,122,549.33    | 75,761.0      | NULL            | 5,070,490.0       | 32,399.0       | NULL             |
| 21          | corn stover cobs                   | corn - all            | NULL        | dry_tons_acre | 2017         | 12           | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 21          | corn stover cobs                   | corn - all            | bu          | dry_tons_acre | 2022         | 12           | 967,509.0        | 5,518.0       | NULL            | NULL              | NULL           | NULL             |
| 21          | corn stover cobs                   | corn - all            | lb          | dry_tons_acre | 2022         | 1            | 2,422.0          | 6.0           | NULL            | NULL              | NULL           | NULL             |
| 21          | corn stover cobs                   | corn - all            | tons        | dry_tons_acre | 2022         | 17           | 9,524,305.0      | 88,789.0      | NULL            | 4,346,334.0       | 18,472.0       | NULL             |
| 21          | corn stover cobs                   | corn - all            | NULL        | dry_tons_acre | 2022         | 8            | NULL             | 89.0          | NULL            | NULL              | NULL           | NULL             |
| 22          | grape pomace                       | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | NULL            | NULL              | 121,949.0      | NULL             |
| 22          | grape pomace                       | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | NULL            | NULL              | 131,002.0      | NULL             |
| 23          | grape stem                         | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | 956,420.3       | NULL              | 121,949.0      | 134,143.9        |
| 23          | grape stem                         | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | 909,008.1       | NULL              | 131,002.0      | 144,102.2        |
| 24          | pistachio stems & leaves           | pistachios            | NULL        | dry_tons_acre | 2017         | 36           | NULL             | 234,774.0     | NULL            | NULL              | 7,682.0        | NULL             |
| 24          | pistachio stems & leaves           | pistachios            | NULL        | dry_tons_acre | 2022         | 31           | NULL             | 355,085.0     | NULL            | NULL              | 17,333.0       | NULL             |
| 25          | spent oak chips                    | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | NULL            | NULL              | 121,949.0      | NULL             |
| 25          | spent oak chips                    | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | NULL            | NULL              | 131,002.0      | NULL             |
| 26          | corn stover stalks                 | corn - all            | bu          | dry_tons_acre | 2017         | 6            | 2,635,549.0      | 16,618.0      | 38,221.4        | NULL              | NULL           | NULL             |
| 26          | corn stover stalks                 | corn - all            | lb          | dry_tons_acre | 2017         | 1            | 10,800.0         | NULL          | NULL            | NULL              | NULL           | NULL             |
| 26          | corn stover stalks                 | corn - all            | tons        | dry_tons_acre | 2017         | 19           | 11,122,549.33    | 75,761.0      | 174,250.3       | 5,070,490.0       | 32,399.0       | 74,517.7         |
| 26          | corn stover stalks                 | corn - all            | NULL        | dry_tons_acre | 2017         | 12           | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 26          | corn stover stalks                 | corn - all            | bu          | dry_tons_acre | 2022         | 12           | 967,509.0        | 5,518.0       | 12,691.4        | NULL              | NULL           | NULL             |
| 26          | corn stover stalks                 | corn - all            | lb          | dry_tons_acre | 2022         | 1            | 2,422.0          | 6.0           | 13.8            | NULL              | NULL           | NULL             |
| 26          | corn stover stalks                 | corn - all            | tons        | dry_tons_acre | 2022         | 17           | 9,524,305.0      | 88,789.0      | 204,214.7       | 4,346,334.0       | 18,472.0       | 42,485.6         |
| 26          | corn stover stalks                 | corn - all            | NULL        | dry_tons_acre | 2022         | 8            | NULL             | 89.0          | 204.7           | NULL              | NULL           | NULL             |
| 27          | walnut shells                      | walnuts               | NULL        | dry_tons_acre | 2017         | 46           | NULL             | 266,957.0     | NULL            | NULL              | 85,918.0       | NULL             |
| 27          | walnut shells                      | walnuts               | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 299,513.0     | NULL            | NULL              | 107,489.0      | NULL             |
| 28          | sweet potato culls                 | sweet potatoes        | NULL        | dry_tons_acre | 2017         | 27           | NULL             | 21,296.0      | NULL            | NULL              | 20,477.0       | NULL             |
| 28          | sweet potato culls                 | sweet potatoes        | NULL        | dry_tons_acre | 2022         | 25           | NULL             | 24,047.0      | NULL            | NULL              | 23,675.0       | NULL             |
| 29          | peach pomace                       | peaches               | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 39,028.0      | NULL            | NULL              | 6,880.0        | NULL             |
| 29          | peach pomace                       | peaches               | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 37,804.0      | NULL            | NULL              | 5,593.0        | NULL             |
| 30          | olive pomace                       | olives - processing   | NULL        | dry_tons_acre | 2017         | 47           | NULL             | 27,258.0      | NULL            | NULL              | 3,004.0        | NULL             |
| 30          | olive pomace                       | olives - processing   | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 33,386.0      | NULL            | NULL              | 3,183.0        | NULL             |
| 31          | peach stems / leaves               | peaches               | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 39,028.0      | NULL            | NULL              | 6,880.0        | NULL             |
| 31          | peach stems / leaves               | peaches               | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 37,804.0      | NULL            | NULL              | 5,593.0        | NULL             |
| 32          | almond hulls                       | almonds               | NULL        | dry_tons_acre | 2017         | 44           | NULL             | 1,046,928.0   | NULL            | NULL              | 339,550.0      | NULL             |
| 32          | almond hulls                       | almonds               | NULL        | dry_tons_acre | 2022         | 40           | NULL             | 1,363,420.0   | NULL            | NULL              | 435,031.0      | NULL             |
| 33          | corn stover husks                  | corn - all            | bu          | dry_tons_acre | 2017         | 6            | 2,635,549.0      | 16,618.0      | NULL            | NULL              | NULL           | NULL             |
| 33          | corn stover husks                  | corn - all            | lb          | dry_tons_acre | 2017         | 1            | 10,800.0         | NULL          | NULL            | NULL              | NULL           | NULL             |
| 33          | corn stover husks                  | corn - all            | tons        | dry_tons_acre | 2017         | 19           | 11,122,549.33    | 75,761.0      | NULL            | 5,070,490.0       | 32,399.0       | NULL             |
| 33          | corn stover husks                  | corn - all            | NULL        | dry_tons_acre | 2017         | 12           | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 33          | corn stover husks                  | corn - all            | bu          | dry_tons_acre | 2022         | 12           | 967,509.0        | 5,518.0       | NULL            | NULL              | NULL           | NULL             |
| 33          | corn stover husks                  | corn - all            | lb          | dry_tons_acre | 2022         | 1            | 2,422.0          | 6.0           | NULL            | NULL              | NULL           | NULL             |
| 33          | corn stover husks                  | corn - all            | tons        | dry_tons_acre | 2022         | 17           | 9,524,305.0      | 88,789.0      | NULL            | 4,346,334.0       | 18,472.0       | NULL             |
| 33          | corn stover husks                  | corn - all            | NULL        | dry_tons_acre | 2022         | 8            | NULL             | 89.0          | NULL            | NULL              | NULL           | NULL             |
| 35          | pistachio hulls                    | pistachios            | NULL        | dry_tons_acre | 2017         | 36           | NULL             | 234,774.0     | NULL            | NULL              | 7,682.0        | NULL             |
| 35          | pistachio hulls                    | pistachios            | NULL        | dry_tons_acre | 2022         | 31           | NULL             | 355,085.0     | NULL            | NULL              | 17,333.0       | NULL             |
| 36          | rice hulls                         | rice                  | cwt         | dry_tons_acre | 2017         | 13           | 33,954,061.0     | 434,714.0     | NULL            | 385,501.0         | 4,353.0        | NULL             |
| 36          | rice hulls                         | rice                  | NULL        | dry_tons_acre | 2017         | 4            | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 36          | rice hulls                         | rice                  | cwt         | dry_tons_acre | 2022         | 10           | 23,076,765.0     | 262,063.0     | NULL            | 820,639.0         | 8,852.0        | NULL             |
| 36          | rice hulls                         | rice                  | NULL        | dry_tons_acre | 2022         | 2            | NULL             | NULL          | NULL            | NULL              | NULL           | NULL             |
| 37          | lees                               | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | NULL            | NULL              | 121,949.0      | NULL             |
| 37          | lees                               | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | NULL            | NULL              | 131,002.0      | NULL             |
| 38          | orange pomace                      | oranges               | NULL        | dry_tons_acre | 2017         | 39           | NULL             | 155,422.0     | NULL            | NULL              | 91.0           | NULL             |
| 38          | orange pomace                      | oranges               | NULL        | dry_tons_acre | 2022         | 43           | NULL             | 162,088.0     | NULL            | NULL              | 870.0          | NULL             |
| 39          | orange peel                        | oranges               | NULL        | dry_tons_acre | 2017         | 39           | NULL             | 155,422.0     | NULL            | NULL              | 91.0           | NULL             |
| 39          | orange peel                        | oranges               | NULL        | dry_tons_acre | 2022         | 43           | NULL             | 162,088.0     | NULL            | NULL              | 870.0          | NULL             |
| 42          | potato culls                       | potatoes              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 40,531.0      | NULL            | NULL              | 3,204.0        | NULL             |
| 42          | potato culls                       | potatoes              | NULL        | dry_tons_acre | 2022         | 42           | NULL             | 21,786.0      | NULL            | NULL              | 4,480.0        | NULL             |
| 44          | apricot peels                      | apricots              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 10,216.0      | NULL            | NULL              | 6,971.0        | NULL             |
| 44          | apricot peels                      | apricots              | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 5,275.0       | NULL            | NULL              | 2,800.0        | NULL             |
| 45          | apricot pomace                     | apricots              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 10,216.0      | NULL            | NULL              | 6,971.0        | NULL             |
| 45          | apricot pomace                     | apricots              | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 5,275.0       | NULL            | NULL              | 2,800.0        | NULL             |
| 46          | apricot seeds                      | apricots              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 10,216.0      | NULL            | NULL              | 6,971.0        | NULL             |
| 46          | apricot seeds                      | apricots              | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 5,275.0       | NULL            | NULL              | 2,800.0        | NULL             |
| 47          | apricot stems / leaves             | apricots              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 10,216.0      | 15,324.0        | NULL              | 6,971.0        | 10,456.5         |
| 47          | apricot stems / leaves             | apricots              | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 5,275.0       | 7,912.5         | NULL              | 2,800.0        | 4,200.0          |
| 48          | apricot rejects                    | apricots              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 10,216.0      | NULL            | NULL              | 6,971.0        | NULL             |
| 48          | apricot rejects                    | apricots              | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 5,275.0       | NULL            | NULL              | 2,800.0        | NULL             |
| 49          | nectarine peels                    | nectarines            | NULL        | dry_tons_acre | 2017         | 41           | NULL             | 14,396.0      | NULL            | NULL              | 180.0          | NULL             |
| 49          | nectarine peels                    | nectarines            | NULL        | dry_tons_acre | 2022         | 41           | NULL             | 15,743.0      | NULL            | NULL              | 135.0          | NULL             |
| 50          | nectarine pomace                   | nectarines            | NULL        | dry_tons_acre | 2017         | 41           | NULL             | 14,396.0      | NULL            | NULL              | 180.0          | NULL             |
| 50          | nectarine pomace                   | nectarines            | NULL        | dry_tons_acre | 2022         | 41           | NULL             | 15,743.0      | NULL            | NULL              | 135.0          | NULL             |
| 51          | nectarine seeds                    | nectarines            | NULL        | dry_tons_acre | 2017         | 41           | NULL             | 14,396.0      | NULL            | NULL              | 180.0          | NULL             |
| 51          | nectarine seeds                    | nectarines            | NULL        | dry_tons_acre | 2022         | 41           | NULL             | 15,743.0      | NULL            | NULL              | 135.0          | NULL             |
| 52          | nectarine stems / leaves           | nectarines            | NULL        | dry_tons_acre | 2017         | 41           | NULL             | 14,396.0      | NULL            | NULL              | 180.0          | NULL             |
| 52          | nectarine stems / leaves           | nectarines            | NULL        | dry_tons_acre | 2022         | 41           | NULL             | 15,743.0      | NULL            | NULL              | 135.0          | NULL             |
| 53          | nectarine rejects                  | nectarines            | NULL        | dry_tons_acre | 2017         | 41           | NULL             | 14,396.0      | NULL            | NULL              | 180.0          | NULL             |
| 53          | nectarine rejects                  | nectarines            | NULL        | dry_tons_acre | 2022         | 41           | NULL             | 15,743.0      | NULL            | NULL              | 135.0          | NULL             |
| 54          | peach peels                        | peaches               | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 39,028.0      | NULL            | NULL              | 6,880.0        | NULL             |
| 54          | peach peels                        | peaches               | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 37,804.0      | NULL            | NULL              | 5,593.0        | NULL             |
| 55          | peach seeds                        | peaches               | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 39,028.0      | NULL            | NULL              | 6,880.0        | NULL             |
| 55          | peach seeds                        | peaches               | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 37,804.0      | NULL            | NULL              | 5,593.0        | NULL             |
| 56          | peach rejects                      | peaches               | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 39,028.0      | NULL            | NULL              | 6,880.0        | NULL             |
| 56          | peach rejects                      | peaches               | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 37,804.0      | NULL            | NULL              | 5,593.0        | NULL             |
| 57          | plum peels                         | plums & prunes        | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 10,305.0      | NULL            | NULL              | 41.0           | NULL             |
| 57          | plum peels                         | plums & prunes        | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 11,093.0      | NULL            | NULL              | 78.0           | NULL             |
| 58          | plum pomace                        | plums & prunes        | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 10,305.0      | NULL            | NULL              | 41.0           | NULL             |
| 58          | plum pomace                        | plums & prunes        | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 11,093.0      | NULL            | NULL              | 78.0           | NULL             |
| 59          | plum seeds                         | plums & prunes        | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 10,305.0      | NULL            | NULL              | 41.0           | NULL             |
| 59          | plum seeds                         | plums & prunes        | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 11,093.0      | NULL            | NULL              | 78.0           | NULL             |
| 60          | plum stems / leaves                | plums & prunes        | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 10,305.0      | NULL            | NULL              | 41.0           | NULL             |
| 60          | plum stems / leaves                | plums & prunes        | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 11,093.0      | NULL            | NULL              | 78.0           | NULL             |
| 61          | plum rejects                       | plums & prunes        | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 10,305.0      | NULL            | NULL              | 41.0           | NULL             |
| 61          | plum rejects                       | plums & prunes        | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 11,093.0      | NULL            | NULL              | 78.0           | NULL             |
| 68          | pear peels                         | pears                 | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 5,838.0       | NULL            | NULL              | 147.0          | NULL             |
| 68          | pear peels                         | pears                 | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 2,095.0       | NULL            | NULL              | NULL           | NULL             |
| 69          | pear pomace                        | pears                 | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 5,838.0       | NULL            | NULL              | 147.0          | NULL             |
| 69          | pear pomace                        | pears                 | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 2,095.0       | NULL            | NULL              | NULL           | NULL             |
| 70          | pear rejects                       | pears                 | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 5,838.0       | NULL            | NULL              | 147.0          | NULL             |
| 70          | pear rejects                       | pears                 | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 2,095.0       | NULL            | NULL              | NULL           | NULL             |
| 71          | pear seeds                         | pears                 | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 5,838.0       | NULL            | NULL              | 147.0          | NULL             |
| 71          | pear seeds                         | pears                 | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 2,095.0       | NULL            | NULL              | NULL           | NULL             |
| 72          | pear stems / leaves                | pears                 | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 5,838.0       | NULL            | NULL              | 147.0          | NULL             |
| 72          | pear stems / leaves                | pears                 | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 2,095.0       | NULL            | NULL              | NULL           | NULL             |
| 73          | apricot screening waste            | apricots              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 10,216.0      | NULL            | NULL              | 6,971.0        | NULL             |
| 73          | apricot screening waste            | apricots              | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 5,275.0       | NULL            | NULL              | 2,800.0        | NULL             |
| 74          | nectarine screening waste          | nectarines            | NULL        | dry_tons_acre | 2017         | 41           | NULL             | 14,396.0      | NULL            | NULL              | 180.0          | NULL             |
| 74          | nectarine screening waste          | nectarines            | NULL        | dry_tons_acre | 2022         | 41           | NULL             | 15,743.0      | NULL            | NULL              | 135.0          | NULL             |
| 75          | pear screening waste               | pears                 | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 5,838.0       | NULL            | NULL              | 147.0          | NULL             |
| 75          | pear screening waste               | pears                 | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 2,095.0       | NULL            | NULL              | NULL           | NULL             |
| 77          | plum screening waste               | plums & prunes        | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 10,305.0      | NULL            | NULL              | 41.0           | NULL             |
| 77          | plum screening waste               | plums & prunes        | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 11,093.0      | NULL            | NULL              | 78.0           | NULL             |
| 78          | apricot off-spec canned products   | apricots              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 10,216.0      | NULL            | NULL              | 6,971.0        | NULL             |
| 78          | apricot off-spec canned products   | apricots              | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 5,275.0       | NULL            | NULL              | 2,800.0        | NULL             |
| 79          | nectarine off-spec canned products | nectarines            | NULL        | dry_tons_acre | 2017         | 41           | NULL             | 14,396.0      | NULL            | NULL              | 180.0          | NULL             |
| 79          | nectarine off-spec canned products | nectarines            | NULL        | dry_tons_acre | 2022         | 41           | NULL             | 15,743.0      | NULL            | NULL              | 135.0          | NULL             |
| 80          | peach off-spec canned products     | peaches               | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 39,028.0      | NULL            | NULL              | 6,880.0        | NULL             |
| 80          | peach off-spec canned products     | peaches               | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 37,804.0      | NULL            | NULL              | 5,593.0        | NULL             |
| 81          | pear off-spec canned products      | pears                 | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 5,838.0       | NULL            | NULL              | 147.0          | NULL             |
| 81          | pear off-spec canned products      | pears                 | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 2,095.0       | NULL            | NULL              | NULL           | NULL             |
| 83          | plum off-spec canned products      | plums & prunes        | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 10,305.0      | NULL            | NULL              | 41.0           | NULL             |
| 83          | plum off-spec canned products      | plums & prunes        | NULL        | dry_tons_acre | 2022         | 50           | NULL             | 11,093.0      | NULL            | NULL              | 78.0           | NULL             |
| 84          | cucumber culls                     | cucumbers and pickles | NULL        | dry_tons_acre | 2017         | 51           | NULL             | 7,929.0       | 1,585.8         | NULL              | 3,657.0        | 731.4            |
| 84          | cucumber culls                     | cucumbers and pickles | NULL        | dry_tons_acre | 2022         | 51           | NULL             | 6,353.0       | 1,270.6         | NULL              | 2,643.0        | 528.6            |
| 85          | walnut waste kernels               | walnuts               | NULL        | dry_tons_acre | 2017         | 46           | NULL             | 266,957.0     | NULL            | NULL              | 85,918.0       | NULL             |
| 85          | walnut waste kernels               | walnuts               | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 299,513.0     | NULL            | NULL              | 107,489.0      | NULL             |
| 86          | walnut hulling discharge           | walnuts               | NULL        | dry_tons_acre | 2017         | 46           | NULL             | 266,957.0     | NULL            | NULL              | 85,918.0       | NULL             |
| 86          | walnut hulling discharge           | walnuts               | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 299,513.0     | NULL            | NULL              | 107,489.0      | NULL             |
| 88          | potato culls-red                   | potatoes              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 40,531.0      | NULL            | NULL              | 3,204.0        | NULL             |
| 88          | potato culls-red                   | potatoes              | NULL        | dry_tons_acre | 2022         | 42           | NULL             | 21,786.0      | NULL            | NULL              | 4,480.0        | NULL             |
| 89          | potato culls-yellow                | potatoes              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 40,531.0      | NULL            | NULL              | 3,204.0        | NULL             |
| 89          | potato culls-yellow                | potatoes              | NULL        | dry_tons_acre | 2022         | 42           | NULL             | 21,786.0      | NULL            | NULL              | 4,480.0        | NULL             |
| 90          | potato culls-white                 | potatoes              | NULL        | dry_tons_acre | 2017         | 45           | NULL             | 40,531.0      | NULL            | NULL              | 3,204.0        | NULL             |
| 90          | potato culls-white                 | potatoes              | NULL        | dry_tons_acre | 2022         | 42           | NULL             | 21,786.0      | NULL            | NULL              | 4,480.0        | NULL             |
| 91          | diatomaceous earth from winemaking | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | NULL            | NULL              | 121,949.0      | NULL             |
| 91          | diatomaceous earth from winemaking | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | NULL            | NULL              | 131,002.0      | NULL             |
| 92          | spent oak stick                    | grapes                | NULL        | dry_tons_acre | 2017         | 52           | NULL             | 869,473.0     | NULL            | NULL              | 121,949.0      | NULL             |
| 92          | spent oak stick                    | grapes                | NULL        | dry_tons_acre | 2022         | 53           | NULL             | 826,371.0     | NULL            | NULL              | 131,002.0      | NULL             |
| 93          | almond stick char                  | almonds               | NULL        | dry_tons_acre | 2017         | 44           | NULL             | 1,046,928.0   | NULL            | NULL              | 339,550.0      | NULL             |
| 93          | almond stick char                  | almonds               | NULL        | dry_tons_acre | 2022         | 40           | NULL             | 1,363,420.0   | NULL            | NULL              | 435,031.0      | NULL             |
| 94          | walnut shelling debris             | walnuts               | NULL        | dry_tons_acre | 2017         | 46           | NULL             | 266,957.0     | NULL            | NULL              | 85,918.0       | NULL             |
| 94          | walnut shelling debris             | walnuts               | NULL        | dry_tons_acre | 2022         | 47           | NULL             | 299,513.0     | NULL            | NULL              | 107,489.0      | NULL             |
| 95          | olive prunings                     | olives - processing   | NULL        | dry_tons_acre | 2017         | 47           | NULL             | 27,258.0      | 19,080.6        | NULL              | 3,004.0        | 2,102.8          |
| 95          | olive prunings                     | olives - processing   | NULL        | dry_tons_acre | 2022         | 46           | NULL             | 33,386.0      | 23,370.2        | NULL              | 3,183.0        | 2,228.1          |

_Total rows: 186_

### 6.4 USDA Census `CORN` (`commodity_code = 6`) Observations in NSJV (`2017` & `2022`)

In `public.usda_census_record`, `commodity_code = 6` (`CORN`) combines grain
corn (`obs.unit_id = 18` `'bushels'`) and silage corn (`obs.unit_id = 1`
`'tons'`) under the same `parameter_id = 1` (`production`). Because Path E
(`census_production_based`, line 404) filters
`Observation.unit_id == _tons_unit_id` (`1`), it selects the **wet corn silage
tonnage** (`4,517,173.0 t` in 2017; `5,216,315.0 t` in 2022) and multiplies it
by grain-to-stover residue factors (`1.02`, `0.571`, `0.153`, `0.082`):

```sql
SELECT
            ucr.id AS ucr_id,
            ucr.geoid,
            p.county_name,
            ucr.year,
            param.id AS param_id,
            param.name AS param_name,
            u.id AS unit_id,
            u.name AS unit_name,
            obs.value
        FROM public.usda_census_record ucr
        JOIN public.place p ON ucr.geoid = p.geoid
        JOIN public.observation obs ON obs.record_id = CAST(ucr.id AS VARCHAR) AND obs.record_type = 'usda_census_record'
        JOIN public.parameter param ON obs.parameter_id = param.id
        JOIN public.unit u ON obs.unit_id = u.id
        WHERE ucr.commodity_code = 6
          AND lower(p.county_name) IN ('san joaquin', 'stanislaus', 'merced')
        ORDER BY ucr.year, p.county_name, param.name, u.name;
```

| ucr_id | geoid | county_name | year | param_id | param_name     | unit_id | unit_name  | value   |
| ------ | ----- | ----------- | ---- | -------- | -------------- | ------- | ---------- | ------- |
| 1461   | 06047 | merced      | 1997 | 3        | area harvested | 19      | acres      | 25.0    |
| 1461   | 06047 | merced      | 1997 | 3        | area harvested | 23      | operations | 13.0    |
| 1467   | 06077 | san joaquin | 1997 | 3        | area harvested | 19      | acres      | 3,455.0 |
| 1467   | 06077 | san joaquin | 1997 | 3        | area harvested | 23      | operations | 35.0    |
| 1599   | 06099 | stanislaus  | 1997 | 3        | area harvested | 23      | operations | 5.0     |
| 1460   | 06047 | merced      | 2002 | 3        | area harvested | 19      | acres      | 357.0   |
| 1460   | 06047 | merced      | 2002 | 3        | area harvested | 23      | operations | 8.0     |
| 1466   | 06077 | san joaquin | 2002 | 3        | area harvested | 19      | acres      | 4,233.0 |
| 1466   | 06077 | san joaquin | 2002 | 3        | area harvested | 23      | operations | 27.0    |
| 1472   | 06099 | stanislaus  | 2002 | 3        | area harvested | 19      | acres      | 4.0     |
| 1472   | 06099 | stanislaus  | 2002 | 3        | area harvested | 23      | operations | 7.0     |
| 1459   | 06047 | merced      | 2007 | 3        | area harvested | 19      | acres      | 454.0   |
| 1459   | 06047 | merced      | 2007 | 3        | area harvested | 23      | operations | 10.0    |
| 1465   | 06077 | san joaquin | 2007 | 3        | area harvested | 19      | acres      | 3,547.0 |
| 1465   | 06077 | san joaquin | 2007 | 3        | area harvested | 23      | operations | 21.0    |
| 1471   | 06099 | stanislaus  | 2007 | 3        | area harvested | 19      | acres      | 2.0     |
| 1471   | 06099 | stanislaus  | 2007 | 3        | area harvested | 23      | operations | 7.0     |
| 1458   | 06047 | merced      | 2012 | 3        | area harvested | 19      | acres      | 20.0    |
| 1458   | 06047 | merced      | 2012 | 3        | area harvested | 23      | operations | 17.0    |
| 1464   | 06077 | san joaquin | 2012 | 3        | area harvested | 19      | acres      | 2,848.0 |
| 1464   | 06077 | san joaquin | 2012 | 3        | area harvested | 23      | operations | 34.0    |
| 1470   | 06099 | stanislaus  | 2012 | 3        | area harvested | 19      | acres      | 6.0     |
| 1470   | 06099 | stanislaus  | 2012 | 3        | area harvested | 23      | operations | 8.0     |
| 1457   | 06047 | merced      | 2017 | 3        | area harvested | 19      | acres      | 54.0    |
| 1457   | 06047 | merced      | 2017 | 3        | area harvested | 23      | operations | 33.0    |
| 1463   | 06077 | san joaquin | 2017 | 3        | area harvested | 19      | acres      | 3,599.0 |
| 1463   | 06077 | san joaquin | 2017 | 3        | area harvested | 23      | operations | 33.0    |
| 1469   | 06099 | stanislaus  | 2017 | 3        | area harvested | 19      | acres      | 4.0     |
| 1469   | 06099 | stanislaus  | 2017 | 3        | area harvested | 23      | operations | 10.0    |
| 1456   | 06047 | merced      | 2022 | 3        | area harvested | 19      | acres      | 17.0    |
| 1456   | 06047 | merced      | 2022 | 3        | area harvested | 23      | operations | 10.0    |
| 1462   | 06077 | san joaquin | 2022 | 3        | area harvested | 19      | acres      | 2,621.0 |
| 1462   | 06077 | san joaquin | 2022 | 3        | area harvested | 23      | operations | 21.0    |
| 1468   | 06099 | stanislaus  | 2022 | 3        | area harvested | 19      | acres      | 5.0     |
| 1468   | 06099 | stanislaus  | 2022 | 3        | area harvested | 23      | operations | 10.0    |

_Total rows: 35_

---

## 7. Complete `public.residue_factor` Table (`39` Rows)

```sql
SELECT
            rf.id AS rf_id,
            rf.resource_id,
            rf.resource_name,
            r.name AS joined_resource_name,
            r.primary_ag_product_id,
            pap.name AS pap_name,
            rf.factor_type,
            rf.factor_min,
            rf.factor_mid,
            rf.factor_max,
            rf.prune_trim_yield,
            rf.prune_trim_yield_unit_id,
            u.name AS prune_unit_name,
            rf.data_source_id,
            rf.notes
        FROM public.residue_factor rf
        LEFT JOIN public.resource r ON rf.resource_id = r.id
        LEFT JOIN public.primary_ag_product pap ON r.primary_ag_product_id = pap.id
        LEFT JOIN public.unit u ON rf.prune_trim_yield_unit_id = u.id
        ORDER BY rf.id;
```

| rf_id | resource_id | resource_name               | joined_resource_name        | primary_ag_product_id | pap_name                | factor_type | factor_min | factor_mid | factor_max | prune_trim_yield | prune_trim_yield_unit_id | prune_unit_name | data_source_id | notes                                                                                                                                                                                                                       |
| ----- | ----------- | --------------------------- | --------------------------- | --------------------- | ----------------------- | ----------- | ---------- | ---------- | ---------- | ---------------- | ------------------------ | --------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | 11          | alfalfa                     | alfalfa                     | 3                     | hay - alfalfa           | commodity   | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 2     | 16          | almond branches             | almond branches             | 2                     | almonds                 | area        | NULL       | NULL       | NULL       | 1.5              | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 3     | 32          | almond hulls                | almond hulls                | 2                     | almonds                 | commodity   | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 4     | 5           | almond shells               | almond shells               | 2                     | almonds                 | commodity   | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 5     | 9           | almond shells and hulls mix | almond shells and hulls mix | 2                     | almonds                 | weight      | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | can't estimate from residue factors                                                                                                                                                                                         |
| 6     | 1           | almond woodchips            | almond woodchips            | 2                     | almonds                 | weight      | NULL       | NULL       | NULL       | 1.5              | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 7     | 21          | corn stover cobs            | corn stover cobs            | 16                    | corn - all              | weight      | 0.123      | 0.153      | 0.183      | NULL             | NULL                     | NULL            | NULL           | based on 45-55% range of grain as total harvest. stover fractions listed as 15% cob, 8% husk, 56% stalk (also 21% leaf)                                                                                                     |
| 8     | 33          | corn stover husks           | corn stover husks           | 16                    | corn - all              | weight      | 0.065      | 0.082      | 0.098      | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 9     | 26          | corn stover stalks          | corn stover stalks          | 16                    | corn - all              | weight      | 0.458      | 0.571      | 0.684      | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 10    | 12          | corn stover whole           | corn stover whole           | 16                    | corn - all              | weight      | 0.818      | 1.02       | 1.222      | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 11    | 6           | cotton stem mix             | cotton stem mix             | 26                    | cotton                  | area        | NULL       | NULL       | NULL       | 1.2              | NULL                     | NULL            | NULL           | assumed the average mc of 42%                                                                                                                                                                                               |
| 12    | 22          | grape pomace                | grape pomace                | 23                    | grapes                  | weight      | 0.2        | 0.25       | 0.3        | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 13    | 23          | grape stem                  | grape stem                  | 23                    | grapes                  | area        | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | it sounds like grapes are destemmed while harvesting, unclear if fraser's data reflects that or not. stems make up 3-7% of the bunch weight prior to destemming based on https://pmc.ncbi.nlm.nih.gov/articles/pmc7956323/. |
| 14    | 4           | grape vine prunings         | grape vine prunings         | 23                    | grapes                  | area        | NULL       | NULL       | NULL       | 1.1              | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 15    | 7           | grape vines                 | grape vines                 | 23                    | grapes                  | weight      | NULL       | NULL       | NULL       | 1.1              | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 16    | 37          | lees                        | lees                        | 23                    | grapes                  | null        | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | can't estimate from residue factors                                                                                                                                                                                         |
| 17    | 30          | olive pomace                | olive pomace                | 20                    | olives - processing     | weight      | NULL       | 0.35       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 18    | 17          | olive stems / leaves        | olive stems / leaves        | 20                    | olives - processing     | weight      | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | can't find this                                                                                                                                                                                                             |
| 19    | 29          | peach pomace                | peach pomace                | 12                    | peaches                 | weight      | NULL       | 0.24       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 20    | 18          | peach screening waste       | peach screening waste       | 12                    | peaches                 | weight      | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | need to know more about what this is (pits/skins? culls? pomace + pits + skins?)                                                                                                                                            |
| 21    | 31          | peach stems / leaves        | peach stems / leaves        | 12                    | peaches                 | weight      | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | can't find this                                                                                                                                                                                                             |
| 22    | 35          | pistachio hulls             | pistachio hulls             | 8                     | pistachios              | weight      | NULL       | 0.147      | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 23    | 10          | pistachio shells            | pistachio shells            | 8                     | pistachios              | weight      | NULL       | 0.15       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 24    | 24          | pistachio stems & leaves    | pistachio stems & leaves    | 8                     | pistachios              | weight      | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | can't find this                                                                                                                                                                                                             |
| 25    | 36          | rice hulls                  | rice hulls                  | 1                     | rice                    | weight      | 0.18       | 0.235      | 0.29       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 26    | 2           | rice straw                  | rice straw                  | 1                     | rice                    | weight      | 0.7        | 1.05       | 1.4        | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 27    | 3           | sargassum                   | sargassum                   | 5                     | sargassum               | null        | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | collaboration samples, amount produced in nsjv will be 0                                                                                                                                                                    |
| 28    | 25          | spent oak chips             | spent oak chips             | 23                    | grapes                  | null        | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | can't estimate from residue factors                                                                                                                                                                                         |
| 29    | 20          | spent yeast                 | spent yeast                 | 23                    | grapes                  | null        | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | can't estimate from residue factors                                                                                                                                                                                         |
| 30    | 28          | sweet potato culls          | sweet potato culls          | 9                     | sweet potatoes          | weight      | 0.25       | 0.406      | 0.563      | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 31    | 19          | tomato pomace               | tomato pomace               | 29                    | tomatoes for processing | weight      | 0.03       | 0.04       | 0.05       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 32    | 13          | unused oak stick            | unused oak stick            | 23                    | grapes                  | null        | NULL       | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 33    | 14          | walnut hulls                | walnut hulls                | 6                     | walnuts                 | weight      | NULL       | 0.524      | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 34    | 8           | walnut shelling fines       | walnut shelling fines       | 6                     | walnuts                 | weight      | NULL       | 1.494      | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 35    | 27          | walnut shells               | walnut shells               | 6                     | walnuts                 | weight      | NULL       | 1.494      | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 36    | 15          | walnut tree sticks          | walnut tree sticks          | 6                     | walnuts                 | area        | NULL       | NULL       | NULL       | 0.6              | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 37    | 34          | wheat straw                 | wheat straw                 | 25                    | winter wheat            | area        | 0.6        | 0.7        | 0.8        | NULL             | NULL                     | NULL            | NULL           | this is residue available after bailing, more may be left on the ground but collecting sounds impractical.                                                                                                                  |
| 38    | 1           | NULL                        | almond woodchips            | 2                     | almonds                 | commodity   | 0.1        | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |
| 39    | 3           | NULL                        | sargassum                   | 5                     | sargassum               | weight      | 0.3        | NULL       | NULL       | NULL             | NULL                     | NULL            | NULL           | NULL                                                                                                                                                                                                                        |

_Total rows: 39_
