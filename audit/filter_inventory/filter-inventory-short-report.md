# BioCirv Filter Inventory — Phase 1 Report

**Scan date:** 2026-08-05
**Branch:** `filter-inventory`
**Question:** Where and why can data be removed from, excluded from, or hidden in BioCirv outputs?

**Scope scanned:** `src/`, `alembic/versions/`, `resources/sql/`
**Scope excluded by decision:** `frontend/` (git submodule, not checked out locally), `audit/`, `exports/`, `analysis/`, `scripts/`, `alembic/versions_old/`

This is a first-pass inventory. It records what the repository shows, not what the rules ought to be. Where the code does not state a rationale, the entry says `Unknown` rather than guessing.

---

## 1. Pipeline overview

Records pass through the stages below. Inclusion decisions are made at nearly every one of them — including the first, before any code runs.

Rule counts per stage are shown in brackets. This is the structure the Lucidchart diagram should mirror.

```
   ╔═ GOOGLE SHEETS ════════════╗  ┌─ USDA NASS API ─┐  ┌─ LandIQ / BillionTon ─┐
   ║  Analyst enters + QC-marks ║  │                 │  │                       │
   ║  records. qc_result=fail   ║  └────────┬────────┘  └───────────┬───────────┘
   ║  decided HERE.        [1]  ║           │                       │
   ╚═════════════╤══════════════╝           │                       │
                 │                          │                       │
        ╔════════▼══════════════════════════▼═══════════════════════▼═══════╗
        ║  EXTRACT SCRIPTS   pipeline/etl/extract/                    [2]   ║
        ║  Geographic + commodity scoping at the source                     ║
        ╚═══════════════════════════════╤═══════════════════════════════════╝
        ╔═══════════════════════════════▼═══════════════════════════════════╗
        ║  ORCHESTRATION (PREFECT)   pipeline/flows/                  [5]   ║
        ║  Swallowed extract errors + empty-frame guards drop WHOLE         ║
        ║  DATASETS while the flow still reports success                    ║
        ╚═══════════════════════════════╤═══════════════════════════════════╝
        ╔═══════════════════════════════▼═══════════════════════════════════╗
        ║  TRANSFORM SCRIPTS   pipeline/etl/transform/                [8]   ║
        ║  pandas row drops: null keys, placeholder tokens, dedup           ║
        ║  qc_result → qc_pass  (flag carried, NOT applied here)            ║
        ║      └─ shared: utils/cleaning_functions/cleaning.py        [1]   ║
        ╚═══════════════════════════════╤═══════════════════════════════════╝
        ╔═══════════════════════════════▼═══════════════════════════════════╗
        ║  LOAD SCRIPTS   pipeline/etl/load/                          [3]   ║
        ║  UPSERT (ON CONFLICT DO UPDATE / DO NOTHING)                      ║
        ╚═══════════════════════════════╤═══════════════════════════════════╝
        ╔═══════════════════════════════▼═══════════════════════════════════╗
        ║  STAGING + PRODUCTION   datamodels/models/                  [3]   ║
        ║  Unique constraints collapse duplicates. ONE definition tree      ║
        ║  reaching both environments via the same alembic chain            ║
        ╟───────────────────────────────────────────────────────────────────╢
        ║  GITHUB ACTION CHECKS                                       [0]   ║
        ║  Gates schema + tests only. NOTHING validates data content        ║
        ╚═══════════════════════════════╤═══════════════════════════════════╝
                     ┌──────────────────┴──────────────────┐
   ╔═════════════════▼═══════════════╗  ╔══════════════════▼══════════════════╗
   ║  MAT. VIEWS — data_portal [21]  ║  ║  MAT. VIEWS — ca_biositing    [2]   ║
   ║  data_portal_views/*.py         ║  ║  views.py                           ║
   ║  12 mv_biomass_* views          ║  ║  8 views: analysis_data, usda_*,    ║
   ║                                 ║  ║  landiq/billion-ton tilesets        ║
   ║  ┌───────────────────────────┐  ║  ║                                     ║
   ║  │ common.py           [7]   │◄─╫──╫── imported by views.py:19           ║
   ║  │ EXCLUDED_RESOURCES,       │  ║  ║   (shared QC layer, not a copy)     ║
   ║  │ qc_pass, sums, ICP, ult.  │  ║  ║                                     ║
   ║  └───────────────────────────┘  ║  ║                                     ║
   ╚═════════════════╤═══════════════╝  ╚══════════════════╤══════════════════╝
   ╔═════════════════▼═══════════════╗  ╔══════════════════▼══════════════════╗
   ║  BIOCIRV PORTAL             [0] ║  ║  API ENDPOINTS                [2]   ║
   ║  Frontend for users             ║  ║  REST API for developer access      ║
   ║  NOT SCANNED — submodule        ║  ║  pagination cap, facet null-drops   ║
   ╚═════════════════════════════════╝  ╚═════════════════════════════════════╝
```

