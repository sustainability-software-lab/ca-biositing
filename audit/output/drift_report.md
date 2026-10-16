# BioCirV — Multi-Environment Database Drift Assessment Report (`local` · `staging` · `production`)

**Generated UTC:** `2026-10-16 17:58:22 UTC`  
**Interactive Dashboard:** `exports/plots/audit/db_environment_drift_dashboard.html`  
**Generator CLI:** `python3 analysis/audit/db_environment_drift.py --compare`

---

## 1. Executive Environment Summary & Sync Scorecard

| Dimension | Local Dev (`:5432`) | Staging (`:5434` Proxy) | Production (`:5435` Proxy) | Drift Status |
| :--- | :--- | :--- | :--- | :--- |
| **Database Name** | `biocirv_db` | `biocirv-staging` | `biocirv-production` | Canonical 3-tier topology |
| **Capture Mode** | `baseline_snapshot` | `simulated_staging_lag` | `simulated_prod_release` | Supports `--extract-env` & UI upload |
| **Alembic Revision Head** | `8f4b2c19a03d (head)` | `7c91e04b211a (0023_centralize_qc_analysis_data_view)` | `4a18d93f05c2 (0021_remove_almond_meats_from_volume_estimate)` | **Staging -1 rev · Prod -3 revs** |
| **Aim 1 / Aim 2 Record Rows** | **11,894** (11,974 joined obs) | **11,755** (`Δ -101` vs Local) | **9,500** (`Δ -2,414` vs Local) | **Staging lag & Prod prior release** |
| **Resources / Field / Prep Samples** | `127 / 147 / 384` | `127 / 144 / 376` | `121 / 118 / 296` | **+88 Prepared Samples in Local vs Prod** |
| **Materialized View Health** | `19/19 Fresh (0 Stale)` | **`5/19 Stale (74.5h lag)`** | `8/19 Definition Drift (Rev 0021)` | **`pixi run refresh-views` needed in Staging** |
| **Pairwise Sync Score** | **Local vs Staging: `57.9%`** | **Staging vs Prod: `41.8%`** | **Local vs Prod: `35.3%`** | Action required before Prod promotion |

---

## 2. Critical Drift Findings & Remediation Checklist

1. **Staging Materialized Views Stale (`MV STALE` Alert)**:
   - **Finding**: Base tables in `staging` (`compositional_record`, `xrf_record`, `proximate_record`) were updated by ETL runs, but `REFRESH MATERIALIZED VIEW` was not executed (`74.5 hours` lag). `data_portal.mv_biomass_composition` serves `1,064` rows instead of `1,109`, and `ca_biositing.analysis_data_view` serves `7,312` instead of `7,461`.
   - **Remediation**: Run `POSTGRES_HOST=localhost POSTGRES_PORT=5434 POSTGRES_DB=biocirv-staging pixi run refresh-views`.
2. **Alembic Migration Revision Drift (`0024` Local vs `0023` Staging vs `0021` Production)**:
   - **Finding**: `staging` is missing `0024_centralize_qc_constants_across_data_portal_views`. `production` is on `0021_remove_almond_meats_from_volume_estimate` and is missing `0022_exclude_jaguar_provider`, `0023`, and `0024`.
   - **Impact**: Production `ca_biositing.analysis_data_view` still includes `665` rows from excluded provider `jaguar` (`removed_by_provider_blacklist = 0` in Prod vs `665` in Local).
   - **Remediation**: Promote Alembic migrations `0022 -> 0024` via `pixi run migrate` against Staging and Production.
3. **Unpromoted Aim 1 / Aim 2 Analytical Batches (`Calorimetry`, `XRD`, `XRF`, `Gasification`)**:
   - **Finding**: `local` contains `60` `calorimetry_record` rows (`38` in Staging, `0` in Production), `28` `xrd_record` rows (`19` in Staging, `28` un-flagged in Production), `2,777` `xrf_record` rows (`390` in Production), and `801` `gasification_record` rows (`756` in Staging, `611` in Production).
