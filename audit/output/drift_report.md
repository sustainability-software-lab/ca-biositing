# BioCirV — Multi-Environment Database Drift Assessment Report (`local` · `staging` · `production`)

**Generated UTC:** `2026-10-18 18:50:03 UTC` **Interactive Dashboard:**
`exports/plots/audit/db_environment_drift_dashboard.html` **Generator CLI:**
`pixi run python analysis/audit/db_environment_drift.py --extract-env local staging production --compare`

---

## 1. Executive Environment Summary & Sync Scorecard

| Dimension                            | Local Dev (`:5432`)            | Staging (`:5434` Proxy)                                        | Production (`:5435` Proxy)                             | Drift Status                                |
| :----------------------------------- | :----------------------------- | :------------------------------------------------------------- | :----------------------------------------------------- | :------------------------------------------ |
| **Database Name**                    | `biocirv_db`                   | `biocirv-staging`                                              | `biocirv-production`                                   | Canonical 3-tier topology                   |
| **Capture Mode**                     | `live_db`                      | `live_db`                                                      | `127.0.0.1:5435` (`live_db`)                           | Live SQL extraction                         |
| **Alembic Revision Head**            | `0025 (live)`                  | `0024_centralize_qc_constants_across_data_portal_views (0024)` | `0021_remove_almond_meats_from_volume_estimate (0021)` | **L vs S: `+1` · L vs P: `+4` migrations**  |
| **Aim 1 / Aim 2 Record Rows**        | **11,894** (11,876 joined obs) | **11,929** (`Δ -35` vs Local)                                  | **11,929** (`Δ -35` vs Local)                          | Live analytical record counts               |
| **Resources / Field / Prep Samples** | `127 / 147 / 384`              | `127 / 172 / 402`                                              | `127 / 172 / 402`                                      | **`-18` Prepared Samples in Local vs Prod** |
| **Public Tables / Columns**          | `115 tables / 1345 cols`       | `114 tables / 1318 cols`                                       | `114 tables / 1318 cols`                               | Public schema introspection                 |
| **Pairwise Sync Score**              | **Local vs Staging: `78.4%`**  | **Staging vs Prod: `62.4%`**                                   | **Local vs Prod: `54.1%`**                             | Composite 4-layer parity index              |

---

## 2. Key Environment Findings & Remediation

1. **Alembic Migration Revision Parity (`0025` Local vs `0024` Staging vs `0021`
   Production)**:
   - **Finding**: Local vs Staging migration delta is `+1`; Local vs Production
     migration delta is `+4`.
   - **Remediation**: Promote pending Alembic migrations via `pixi run migrate`
     and refresh materialized views via `pixi run refresh-views`.
2. **View Schema Guard (`19/19` Views Verified Across Local vs Production)**:
   - **Finding**: Checked `251` view columns across `ca_biositing` (8 views) and
     `data_portal` (11 views) with `0` column/type mismatches.
3. **Aim 1 / Aim 2 Analytical Record Delta (`Local - Staging = -35` ·
   `Local - Prod = -35`)**:
   - **Finding**: Local holds `11,894` analytical records (`62,686`
     observations), Staging holds `11,929` records (`65,137` observations), and
     Production holds `11,929` records (`19,348` observations).
4. **Parameter Mean Shift Audit (`>5%` Threshold)**:
   - **Finding**: `8` parameter slices exceed 5% mean shift between Local and
     Staging; `8` parameter slices exceed 5% mean shift between Local and
     Production.

---

## 3. Layer 2: Core Table & Materialized View Row-Count Waterfall

### 3.1 Core Public Schema Tables (21 Tables)