### The two view stacks — related, not redundant

`data_portal_views/` and `views.py` sit next to each other and both define materialized views, which invites the assumption that one supersedes the other. They are not redundant, and the relationship runs one way.

**They share no view.** Zero overlap in names or output shape:

| | `data_portal_views/*.py` → `data_portal` | `views.py` → `ca_biositing` |
|---|---|---|
| Views defined | 12 `mv_biomass_*` | 8: `analysis_data_view`, `analysis_average_view`, `usda_census_view`, `usda_survey_view`, `usda_resource_commodity_view`, `landiq_record_view`, `landiq_tileset_view`, `billion_ton_tileset_view` |
| Shape | Denormalized, one row per resource / per resource-parameter | Row-level observations, USDA lookups, and geospatial tilesets |
| Consumer | Portal / biomass search UI | REST API and map tiles |

**`views.py` imports from `data_portal_views`, not the reverse.** [views.py:19-24](src/ca_biositing/datamodels/ca_biositing/datamodels/views.py#L19-L24):

```python
from .data_portal_views.common import (
    get_sum_constraints_subquery, get_ultimate_filter,
    get_icp_filter, get_resource_filter,
)
```

So `common.py` is the shared QC layer for both stacks. That is deliberate reuse — and it is why F-16 through F-22 are genuinely *one rule each*, not duplicated pairs.

`views.py` also owns the single refresh entry point for the whole system: [refresh_all_views()](src/ca_biositing/datamodels/ca_biositing/datamodels/views.py#L520) refreshes the `ca_biositing` views by name, then discovers and refreshes every `data_portal` matview dynamically from `pg_matviews`.

**Where they do diverge** is narrower than the file layout suggests:

| Rule | `data_portal` | `ca_biositing` |
|---|---|---|
| Excluded resources, `qc_pass != 'fail'`, ultimate whitelist + ≤100, ICP ppm, both sum bounds | Yes | Yes — inherited from `common.py` |
| ICP ≤ 500,000 ppm (F-23) | **Yes** | **No** |
| Three-county restriction (F-25) | **Yes** (volume views only) | **No** |
| USDA record types | Separate dedicated views | Excluded from `analysis_data_view` (F-37) |

Only the first of those three is an unexplained asymmetry; the other two follow from the stacks answering different questions.

| | `data_portal.mv_biomass_*` | `ca_biositing.analysis_data_view` |
|---|---|---|
Both are deployed by the same alembic chain — migration 0021 drops and recreates 9 `data_portal` views and 3 `ca_biositing` views in a single revision — and both were touched by the newest migration in the repository. Neither stack is abandoned.

### Where the analyst flag enters

`qc_pass` is not computed by the pipeline. It is a spreadsheet column named `qc_result`, renamed during transform in ten separate files ([calorimetry_record.py:99](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/calorimetry_record.py#L99), [compositional_record.py:75](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/compositional_record.py#L75), [fermentation_record.py:136](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/fermentation_record.py#L136), [gasification_record.py:118](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/gasification_record.py#L118), [icp_record.py:62](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/icp_record.py#L62), [pretreatment_record.py:87](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/pretreatment_record.py#L87), [proximate_record.py:74](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/proximate_record.py#L74), [ultimate_record.py:74](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/ultimate_record.py#L74), [xrd_record.py:98](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/xrd_record.py#L98), [xrf_record.py:103](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/xrf_record.py#L103)).

The pipeline never filters on it. Every record marked `fail` is still stored in the base tables. The exclusion happens only at the view layer. So a `fail` record is **hidden, not removed** — it is queryable by anyone with direct DB access.

---

## 2. Priority filter inventory

See [filter-inventory.csv](audit/filter_inventory/filter-inventory.csv) for the full table with all fields (Rule, Pipeline stage, Data affected, Trigger, Effect, Source, Related rules, Questions). Rows are generated from [build_inventory.py](audit/filter_inventory/build_inventory.py), which is the editable source of truth.

**48 rules.** Stages follow the team's own vocabulary for "places where filtering happens." Shared helper modules are *not* separate stages — each rule is filed under the stage that consumes it, and a **Shared script** column records which helper it comes from, so a diagram can group by helper without fragmenting the stage list.

| Stage | Rules | Effect summary |
|---|---|---|
| Google Sheets | 1 | Analyst sets the flag that later hides records |
| Extract Scripts | 2 | Records never enter the pipeline |
| Orchestration (Prefect flows) | 5 | Whole datasets or records skipped, usually silently |
| Transform Scripts | 8 | Rows dropped in pandas before load |
| Load Scripts | 3 | Rows dropped or silently replaced on write |
| Staging + Production (table definitions) | 3 | Constraints collapse duplicate rows |
| GitHub Action Checks | **0** | Gates schema and tests only — see below |
| Materialized Views — `data_portal` | 21 | Records hidden from portal outputs |
| Materialized Views — `ca_biositing` | 2 | Records hidden from API outputs |
| API Endpoints | 2 | Records withheld at request time |
| BioCirV Portal | **0** | Not scanned — see below |
| Stale artifact (not deployed) | 1 | No live effect; documents behaviour the system lacks |

Grouped by shared script:

| Shared script | Rules | Note |
|---|---|---|
| `data_portal_views/common.py` | 7 | F-16 – F-22. Consumed by **both** view stacks |
| `data_portal_views/common.py` via `views.py` import | 1 | F-38 — the `ca_biositing` stack inheriting the above |
| `utils/cleaning_functions/cleaning.py` | 1 | F-44 |

**`common.py` is the single densest concentration of inclusion logic in the repository** — seven rules in 221 lines, imported by both view stacks. `EXCLUDED_RESOURCES`, `qc_pass != 'fail'` across 11 record types, the ultimate-parameter whitelist, the ≤ 100 bound, the ICP-ppm rule, and both sum constraints all originate there. It executes nothing itself, which is exactly why it is easy to miss reading stage by stage. If one file is reviewed first, it should be this one.

### Two stages carry no rules — and that is the finding

**GitHub Action Checks — zero record-inclusion rules.** Eleven workflows exist. [migrations.yml](.github/workflows/migrations.yml) runs `alembic upgrade head`, `alembic check` (verifies migrations match the models) and `alembic downgrade base`; [ci.yml](.github/workflows/ci.yml) runs pytest across the three packages. These gate *code and schema*, never data content. **Nothing in CI validates that a pipeline run produced a plausible number of records** — which is precisely where F-42 and F-43, the silent whole-dataset drops, would be caught.

**BioCirV Portal — not scanned.** The frontend is a git submodule (`sustainability-software-lab/cal-bioscape-frontend`) that is not checked out in this working copy. Any client-side hiding — default filter state, empty-value suppression, pagination defaults, feature flags — is uninventoried. Zero here means *unexamined*, not *clean*.

### One note on Staging vs Production

Both appear in the stage vocabulary, but table definitions live in a single `datamodels/models/` tree and reach both environments through the same alembic chain. There is no environment-conditional filtering anywhere in the scanned scope, so no rule can be assigned to one and not the other. They are kept as one combined stage rather than listing all three rules twice. If the distinction matters for review, it is better as a *column* — "confirmed live in staging / production" — than as a stage. The one open environment question is whether `biocirv-staging` is migrated through revision `0021`.

**On model-level validation:** there is none. A search for `@field_validator`, `@validator`, `@model_validator` and `def validate` across all 128 files in `datamodels/` returns **zero matches**. Every SQLModel class is a plain schema declaration. All validation that affects inclusion happens either in pandas during transform, or as a database constraint, or in a view predicate — never in the model layer.

> **XLSX note:** the inventory is CSV only. `openpyxl` is not present in any pixi environment, and the plan prohibits modifying configuration, so no dependency was added. [build_inventory.py](audit/filter_inventory/build_inventory.py) already contains the XLSX writer and will emit a formatted workbook automatically if `openpyxl` is ever added to the `auditor` feature. Note also that `*.csv` is globally gitignored ([.gitignore:47](.gitignore#L47)), so the CSV is local-only; the Google Sheet is the shareable copy.

The highest-impact entries, by breadth of data affected:

- **F-16 `EXCLUDED_RESOURCES`** — seven resource names hardcoded in [common.py:27-35](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L27-L35), applied to every portal MV *and* the API's `analysis_data_view`. Removes whole resources from every user-facing surface. No rationale documented beyond the comment "exclude problematic records".
- **F-17 `qc_pass != 'fail'`** — applied to 11 record types in one place ([common.py:65-75](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L65-L75)) and re-implemented individually in 5 other view files.
- **F-25 three-county restriction** — `san joaquin`, `stanislaus`, `merced` hardcoded in all five volume-estimation paths of [mv_biomass_volume_estimate.py](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py). All other California counties produce zero volume in the portal.
- **F-05 observation dedup** — `(record_id, record_type, parameter_id, unit_id)` applied three times: twice in pandas ([observation.py:137](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py#L137), [observation.py:156](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py#L156)) and once as a DB constraint ([observation.py:14-21](src/ca_biositing/datamodels/ca_biositing/datamodels/models/general_analysis/observation.py#L14-L21)).

---

## 3. Duplicate or conflict candidates

These are questions for human review, not confirmed defects.

### 3.1 `resources/sql/create_analytical_views.sql` is an orphaned, misleading artifact — RESOLVED

*This section originally flagged an unresolved risk that the REST API might be serving QC-failed records. That has now been settled by inspecting the deployed migration SQL. It is not happening. The finding downgrades from "highest priority risk" to "delete this stale file."*

The SQL file's header says:

> `-- [GENERATED] ... DO NOT EDIT MANUALLY. Matches Python definitions in src/ca_biositing/datamodels/ca_biositing/datamodels/views.py`

It does not match. [create_analytical_views.sql:77](resources/sql/create_analytical_views.sql#L77) applies exactly one filter to `analysis_data_view` (`record_type NOT IN (...)`), where [views.py:288-321](src/ca_biositing/datamodels/ca_biositing/datamodels/views.py#L288-L321) applies seven.

**But nothing executes it.** A repository-wide search for `create_analytical_views` returns zero references outside this inventory — no Python, no shell script, no pixi task, no CI config, no documentation. It is dead weight.

The deployed views come from the migration chain instead. Probing the compiled SQL inside [migration 0021](alembic/versions/0021_remove_almond_meats_from_volume_estimate.py) — the newest migration — for the `ca_biositing.analysis_data_view` definition:

| Marker | Occurrences in deployed SQL |
|---|---|
| `qc_pass` | 21 |
| `sargassum` / `lab media` (excluded resources) | 1 each |
| `proximate_sum`, `>= 95`, `<= 105` | 4 / 1 / 2 |
| `ppm` (ICP unit filter) | 1 |
| `500000` (ICP ceiling) | **0** |

So the deployed `analysis_data_view` carries the full QC filter set, compiled from `views.py`. **The REST API is not serving QC-failed or excluded-resource records.**

Two things follow:

1. **`create_analytical_views.sql` should be deleted or regenerated.** As written it documents behaviour the system does not have, and its `[GENERATED] ... DO NOT EDIT MANUALLY` header invites a reader to trust it. The inner-join-to-`unit` issue previously flagged here (F-39) exists only in this file and has no live effect.
2. **The ICP 500,000 ppm asymmetry (§3.4) is confirmed real and deployed.** The same migration's `data_portal.mv_biomass_composition` contains `500000`; `ca_biositing.analysis_data_view` does not. That divergence is genuine, not an artifact of reading the wrong source.

Remaining question, and it is a small one: whether `biocirv-staging` has migrations applied through 0021. `SELECT version_num FROM alembic_version;` settles it.

### 3.2 Documented QC semantics contradict the code

Three view modules carry docstrings stating a `pass`-only rule:

- [mv_biomass_composition.py:9](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L9) — *"QC: filtered to pass only - only includes observations from records with qc_pass = 'pass'"*
- [mv_biomass_sample_stats.py:6](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_sample_stats.py#L6) — *"QC: filtered to pass only - only counts records with qc_pass = 'pass'"*

The code in both is `qc_pass != "fail"` — which also admits `NULL`, `pending`, `''`, and any other value. Within the same file, [mv_biomass_composition.py:45](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L45) and [mv_biomass_sample_stats.py:33](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_sample_stats.py#L33) describe the `!= "fail"` behaviour correctly. The two statements cannot both be right.

**Question for review:** how many stored records have `qc_pass` set to something that is neither `pass` nor `fail`? That count is the size of the discrepancy. This scan cannot answer it without database access.

### 3.3 `UNION ALL` described as having precedence logic

[mv_biomass_volume_estimate.py:428](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L428) states:

> `# Uses UNION ALL to combine multiple paths (A, B, C, D), with precedence logic for selection`

There is no precedence logic. Lines 435–591 are a plain `union_all` of five branches with ID offsets for uniqueness. Nothing deduplicates a resource/county/year that qualifies under more than one path.

Only one anti-double-counting guard exists, on Path E only ([mv_biomass_volume_estimate.py:408-412](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L408-L412)), excluding resources that already have county-ag-report production. Paths A and C both read `CountyAgReportRecord` with no equivalent guard between them.

Note also the comment enumerates paths A–D and the offset table lists four, but five branches are unioned — Path E (`census_production_based`, offset 40,000,000) was added without updating either comment.

**Question for review:** can a single (resource, county, year) legitimately appear via both Path A and Path C, and if so, does `mv_biomass_search`'s `SUM` over this view double-count it? [mv_biomass_search.py:135-146](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py#L135-L146) sums without deduplication.

### 3.4 The ICP 500,000 ppm ceiling exists in one view only

[mv_biomass_composition.py:202-208](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L202-L208) drops ICP experiments where any value exceeds 500,000 ppm. `views.py`'s `ANALYSIS_DATA_VIEW` has no such rule, so the same ICP experiment is hidden in the portal and visible through the API.

### 3.5 The ultimate ≤ 100 bound is applied twice, inconsistently

`get_ultimate_filter` ([common.py:140-158](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L140-L158)) accepts an optional `value_col` and, when given, adds `value <= 100`.

- [views.py:292](src/ca_biositing/datamodels/ca_biositing/datamodels/views.py#L292) passes `value_col`, so the bound comes from the helper.
- [mv_biomass_composition.py:66](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L66) omits `value_col`, then re-implements the bound inline at [lines 68-71](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L68-L71).

The inline version compares `literal(analysis_type) != "ultimate"`, matching only the bare string `ultimate`. The helper's version checks membership in `["ultimate", "ultimate analysis", "ultimate_analysis"]`. In `mv_biomass_composition` the analysis_type literal is always `"ultimate"`, so the two agree *there* — but the narrower form would silently stop working if the literal were ever changed to `"ultimate analysis"`.

### 3.6 Placeholder-token drops use inconsistent case handling

Records whose `record_id` is a placeholder string are dropped in several transforms, but the token list differs:

- [fermentation_record.py:164](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/fermentation_record.py#L164) and [pretreatment_record.py:131](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/pretreatment_record.py#L131) use `['-', 'nan', 'None', '']` — capital `None`
- [gasification_record.py:148](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/gasification_record.py#L148) uses `['-', 'nan', 'none', '']` — lowercase `none`
- [experiment.py:114](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/experiment.py#L114) uses `['-', 'nan', 'none', '']` on `name`, not `record_id`

Whether this matters depends on whether upstream cleaning lowercases before this point. `standard_clean` is applied in the observation transform ([observation.py:50](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py#L50)) and is documented as lowercasing data — if it runs before these filters in every path, the variants are equivalent. This scan did not trace every call order.

### 3.7 Null-to-zero coercion for XRF/ICP changes what survives a later filter

[observation.py:57-64](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py#L57-L64) fills null values with `0` for XRF and ICP records (excepting ICP `y-axial` / `y-radial`). The comment attributes it to "User request".

Fifty-five lines later, [observation.py:119](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py#L119) drops rows with a null `value`. So the coercion is not cosmetic — it decides whether those XRF/ICP rows are stored at all. A null XRF measurement becomes a stored zero; a null measurement of any other type is discarded.

**Question for review:** is a null XRF/ICP reading semantically "below detection limit" (≈ 0) or "not measured" (≠ 0)? The two produce different averages downstream in `mv_biomass_composition`.

### 3.8 `qc_pass != 'fail'` is re-stated in five view files

Beyond the central `resource_analysis_map` in [common.py:65-75](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L65-L75), the same predicate is written again in [mv_biomass_composition.py:65](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L65), [mv_biomass_composition.py:99](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L99), [mv_biomass_composition.py:109](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L109), [mv_biomass_fermentation.py:85](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py#L85), [mv_biomass_fermentation.py:144](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py#L144), [mv_biomass_gasification.py:52](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_gasification.py#L52), and [mv_biomass_sample_stats.py:38](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_sample_stats.py#L38).

These currently agree. The duplication is a maintenance risk rather than a present conflict — but it means "change the QC rule" is an eight-location edit, and §3.2 shows the docstrings have already drifted from the code.

### 3.9 The three-county filter is written five times

`func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])` appears at [lines 87](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L87), [182](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L182), [257](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L257), [351](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L351), and [405](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L405). Unlike `EXCLUDED_RESOURCES`, it is not a named constant.

Meanwhile the extract stage pulls **all 58 California counties** ([usda_census_survey.py:144](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/usda_census_survey.py#L144)) and the base tables store them. So 55 counties' worth of census and county-ag-report data is loaded, stored, indexed — and then filtered out at the view layer. Data is hidden, not absent.

### 3.10 `year >= 2017` appears in six places

[mv_biomass_volume_estimate.py:85](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L85), [:178](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L178), [:255](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L255), [:349](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L349), [:403](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L403), and [mv_usda_county_production.py:74](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_usda_county_production.py#L74). Consistent, undocumented, and hardcoded. The extract stage sets `YEAR = None` ([usda_census_survey.py:50](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/usda_census_survey.py#L50)), meaning all available years are pulled and stored.

### 3.11 `almond meats` — a mapping removed, a question left open

Migration [0021](alembic/versions/0021_remove_almond_meats_from_volume_estimate.py) removed the `'almond meats' → 'almond hulls'` pair from the commodity name map. The Python source at [mv_biomass_volume_estimate.py:199-206](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L199-L206) agrees — six pairs remain, no almond meats. Source and latest migration are consistent here.

The map itself is worth flagging: it is a hardcoded six-row literal union matching `primary_ag_product.name` to `resource.name` by lowercase string. Any commodity not named in that literal gets no Path C volume, silently. `almond woodchips`, `almond hulls and shells mix`, and `almond shells and hulls mix` also appear in `EXCLUDED_RESOURCES` — so almond-related records are shaped by at least three separate hardcoded lists.

### 3.12 Three different failure postures for the same class of problem

The orchestration layer handles "the source data is unusable" in three incompatible ways, and which one you get depends on the flow:

| Posture | Behaviour | Example |
|---|---|---|
| **Silent skip, flow succeeds** | Exception caught, `None` returned, dataset omitted | [analysis_records.py:65-67](src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_records.py#L65-L67) |
| **Early return, flow succeeds** | Empty frame detected, `return` before load | [billion_ton_etl.py:37,57](src/ca_biositing/pipeline/ca_biositing/pipeline/flows/billion_ton_etl.py#L37) |
| **Hard fail** | `raise ValueError` | [gasification_archive_pipeline.py:34-42](src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py#L34-L42) |

The first two are the concerning ones for this inventory's purpose. `safe_extract` catches `ValueError` and `IOError` around an entire analysis-type extraction; if the proximate spreadsheet is malformed, **every proximate record for that run disappears and the Prefect flow reports success.** The only trace is a `logger.exception` line.

This is a different *kind* of exclusion from everything else in the inventory. Rules F-01 through F-41 are deliberate: someone wrote a predicate. F-42 and F-43 are incidental — data goes missing because of an error path, at whole-dataset granularity, with no record-level accounting.

**Question for review:** is there alerting on these log lines? If not, a silently-empty analysis type would be indistinguishable from "no new data this run" until someone noticed the portal was missing a whole category.

---

## 4. Discovery gaps

Areas relevant to the Phase 1 question that this scan could not fully inspect.

1. **Front end.** [frontend/](frontend/) is a git submodule (`sustainability-software-lab/cal-bioscape-frontend`) that is not checked out in this working copy. Any client-side hiding — default filter state, empty-value suppression, pagination defaults, feature flags — is entirely uninventoried. This is a substantial gap: the plan explicitly asks about records "displayed in the front end."

2. ~~**Which view definition is actually deployed.**~~ **RESOLVED** — see §3.1. The migration chain deploys the `views.py`-compiled definition with full QC filtering; `create_analytical_views.sql` is orphaned and executes nowhere. One residual check remains: confirm `biocirv-staging` is migrated through revision `0021` (`SELECT version_num FROM alembic_version;`).

3. **Analyst spreadsheets.** `qc_result` originates in Google Sheets or Excel files outside the repository. The criteria an analyst uses to mark a record `fail` are not in version control, and neither is the set of permitted values. `audit/` contains Google Sheets tooling ([audit/skills/anomaly_tracker.py](audit/skills/anomaly_tracker.py)) but was excluded from this scan's scope.

4. **Seeded parameter and unit IDs.** [mv_biomass_volume_estimate.py:42-45](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L42-L45) hardcodes integer IDs (`_acreage_unit_id = 18`, `_param_bearing_id = 5`, `_param_bnb_id = 7`, `_param_harvested_id = 3`) with the comment "stable across environments (seeded from migrations)". If a seed differs between environments, these join predicates match the wrong parameter and records vanish with no error. This scan did not verify the seeds.

5. **`resource_analysis_map` join semantics.** [common.py:63-76](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L63-L76) joins observations to records on `resource_id == record_id`, comparing what appear to be different identifier spaces. Several transforms lowercase `record_id` before load ([observation.py:116](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/observation.py#L116)) and several views compare with `func.lower()` on both sides. Whether any records are lost to case or type mismatch here needs a row-count check against the live database.

6. **`versions_old/` migrations.** Excluded from scope by decision. They contain view definitions superseded by `versions/`, including [3b255400a04e_update_analysis_data_view_to_filter_.py](alembic/versions_old/3b255400a04e_update_analysis_data_view_to_filter_.py), whose name suggests it is directly relevant to §3.1. Worth a targeted read if that question is pursued.

7. **`audit/`, `exports/`, `analysis/`, `scripts/`.** Excluded by scope decision. [exports/compiled_views.sql](exports/compiled_views.sql) and [exports/mv_biomass_search_compiled.sql](exports/mv_biomass_search_compiled.sql) may be closer to deployed reality than the Python sources.

8. **Refresh cadence.** Materialized views only reflect base-table state as of their last `REFRESH`. A record can satisfy every inclusion rule and still be absent from the portal because no refresh has run. No refresh scheduling was found within the scanned scope.

---

## 5. Possible follow-up

Encountered during the scan, outside Phase 1 scope, potentially significant later.

- **Unit coercion in ICP filtering.** [common.py:161-166](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L161-L166) requires `lower(unit) == 'ppm'` for ICP records. Records reported in `mg/kg` (numerically identical to ppm) would be excluded rather than converted. Unit conversion is out of scope, but here it determines inclusion.
- **`ash` → `ash solids` parameter renaming.** Applied in [common.py:48-51](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L48-L51) and again in [mv_biomass_composition.py:50-53](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L50-L53). A rename, so out of scope — but the proximate sum constraint (F-21) matches on `"ash solids"`, so a missed rename would change which experiments pass the 95–105 window.
- **`lignin` vs `lignin+`.** Handled differently in two places: summed in [common.py:212-214](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L212-L214) via `coalesce(avg(lignin), avg(lignin+))`, but in [mv_biomass_search.py:66-76](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py#L66-L76) via a `case` preferring `lignin` and falling back to `lignin+`. Affects the compositional sum, hence inclusion.
- **Percentile tag thresholds.** [mv_biomass_search.py:149-190](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py#L149-L190) computes "low/high moisture" style tags from the 10th/90th percentile of the *already QC-filtered* population. Tags do not remove records, but if the front end offers tag-based filtering, they become an inclusion mechanism one layer up.
- **Fermentation sugar-consumption validation.** [mv_biomass_fermentation.py:146-158](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py#L146-L158) permits absolute error up to 100%. The inline comment calls this "~100% tolerance". A 100% tolerance admits nearly everything; whether that is the intent is unclear.
- **Rate limiting and pagination.** [dependencies.py:31](src/ca_biositing/webservice/ca_biositing/webservice/dependencies.py#L31) caps API page size at 100 with no documented cursor. A client that does not paginate correctly sees a truncated dataset — records withheld by protocol rather than by rule.
- **`standard_clean` lowercasing.** Applied broadly in transforms. Out of scope as normalization, but §3.6 shows placeholder-token filters depend on its ordering.

---

## 6. Method and limitations

Discovery followed imports and data flow from the view definitions backwards to the transforms, and forwards to the API services, rather than grepping for `filter` / `exclude` / `validate`. Several of the rules above — the three-county restriction, the commodity name map, the null-to-zero coercion — contain none of those words.

**Revision notes.** This report has been revised twice after review; both revisions are recorded here rather than silently folded in.

*Revision 1 — orchestration layer.* The first pass reported 41 rules and omitted the Prefect flows entirely; `src/.../pipeline/flows/` had not been scanned. Six rules were added (F-42 – F-47). The class of exclusion they represent — incidental loss through error paths rather than deliberate predicates — is discussed in §3.12 and was not otherwise represented.

*Revision 2 — stage taxonomy, redundancy, and F-38.* Three changes:

- **Stages were re-cut to the team's own vocabulary** (Google Sheets → Extract → Orchestration → Transform → Load → Table Definitions → Materialized Views → API). Shared helpers are no longer pseudo-stages; a `Shared script` column carries that grouping instead. One rule was added, F-48, for the analyst QC decision made in the source spreadsheet — a stage the earlier taxonomy had no box for, holding what is arguably the highest-leverage inclusion decision in the system. Total: 48 rules.
- **The "two parallel view stacks" framing was corrected.** It implied duplication. `views.py` and `data_portal_views/` share no view and serve different consumers; `views.py` *imports* the QC helpers from `data_portal_views/common.py`. See §1.
- **F-38 was resolved and downgraded.** It had been the report's highest-priority open risk, on the premise that `create_analytical_views.sql` might have produced the deployed view. Probing the compiled SQL in migration 0021 shows the deployed view carries the full QC filter set, and that the `.sql` file is executed by nothing. The risk did not exist; the stale file does. See §3.1.

Limitations to state plainly:

- **No database access.** Every "how many records does this affect?" question is unanswered. The inventory records rule existence and location, not magnitude.
- **Compiled SQL in migrations was not read line by line.** Migrations 0004–0021 embed single-line compiled SQL up to several hundred KB. Rules were read from the Python sources they are compiled from, and migrations were checked only for targeted differences (§3.11). If a migration was hand-edited after compilation, this scan would not detect it.
- **`versions_old/` and four top-level directories were excluded by scope decision**, listed in §4.
- **The front end was not scanned at all.**
- **No claim is made about whether any rule is correct.** Where the repository documents no rationale, the inventory says `Unknown`.