4. **Legacy Un-Deduplicated ICP Records in Production (`1,153` Prod vs `826` Local)**:
   - **Finding**: Production `icp_record` contains `1,153` rows (`+327` more than Local's `826` rows) due to duplicate runs and weight-percent (`pc`) entries that were cleaned and standardized to `ppm` (`×10⁴`) in Local.
5. **QC Pass/Fail Normalization & Parameter Mean Shifts (`>5%`)**:
   - **Finding**: In Local & Staging, rigorous QC screening flipped `875` high-variability `fermentation_record` rows (`1,160 fail` vs `285 fail` in Prod), `98` oven-dried `proximate_record` rows (`209 fail` vs `111 fail` in Prod), `27` `xrd_record` rows, and `1` `ultimate_record` sulfur outlier (`270%` sulfur in `almond shells`, record `)udff5df`).

---

## 3. Layer 2: Core Table & Materialized View Row-Count Waterfall

### 3.1 Core Public Schema Tables (21 Tables)

| Table Name | Category | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) | Δ (Local - Staging) | Δ (Local - Prod) | Status (Local vs Prod) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `public.resource` | Entity & Lineage | 127 | 127 | 121 | +0 | +6 | **LOCAL AHEAD** |
| `public.primary_ag_product` | Entity & Lineage | 29 | 29 | 27 | +0 | +2 | **LOCAL AHEAD** |
| `public.provider` | Entity & Lineage | 51 | 51 | 50 | +0 | +1 | **LOCAL AHEAD** |
| `public.field_sample` | Entity & Lineage | 147 | 144 | 118 | +3 | +29 | **LOCAL AHEAD** |
| `public.prepared_sample` | Entity & Lineage | 384 | 376 | 296 | +8 | +88 | **LOCAL AHEAD** |
| `public.experiment` | Entity & Lineage | 109 | 106 | 94 | +3 | +15 | **LOCAL AHEAD** |
| `public.observation` | Entity & Lineage | 62,600 | 62,285 | 58,420 | +315 | +4,180 | **LOCAL AHEAD** |
| `public.compositional_record` | Aim 1 Analytical | 1,043 | 1,018 | 968 | +25 | +75 | **LOCAL AHEAD** |
| `public.proximate_record` | Aim 1 Analytical | 1,348 | 1,342 | 1,339 | +6 | +9 | **LOCAL AHEAD** |
| `public.ultimate_record` | Aim 1 Analytical | 84 | 84 | 84 | +0 | +0 | **SYNCED** |
| `public.xrf_record` | Aim 1 Analytical | 2,777 | 2,745 | 390 | +32 | +2,387 | **LOCAL AHEAD** |
| `public.icp_record` | Aim 1 Analytical | 826 | 826 | 1,153 | +0 | -327 | **PRODUCTION AHEAD** |
| `public.calorimetry_record` | Aim 1 Analytical | 60 | 38 | 0 | +22 | +60 | **LOCAL AHEAD** |
| `public.xrd_record` | Aim 1 Analytical | 28 | 19 | 28 | +9 | +0 | **SYNCED** |
| `public.ftnir_record` | Aim 1 Analytical | 0 | 0 | 0 | +0 | +0 | **SYNCED** |
| `public.fermentation_record` | Aim 2 Conversion | 4,021 | 4,021 | 4,021 | +0 | +0 | **SCHEMA DRIFT** |
| `public.gasification_record` | Aim 2 Conversion | 801 | 756 | 611 | +45 | +190 | **LOCAL AHEAD** |
| `public.pretreatment_record` | Aim 2 Conversion | 906 | 906 | 906 | +0 | +0 | **SYNCED** |
| `public.usda_market_record` | USDA & Market | 73 | 73 | 61 | +0 | +12 | **LOCAL AHEAD** |
| `public.usda_census_record` | USDA & Market | 3,386 | 3,386 | 3,386 | +0 | +0 | **SYNCED** |
| `public.resource_production_record` | USDA & Market | 73 | 73 | 61 | +0 | +12 | **LOCAL AHEAD** |

### 3.2 `ca_biositing` & `data_portal` Materialized Views (19 Views)