| Table Name                          | Category         | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) | Δ (Local - Staging) | Δ (Local - Prod) | Status (Local vs Prod) |
| :---------------------------------- | :--------------- | --------------: | ----------------: | -------------------: | ------------------: | ---------------: | :--------------------- |
| `public.resource`                   | Entity & Lineage |             127 |               127 |                  127 |                  +0 |               +0 | **SYNCED**             |
| `public.primary_ag_product`         | Entity & Lineage |              84 |                84 |                   84 |                  +0 |               +0 | **SYNCED**             |
| `public.provider`                   | Entity & Lineage |              51 |                51 |                   51 |                  +0 |               +0 | **SYNCED**             |
| `public.field_sample`               | Entity & Lineage |             147 |               172 |                  172 |                 -25 |              -25 | **PRODUCTION AHEAD**   |
| `public.prepared_sample`            | Entity & Lineage |             384 |               402 |                  402 |                 -18 |              -18 | **PRODUCTION AHEAD**   |
| `public.experiment`                 | Entity & Lineage |             109 |               115 |                   84 |                  -6 |              +25 | **LOCAL AHEAD**        |
| `public.observation`                | Entity & Lineage |          62,686 |            65,137 |               19,348 |              -2,451 |          +43,338 | **LOCAL AHEAD**        |
| `public.compositional_record`       | Aim 1 Analytical |           1,043 |             1,043 |                1,043 |                  +0 |               +0 | **SYNCED**             |
| `public.proximate_record`           | Aim 1 Analytical |           1,348 |             1,348 |                1,348 |                  +0 |               +0 | **SYNCED**             |
| `public.ultimate_record`            | Aim 1 Analytical |              84 |                84 |                   84 |                  +0 |               +0 | **SYNCED**             |
| `public.xrf_record`                 | Aim 1 Analytical |           2,777 |             2,777 |                2,777 |                  +0 |               +0 | **SYNCED**             |
| `public.icp_record`                 | Aim 1 Analytical |             826 |               826 |                  826 |                  +0 |               +0 | **SYNCED**             |
| `public.calorimetry_record`         | Aim 1 Analytical |              60 |                95 |                   95 |                 -35 |              -35 | **PRODUCTION AHEAD**   |
| `public.xrd_record`                 | Aim 1 Analytical |              28 |                28 |                   28 |                  +0 |               +0 | **SYNCED**             |
| `public.ftnir_record`               | Aim 1 Analytical |               0 |                 0 |                    0 |                  +0 |               +0 | **SYNCED**             |
| `public.fermentation_record`        | Aim 2 Conversion |           4,021 |             4,021 |                4,021 |                  +0 |               +0 | **SYNCED**             |
| `public.gasification_record`        | Aim 2 Conversion |             801 |               801 |                  801 |                  +0 |               +0 | **SYNCED**             |
| `public.pretreatment_record`        | Aim 2 Conversion |             906 |               906 |                  906 |                  +0 |               +0 | **SYNCED**             |
| `public.usda_market_record`         | USDA & Market    |               0 |                 0 |                    0 |                  +0 |               +0 | **SYNCED**             |
| `public.usda_census_record`         | USDA & Market    |           6,299 |             6,299 |                  330 |                  +0 |           +5,969 | **LOCAL AHEAD**        |
| `public.resource_production_record` | USDA & Market    |              73 |                73 |                   73 |                  +0 |               +0 | **SYNCED**             |

### 3.2 `ca_biositing` & `data_portal` Materialized Views (19 Views)

| Materialized View                           | Cols (`Guard`) | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) | Δ (Local - Staging) | Δ (Local - Prod) | Status (Local vs Prod) |
| :------------------------------------------ | :------------: | --------------: | ----------------: | -------------------: | ------------------: | ---------------: | :--------------------- |
| `ca_biositing.analysis_average_view`        | `7` (✅ PASS)  |           1,207 |             1,229 |                1,232 |                 -22 |              -25 | **PRODUCTION AHEAD**   |
| `ca_biositing.analysis_data_view`           | `12` (✅ PASS) |           7,481 |             7,643 |                8,329 |                -162 |             -848 | **PRODUCTION AHEAD**   |
| `ca_biositing.billion_ton_tileset_view`     | `7` (✅ PASS)  |               0 |                 0 |                    0 |                  +0 |               +0 | **SYNCED**             |
| `ca_biositing.landiq_record_view`           | `8` (✅ PASS)  |               0 |                 0 |                    0 |                  +0 |               +0 | **SYNCED**             |
| `ca_biositing.landiq_tileset_view`          | `7` (✅ PASS)  |               0 |                 0 |                    0 |                  +0 |               +0 | **SYNCED**             |
| `ca_biositing.usda_census_view`             | `12` (✅ PASS) |          19,893 |            19,893 |                1,419 |                  +0 |          +18,474 | **PRODUCTION BEHIND**  |
| `ca_biositing.usda_resource_commodity_view` | `2` (✅ PASS)  |              84 |                84 |                   82 |                  +0 |               +2 | **PRODUCTION BEHIND**  |
| `ca_biositing.usda_survey_view`             | `16` (✅ PASS) |          30,375 |            30,375 |                3,545 |                  +0 |          +26,830 | **PRODUCTION BEHIND**  |
| `data_portal.mv_biomass_availability`       | `7` (✅ PASS)  |              90 |                90 |                   90 |                  +0 |               +0 | **SYNCED**             |
| `data_portal.mv_biomass_composition`        | `13` (✅ PASS) |           1,127 |             1,127 |                1,127 |                  +0 |               +0 | **DEF DRIFT**          |
| `data_portal.mv_biomass_county_production`  | `16` (✅ PASS) |               0 |                 0 |                    0 |                  +0 |               +0 | **SYNCED**             |
| `data_portal.mv_biomass_end_uses`           | `11` (✅ PASS) |              34 |                40 |                   40 |                  -6 |               -6 | **PRODUCTION AHEAD**   |
| `data_portal.mv_biomass_fermentation`       | `17` (✅ PASS) |             408 |               441 |                  443 |                 -33 |              -35 | **PRODUCTION AHEAD**   |
| `data_portal.mv_biomass_gasification`       | `12` (✅ PASS) |             269 |               269 |                  269 |                  +0 |               +0 | **DEF DRIFT**          |
| `data_portal.mv_biomass_pricing`            | `15` (✅ PASS) |              73 |                73 |                   73 |                  +0 |               +0 | **SYNCED**             |
| `data_portal.mv_biomass_sample_stats`       | `6` (✅ PASS)  |             121 |               121 |                  121 |                  +0 |               +0 | **DEF DRIFT**          |
| `data_portal.mv_biomass_search`             | `50` (✅ PASS) |             121 |               121 |                  121 |                  +0 |               +0 | **DEF DRIFT**          |
| `data_portal.mv_biomass_volume_estimate`    | `19` (✅ PASS) |             150 |               150 |                  156 |                  +0 |               -6 | **PRODUCTION AHEAD**   |
| `data_portal.mv_usda_county_production`     | `14` (✅ PASS) |           6,941 |             6,941 |                  481 |                  +0 |           +6,460 | **PRODUCTION BEHIND**  |

### 3.3 View Schema Guard (`ca_biositing` & `data_portal` Column & Data-Type Parity)

- **Guard Summary:** `19/19` views verified (`8` in `ca_biositing`, `11` in
  `data_portal`) · `251/251` column definitions & data types match across
  environments.

| Schema · View Name                          | Cols |   Column Schema Hash (`L / S / P`)   | Sample Verified Columns (`name: type`)                                                                                                     |       Guard Status       |
| :------------------------------------------ | ---: | :----------------------------------: | :----------------------------------------------------------------------------------------------------------------------------------------- | :----------------------: |
| `ca_biositing.analysis_average_view`        |    7 | `93c5bf12` / `93c5bf12` / `93c5bf12` | `resource: text`, `geoid: character varying`, `parameter: text`, `average_value: numeric`, … (+3 more)                                     | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.analysis_data_view`           |   12 | `dcb8e27f` / `dcb8e27f` / `dcb8e27f` | `id: integer`, `record_id: character varying`, `record_type: character varying`, `resource_id: integer`, … (+8 more)                       | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.billion_ton_tileset_view`     |    7 | `2dab8beb` / `2dab8beb` / `2dab8beb` | `id: integer`, `resource: character varying`, `county: text`, `parameter: text`, … (+3 more)                                               | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.landiq_record_view`           |    8 | `300347df` / `300347df` / `300347df` | `record_id: character varying`, `geom: geometry`, `geoid: character varying`, `crop_name: character varying`, … (+4 more)                  | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.landiq_tileset_view`          |    7 | `ec5bfd5a` / `ec5bfd5a` / `ec5bfd5a` | `id: integer`, `geom: geometry`, `main_crop: character varying`, `acres: double precision`, … (+3 more)                                    | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.usda_census_view`             |   12 | `6747286f` / `6747286f` / `6747286f` | `id: integer`, `usda_crop: text`, `geoid: character varying`, `parameter: text`, … (+8 more)                                               | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.usda_resource_commodity_view` |    2 | `adc86678` / `adc86678` / `adc86678` | `resource: character varying`, `commodity_id: integer`                                                                                     | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.usda_survey_view`             |   16 | `804d6b55` / `804d6b55` / `804d6b55` | `id: integer`, `usda_crop: text`, `geoid: character varying`, `parameter: text`, … (+12 more)                                              | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_availability`       |    7 | `314849c2` / `314849c2` / `314849c2` | `resource_id: integer`, `resource_name: character varying`, `from_month: integer`, `to_month: integer`, … (+3 more)                        | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_composition`        |   13 | `c7da0404` / `c7da0404` / `c7da0404` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `analysis_type: text`, … (+9 more)                               | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_county_production`  |   16 | `d51d57f4` / `d51d57f4` / `d51d57f4` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `resource_class: character varying`, … (+12 more)                | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_end_uses`           |   11 | `367029bf` / `367029bf` / `367029bf` | `resource_id: integer`, `resource_name: character varying`, `use_case: character varying`, `percentage_low: double precision`, … (+7 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_fermentation`       |   17 | `687b2e49` / `687b2e49` / `687b2e49` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `geoid: character varying`, … (+13 more)                         | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_gasification`       |   12 | `5ede8f73` / `5ede8f73` / `5ede8f73` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `reactor_type: character varying`, … (+8 more)                   | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_pricing`            |   15 | `9d3b8d95` / `9d3b8d95` / `9d3b8d95` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `geoid: character varying`, … (+11 more)                         | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_sample_stats`       |    6 | `ccf5aae0` / `ccf5aae0` / `ccf5aae0` | `resource_id: integer`, `resource_name: character varying`, `sample_count: bigint`, `supplier_count: bigint`, … (+2 more)                  | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_search`             |   50 | `57c8c146` / `57c8c146` / `57c8c146` | `id: integer`, `name: character varying`, `resource_code: character varying`, `description: character varying`, … (+46 more)               | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_volume_estimate`    |   19 | `caec992e` / `caec992e` / `caec992e` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `geoid: character varying`, … (+15 more)                         | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_usda_county_production`     |   14 | `6cc33d4a` / `6cc33d4a` / `6cc33d4a` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `primary_ag_product: character varying`, … (+10 more)            | ✅ **SCHEMA GUARD PASS** |