| Materialized View | Cols (`Guard`) | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) | Δ (Local - Staging) | Δ (Local - Prod) | Staging Freshness |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `ca_biositing.analysis_average_view` | `7` (✅ PASS) | 1,207 | 1,168 | 1,094 | +39 | +113 | ⚠️ **MV STALE** |
| `ca_biositing.analysis_data_view` | `12` (✅ PASS) | 7,481 | 7,312 | 6,485 | +169 | +996 | ⚠️ **MV STALE** |
| `ca_biositing.billion_ton_tileset_view` | `7` (✅ PASS) | 0 | 0 | 0 | +0 | +0 | ✅ Fresh |
| `ca_biositing.landiq_record_view` | `8` (✅ PASS) | 0 | 0 | 0 | +0 | +0 | ✅ Fresh |
| `ca_biositing.landiq_tileset_view` | `7` (✅ PASS) | 0 | 0 | 0 | +0 | +0 | ✅ Fresh |
| `ca_biositing.usda_census_view` | `12` (✅ PASS) | 19,893 | 19,893 | 19,893 | +0 | +0 | ✅ Fresh |
| `ca_biositing.usda_resource_commodity_view` | `2` (✅ PASS) | 84 | 84 | 82 | +0 | +2 | ✅ Fresh |
| `ca_biositing.usda_survey_view` | `16` (✅ PASS) | 30,375 | 30,375 | 30,375 | +0 | +0 | ✅ Fresh |
| `data_portal.mv_biomass_availability` | `7` (✅ PASS) | 90 | 90 | 86 | +0 | +4 | ✅ Fresh |
| `data_portal.mv_biomass_composition` | `13` (✅ PASS) | 1,127 | 1,064 | 982 | +63 | +145 | ⚠️ **MV STALE** |
| `data_portal.mv_biomass_county_production` | `16` (✅ PASS) | 0 | 0 | 0 | +0 | +0 | ✅ Fresh |
| `data_portal.mv_biomass_end_uses` | `11` (✅ PASS) | 34 | 34 | 34 | +0 | +0 | ✅ Fresh |
| `data_portal.mv_biomass_fermentation` | `17` (✅ PASS) | 408 | 408 | 442 | +0 | -34 | ✅ Fresh |
| `data_portal.mv_biomass_gasification` | `12` (✅ PASS) | 269 | 241 | 198 | +28 | +71 | ⚠️ **MV STALE** |
| `data_portal.mv_biomass_pricing` | `15` (✅ PASS) | 73 | 73 | 61 | +0 | +12 | ✅ Fresh |
| `data_portal.mv_biomass_sample_stats` | `6` (✅ PASS) | 121 | 115 | 108 | +6 | +13 | ⚠️ **MV STALE** |
| `data_portal.mv_biomass_search` | `50` (✅ PASS) | 121 | 121 | 115 | +0 | +6 | ✅ Fresh |
| `data_portal.mv_biomass_volume_estimate` | `19` (✅ PASS) | 150 | 150 | 168 | +0 | -18 | ✅ Fresh |
| `data_portal.mv_usda_county_production` | `14` (✅ PASS) | 6,941 | 6,941 | 6,941 | +0 | +0 | ✅ Fresh |

### 3.3 View Schema Guard (`ca_biositing` & `data_portal` Column & Data-Type Parity)

- **Guard Summary:** `19/19` views verified (`8` in `ca_biositing`, `11` in `data_portal`) · `251/251` column definitions & data types match across environments.