---

## 4. Layer 3: Lineage Set-Differences (`Local` vs `Staging` vs `Production`)

- **Resources in Local Only vs Production (0):** None
- **Field Samples in Local Only vs Staging (0):** None
- **Prepared Samples in Local Only vs Staging (0):** None
- **Prepared Samples in Local Only vs Production (0):** None

---

## 5. Layer 4: Filter Funnel Attrition & Parameter Value Shifts (`>5%`)

### 5.1 `ca_biositing.analysis_data_view` Filter Funnel Comparison

| Funnel Stage                                     | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) |
| :----------------------------------------------- | --------------: | ----------------: | -------------------: |
| **1. Raw Candidate Pool**                        |          11,876 |            13,942 |               13,495 |
| **2. Removed by `qc_pass = 'fail'`**             |          -1,914 |            -3,070 |               -2,792 |
| **3. Removed by `EXCLUDED_RESOURCES`**           |            -793 |              -869 |                 -858 |
| **4. Removed by `EXCLUDED_PROVIDERS`**           |            -722 |              -977 |                 -920 |
| **5. Removed by `ULTIMATE_PARAMETERS`**          |             -45 |               -45 |                  -45 |
| **6. Unmapped Resource (`resource_id IS NULL`)** |              -0 |                -0 |                   -0 |
| **7. Final Materialized View Rows**              |       **7,481** |         **7,643** |            **8,329** |
| **Retention Ratio**                              |      **62.99%** |        **54.82%** |           **61.72%** |

### 5.2 Flagged Parameter Mean Shifts (`>5%` Local vs Production — 8 Flagged Slices)

| Analysis Type          | Parameter (Unit) |   Local Mean (`n`) | Staging Mean (`n`) |    Prod Mean (`n`) | Mean % Shift (L vs P) | Flag           |
| :--------------------- | :--------------- | -----------------: | -----------------: | -----------------: | --------------------: | :------------- |
| ICP Elemental Analysis | `ca` (ppm)       |  5,508.20 (`n=64`) |  4,406.65 (`n=80`) |  4,406.65 (`n=80`) |           **+25.00%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `k` (ppm)        | 17,458.13 (`n=61`) | 13,830.83 (`n=77`) | 13,830.83 (`n=77`) |           **+26.23%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `mg` (ppm)       |  1,378.07 (`n=63`) |  1,113.08 (`n=78`) |  1,113.08 (`n=78`) |           **+23.81%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `p` (ppm)        |  1,513.08 (`n=64`) |  1,210.50 (`n=80`) |  1,210.50 (`n=80`) |           **+25.00%** | ⚠️ `>5% SHIFT` |
| Ultimate Analysis      | `carbon`         |      25.00 (`n=2`) |       0.00 (`n=0`) |       0.00 (`n=0`) |          **+100.00%** | ⚠️ `>5% SHIFT` |
| Ultimate Analysis      | `nitrogen` (pc)  |      4.03 (`n=19`) |     10.25 (`n=27`) |      9.06 (`n=25`) |           **-55.51%** | ⚠️ `>5% SHIFT` |
| Ultimate Analysis      | `oxygen`         |      25.00 (`n=1`) |       0.00 (`n=0`) |       0.00 (`n=0`) |          **+100.00%** | ⚠️ `>5% SHIFT` |
| Ultimate Analysis      | `sulfur`         |      25.00 (`n=1`) |       0.00 (`n=0`) |       0.00 (`n=0`) |          **+100.00%** | ⚠️ `>5% SHIFT` |