| Schema · View Name | Cols | Column Schema Hash (`L / S / P`) | Sample Verified Columns (`name: type`) | Guard Status |
| :--- | ---: | :---: | :--- | :---: |
| `ca_biositing.analysis_average_view` | 7 | `—` / `—` / `—` | `resource: text`, `geoid: character varying`, `parameter: text`, `average_value: numeric`, … (+3 more) | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.analysis_data_view` | 12 | `—` / `—` / `—` | `id: integer`, `record_id: character varying`, `record_type: character varying`, `resource_id: integer`, … (+8 more) | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.billion_ton_tileset_view` | 7 | `—` / `—` / `—` | `id: integer`, `resource: character varying`, `county: text`, `parameter: text`, … (+3 more) | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.landiq_record_view` | 8 | `—` / `—` / `—` | `record_id: character varying`, `geom: geometry(Geometry,4326)`, `geoid: character varying`, `crop_name: character varying`, … (+4 more) | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.landiq_tileset_view` | 7 | `—` / `—` / `—` | `id: integer`, `geom: geometry(Geometry,4326)`, `main_crop: character varying`, `acres: double precision`, … (+3 more) | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.usda_census_view` | 12 | `—` / `—` / `—` | `id: integer`, `usda_crop: text`, `geoid: character varying`, `parameter: text`, … (+8 more) | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.usda_resource_commodity_view` | 2 | `—` / `—` / `—` | `resource: character varying`, `commodity_id: integer` | ✅ **SCHEMA GUARD PASS** |
| `ca_biositing.usda_survey_view` | 16 | `—` / `—` / `—` | `id: integer`, `usda_crop: text`, `geoid: character varying`, `parameter: text`, … (+12 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_availability` | 7 | `—` / `—` / `—` | `resource_id: integer`, `resource_name: character varying`, `from_month: integer`, `to_month: integer`, … (+3 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_composition` | 13 | `—` / `—` / `—` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `analysis_type: character varying`, … (+9 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_county_production` | 16 | `—` / `—` / `—` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `resource_class: character varying`, … (+12 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_end_uses` | 11 | `—` / `—` / `—` | `resource_id: integer`, `resource_name: character varying`, `use_case: character varying`, `percentage_low: double precision`, … (+7 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_fermentation` | 17 | `—` / `—` / `—` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `geoid: character varying`, … (+13 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_gasification` | 12 | `—` / `—` / `—` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `reactor_type: character varying`, … (+8 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_pricing` | 15 | `—` / `—` / `—` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `geoid: character varying`, … (+11 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_sample_stats` | 6 | `—` / `—` / `—` | `resource_id: integer`, `resource_name: character varying`, `sample_count: integer`, `supplier_count: integer`, … (+2 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_search` | 50 | `—` / `—` / `—` | `id: integer`, `name: character varying`, `resource_code: character varying`, `description: character varying`, … (+46 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_biomass_volume_estimate` | 19 | `—` / `—` / `—` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `geoid: character varying`, … (+15 more) | ✅ **SCHEMA GUARD PASS** |
| `data_portal.mv_usda_county_production` | 14 | `—` / `—` / `—` | `id: bigint`, `resource_id: integer`, `resource_name: character varying`, `primary_ag_product: character varying`, … (+10 more) | ✅ **SCHEMA GUARD PASS** |

---

## 4. Layer 3: Lineage Set-Differences (`Local` vs `Staging` vs `Production`)

- **Resources in Local/Staging Only (Missing in Prod — 6):** `blend`, `grape vine prunings`, `olive prunings`, `peach screening waste`, `sweet potato culls`, `walnut shelling fines`
- **Field Samples in Local Only (Missing in Staging — 3):** `dod-spcul127` (sweet potato culls), `dod-spcul128` (sweet potato culls), `was-pihu137` (pistachio hulls)
- **Prepared Samples in Local Only (Missing in Staging — 8):** `boa-gpvn103chkm2(eb)`, `boa-gpvpr102chkm2(35)`, `dod-spcul127chop(98)`, `dod-spcul128chop(96)`, `exc-olpr106chf(ab)`, `exc-olpr107chf(85)`, `thy-pchpr104chf(b3)`, `was-pihu137a(9e)`
- **Prepared Samples in Local Only vs Production (88 unpromoted samples):** `boa-gpvn103chkm2(eb)`, `boa-gpvpr102c1i(97)`, `boa-gpvpr102c1i(da)`, `boa-gpvpr102chkm2(35)`, `boa-gpvpr102chokm2(9b)`, `cut-washf089a(4f)`, `cut-washf089a(b5)`, `dod-spcul127chop(98)`, `dod-spcul127chopf(9c)`, `dod-spcul127chopo(27)`, `dod-spcul128chop(96)`, `dod-spcul128chopf(50)`, `dod-spcul128chopo(78)`, `exc-olpr106c1i(eb)`, `exc-olpr106chf(ab)` *(see Tab 3 in dashboard for full searchable list)*

---

## 5. Layer 4: Filter Funnel Attrition & Parameter Value Shifts (`>5%`)

### 5.1 `ca_biositing.analysis_data_view` Filter Funnel Comparison

| Funnel Stage | Local (`:5432`) | Staging (`:5434`) | Production (`:5435`) | Notes |
| :--- | ---: | ---: | ---: | :--- |
| **1. Raw Candidate Pool** | 11,847 | 11,682 | 9,480 | All Aim1/Aim2 observations excluding USDA |
| **2. Removed by `qc_pass = 'fail'`** | -1,361 | -1,344 | -698 | Local/Staging reflect stricter QC pass/fail curation |
| **3. Removed by `EXCLUDED_RESOURCES`** | -969 | -958 | -712 | `#n/a`, `alfalfa`, `sargassum`, `lab media`, mixes |
| **4. Removed by `EXCLUDED_PROVIDERS`** | -665 | -665 | -0 | Prod rev `0021` lacks `0022_exclude_jaguar_provider` (`665` rows) |
| **5. Removed by `ULTIMATE_PARAMETERS`** | -42 | -42 | -42 | Filters non-CHONS parameters (`cf`, `dm`, `adf-r`) |
| **6. Unmapped Resource (`resource_id IS NULL`)** | -1,218 | -1,212 | -1,395 | Control/blank wells without feedstock mapping |
| **7. Final Materialized View Rows** | **7,481** | **7,312** | **6,485** | Staging MV stale (`7,312` cached vs `7,461` live) |
| **Retention Ratio** | **63.15%** | **62.59%** | **68.41%** | Portal retention guard |

### 5.2 Flagged Parameter Mean Shifts (`>5%` Local vs Production — 62 Flagged Slices)

| Analysis Type | Parameter (Unit) | Local Mean (`n`) | Staging Mean (`n`) | Prod Mean (`n`) | Mean % Shift (L vs P) | Flag |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| Calorimetry | `hhv_dry` (mj/kg) | 18.42 (`n=53`) | 19.78 (`n=33`) | 0.00 (`n=0`) | **+100.00%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `3hptiter` (g_l) | 4.21 (`n=219`) | 4.21 (`n=219`) | 3.60 (`n=291`) | **+16.91%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `3hpyield` (pc_g_g) | 13.39 (`n=219`) | 13.39 (`n=219`) | 15.84 (`n=288`) | **-15.49%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `gluconct0` (g_l) | 26.71 (`n=291`) | 26.71 (`n=291`) | 25.32 (`n=363`) | **+5.50%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `gluconcteof` (g_l) | 5.93 (`n=291`) | 5.93 (`n=291`) | 6.63 (`n=363`) | **-10.67%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `od600teof` () | 1.50 (`n=123`) | 1.50 (`n=123`) | 3.63 (`n=363`) | **-58.75%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `rel_growth` (pc) | 31.76 (`n=123`) | 31.76 (`n=123`) | 85.80 (`n=363`) | **-62.98%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `sugar_cons` (pc) | 46.76 (`n=291`) | 46.76 (`n=291`) | 40.54 (`n=363`) | **+15.35%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `sugarteof` (g_l) | 10.24 (`n=291`) | 10.24 (`n=291`) | 11.35 (`n=363`) | **-9.78%** | ⚠️ `>5% SHIFT` |
| Fermentation (Bioconversion) | `xylconcteof` (g_l) | 4.31 (`n=291`) | 4.31 (`n=291`) | 4.71 (`n=363`) | **-8.44%** | ⚠️ `>5% SHIFT` |
| Gasification | `c2h6` (ppm) | 10,997.01 (`n=25`) | 8,198.16 (`n=19`) | 7,937.70 (`n=17`) | **+38.54%** | ⚠️ `>5% SHIFT` |
| Gasification | `c3h8` (ppm) | 4,124.20 (`n=25`) | 2,015.69 (`n=19`) | 1,937.74 (`n=17`) | **+112.84%** | ⚠️ `>5% SHIFT` |
| Gasification | `c4h10(b)` (ppm) | 1,276.83 (`n=25`) | 367.00 (`n=19`) | 391.17 (`n=17`) | **+226.41%** | ⚠️ `>5% SHIFT` |
| Gasification | `c4h10(i)` (ppm) | 1,518.25 (`n=25`) | 1,393.60 (`n=19`) | 1,159.12 (`n=17`) | **+30.98%** | ⚠️ `>5% SHIFT` |
| Gasification | `c5h12` (ppm) | 0.41 (`n=25`) | 0.16 (`n=19`) | 0.16 (`n=17`) | **+156.13%** | ⚠️ `>5% SHIFT` |
| Gasification | `c6h14` (ppm) | 0.04 (`n=25`) | 0.03 (`n=19`) | 0.03 (`n=17`) | **+5.07%** | ⚠️ `>5% SHIFT` |
| Gasification | `ch4` (ppm) | 16,688.09 (`n=25`) | 16,432.00 (`n=19`) | 14,774.33 (`n=17`) | **+12.95%** | ⚠️ `>5% SHIFT` |
| Gasification | `char` (g) | 79.24 (`n=14`) | 85.89 (`n=10`) | 84.15 (`n=9`) | **-5.83%** | ⚠️ `>5% SHIFT` |
| Gasification | `co2` (ppm) | 137,327.45 (`n=25`) | 130,911.01 (`n=19`) | 130,436.53 (`n=17`) | **+5.28%** | ⚠️ `>5% SHIFT` |
| Gasification | `comb` () | 18.68 (`n=42`) | 18.68 (`n=42`) | 17.14 (`n=32`) | **+9.01%** | ⚠️ `>5% SHIFT` |
| Gasification | `combfrac` (pc) | 22.55 (`n=2`) | 22.55 (`n=2`) | 2.76 (`n=2`) | **+717.21%** | ⚠️ `>5% SHIFT` |
| Gasification | `ta` (c) | 21.01 (`n=14`) | 22.53 (`n=10`) | 22.48 (`n=9`) | **-6.51%** | ⚠️ `>5% SHIFT` |
| Gasification | `tar` (g) | 6.34 (`n=14`) | 8.88 (`n=10`) | 9.86 (`n=9`) | **-35.71%** | ⚠️ `>5% SHIFT` |
| Gasification | `time` (min) | 31.59 (`n=14`) | 38.30 (`n=10`) | 37.12 (`n=9`) | **-14.90%** | ⚠️ `>5% SHIFT` |
| Gasification | `unc-bio` (g) | 45.30 (`n=14`) | 50.04 (`n=10`) | 55.60 (`n=9`) | **-18.52%** | ⚠️ `>5% SHIFT` |
| Gasification | `va` (mps) | 0.49 (`n=14`) | 0.67 (`n=10`) | 0.65 (`n=9`) | **-24.17%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `al` (ppm) | 50.44 (`n=48`) | 50.44 (`n=48`) | 40.64 (`n=51`) | **+24.11%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `b` (ppm) | 44.56 (`n=16`) | 44.56 (`n=16`) | 46.93 (`n=15`) | **-5.04%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `ca` (ppm) | 5,508.20 (`n=64`) | 5,508.20 (`n=64`) | 4,375.87 (`n=68`) | **+25.88%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `fe` (ppm) | 306.29 (`n=64`) | 306.29 (`n=64`) | 247.93 (`n=68`) | **+23.54%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `k` (ppm) | 17,458.13 (`n=61`) | 17,458.13 (`n=61`) | 13,505.43 (`n=65`) | **+29.27%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `mg` (ppm) | 1,378.07 (`n=63`) | 1,378.07 (`n=63`) | 1,072.46 (`n=67`) | **+28.50%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `na` (ppm) | 1,029.68 (`n=23`) | 1,029.68 (`n=23`) | 800.79 (`n=23`) | **+28.58%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `p` (ppm) | 1,513.08 (`n=64`) | 1,513.08 (`n=64`) | 1,124.34 (`n=68`) | **+34.57%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `s` (ppm) | 1,147.11 (`n=64`) | 1,147.11 (`n=64`) | 890.89 (`n=68`) | **+28.76%** | ⚠️ `>5% SHIFT` |
| ICP Elemental Analysis | `si` (ppm) | 18.40 (`n=48`) | 18.40 (`n=48`) | 14.13 (`n=51`) | **+30.20%** | ⚠️ `>5% SHIFT` |
| Proximate Analysis | `ash` (% total weight) | 6.38 (`n=288`) | 6.38 (`n=288`) | 6.85 (`n=324`) | **-6.83%** | ⚠️ `>5% SHIFT` |
| Proximate Analysis | `moisture` (% total weight) | 32.48 (`n=275`) | 32.48 (`n=275`) | 28.15 (`n=287`) | **+15.39%** | ⚠️ `>5% SHIFT` |
| Ultimate Analysis | `sulfur` (pc) | 25.00 (`n=1`) | 25.00 (`n=1`) | 147.50 (`n=2`) | **-83.05%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `al` (ppm) | 2,986.58 (`n=69`) | 2,987.48 (`n=66`) | 1,846.67 (`n=9`) | **+61.73%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `ba` (ppm) | 47.02 (`n=111`) | 47.02 (`n=111`) | 28.67 (`n=15`) | **+64.02%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `ca` (ppm) | 8,207.79 (`n=145`) | 8,207.79 (`n=145`) | 16,818.95 (`n=19`) | **-51.20%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `ce` (ppm) | 111.82 (`n=65`) | 115.97 (`n=61`) | 42.11 (`n=9`) | **+165.52%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `cu` (ppm) | 20.39 (`n=144`) | 20.39 (`n=144`) | 32.42 (`n=19`) | **-37.11%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `fe` (ppm) | 766.94 (`n=144`) | 766.94 (`n=144`) | 501.47 (`n=19`) | **+52.94%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `k` (ppm) | 24,740.40 (`n=145`) | 24,740.40 (`n=145`) | 13,896.84 (`n=19`) | **+78.03%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `la` (ppm) | 98.16 (`n=51`) | 100.69 (`n=49`) | 28.17 (`n=6`) | **+248.49%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `mg` (ppm) | 7,030.00 (`n=58`) | 6,596.60 (`n=47`) | 11,466.25 (`n=8`) | **-38.69%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `mn` (ppm) | 111.68 (`n=145`) | 111.68 (`n=145`) | 72.84 (`n=19`) | **+53.31%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `mo` (ppm) | 7.41 (`n=64`) | 7.44 (`n=62`) | 8.25 (`n=8`) | **-10.23%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `nd` (ppm) | 65.65 (`n=17`) | 65.65 (`n=17`) | 44.00 (`n=3`) | **+49.20%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `p` (ppm) | 1,721.38 (`n=145`) | 1,721.38 (`n=145`) | 2,047.74 (`n=19`) | **-15.94%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `pb` (ppm) | 4.27 (`n=52`) | 4.18 (`n=49`) | 5.00 (`n=6`) | **-14.62%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `pr` (ppm) | 73.98 (`n=50`) | 73.98 (`n=50`) | 65.00 (`n=7`) | **+13.82%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `rb` (ppm) | 24.10 (`n=136`) | 24.10 (`n=136`) | 32.17 (`n=18`) | **-25.09%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `s` (ppm) | 1,973.48 (`n=145`) | 1,973.48 (`n=145`) | 2,515.63 (`n=19`) | **-21.55%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `si` (ppm) | 14,475.51 (`n=145`) | 14,475.51 (`n=145`) | 5,392.11 (`n=19`) | **+168.46%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `sr` (ppm) | 44.10 (`n=139`) | 44.10 (`n=139`) | 93.42 (`n=19`) | **-52.79%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `th` (ppm) | 50.81 (`n=145`) | 50.81 (`n=145`) | 56.16 (`n=19`) | **-9.53%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `ti` (ppm) | 292.98 (`n=60`) | 295.00 (`n=58`) | 262.50 (`n=8`) | **+11.61%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `u` (ppm) | 16.22 (`n=144`) | 16.22 (`n=144`) | 19.89 (`n=19`) | **-18.46%** | ⚠️ `>5% SHIFT` |
| XRF Elemental Analysis | `zn` (ppm) | 51.11 (`n=145`) | 51.11 (`n=145`) | 211.32 (`n=19`) | **-75.81%** | ⚠️ `>5% SHIFT` |

