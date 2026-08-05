# BioCirv Filter Inventory — Phase 1 Report

**Scan date:** 2026-08-05 · **Branch:** `filter-inventory` · **48 rules**
**Question:** Where and why can data be removed from, excluded from, or hidden in BioCirv outputs?

**Scanned:** `src/`, `alembic/versions/`, `resources/sql/`, `.github/workflows/`
**Not scanned (by decision):** `frontend/` (submodule, not checked out), `audit/`, `exports/`, `analysis/`, `scripts/`, `alembic/versions_old/`

This records what the repository shows, not what the rules ought to be. Where the code states no rationale, entries say `Unknown` rather than guessing.

Full per-rule detail lives in the [Google Sheet](https://docs.google.com/spreadsheets/d/1dEp-46Jng4K6oKGA41rMyzzHLmwIfJ-6p1KRnwnUpog/edit#gid=0) and [filter-inventory.csv](audit/filter_inventory/filter-inventory.csv). This report is the map, not the territory.

---

## 1. Pipeline overview

Inclusion decisions are made at nearly every stage — including the first, before any code runs. Rule counts in brackets.

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

`data_portal_views/` and `views.py` sit next to each other and both define materialized views, which invites the assumption that one supersedes the other. Neither is abandoned: migration 0021, the newest in the repo, drops and recreates 9 `data_portal` views and 3 `ca_biositing` views in one revision.

**They share no view:**

| | `data_portal_views/` → `data_portal` | `views.py` → `ca_biositing` |
|---|---|---|
| Views | 12 `mv_biomass_*` | 8: `analysis_data`, `analysis_average`, `usda_census`, `usda_survey`, `usda_resource_commodity`, `landiq_record`, `landiq_tileset`, `billion_ton_tileset` |
| Shape | Denormalized, one row per resource | Row-level observations, USDA lookups, geospatial tilesets |
| Consumer | BioCirV Portal / search UI | REST API + map tiles |

**`views.py` imports from `data_portal_views`, not the reverse** — [views.py:19-24](src/ca_biositing/datamodels/ca_biositing/datamodels/views.py#L19-L24):

```python
from .data_portal_views.common import (
    get_sum_constraints_subquery, get_ultimate_filter,
    get_icp_filter, get_resource_filter,
)
```

`common.py` is therefore the shared QC layer for both stacks — which is why F-16 – F-22 are genuinely one rule each, not duplicated pairs. `views.py` also owns the single refresh entry point for the whole system: [refresh_all_views()](src/ca_biositing/datamodels/ca_biositing/datamodels/views.py#L520) refreshes `ca_biositing` views by name, then discovers every `data_portal` matview from `pg_matviews`.

**Where they diverge:**

| Rule | `data_portal` | `ca_biositing` | Explained? |
|---|---|---|---|
| Excluded resources, `qc_pass != 'fail'`, ultimate whitelist + ≤100, ICP ppm, both sum bounds | Yes | Yes — inherited from `common.py` | n/a, shared |
| ICP ≤ 500,000 ppm (F-23) | **Yes** | **No** | **No — unexplained** |
| Three-county restriction (F-25) | **Yes** (volume views only) | **No** | Yes — different purpose |
| USDA record types | Separate dedicated views | Excluded from `analysis_data_view` (F-37) | Yes — routed elsewhere |

### Where the analyst flag enters

`qc_pass` is not computed. It is a spreadsheet column named `qc_result`, renamed during transform in ten files. The pipeline **never filters on it** — every record marked `fail` is stored in the base tables and excluded only at the view layer. A `fail` record is **hidden, not removed**, and remains queryable with direct DB access.

---

## 2. Inventory at a glance

| Stage | Rules | Effect summary |
|---|---|---|
| Google Sheets | 1 | Analyst sets the flag that later hides records |
| Extract Scripts | 2 | Records never enter the pipeline |
| Orchestration (Prefect flows) | 5 | Whole datasets or records skipped, usually silently |
| Transform Scripts | 8 | Rows dropped in pandas before load |
| Load Scripts | 3 | Rows dropped or silently replaced on write |
| Staging + Production (table definitions) | 3 | Constraints collapse duplicate rows |
| GitHub Action Checks | **0** | Gates schema and tests only |
| Materialized Views — `data_portal` | 21 | Records hidden from portal outputs |
| Materialized Views — `ca_biositing` | 2 | Records hidden from API outputs |
| API Endpoints | 2 | Records withheld at request time |
| BioCirV Portal | **0** | Not scanned |
| Stale artifact (not deployed) | 1 | No live effect |

**Rules originating in a shared script** — the `Shared script` column in the sheet carries this, for diagram grouping:

| Shared script | Rules |
|---|---|
| `data_portal_views/common.py` | 7 (F-16 – F-22), consumed by **both** view stacks |
| ↳ same, via `views.py` import | 1 (F-38) |
| `utils/cleaning_functions/cleaning.py` | 1 (F-44) |

### The two empty stages are findings, not blanks

**GitHub Action Checks — zero data rules.** Eleven workflows. [migrations.yml](.github/workflows/migrations.yml) runs `alembic upgrade head`, `alembic check`, `alembic downgrade base`; [ci.yml](.github/workflows/ci.yml) runs pytest. These gate *code and schema*, never data content. **Nothing validates that a pipeline run produced a plausible row count** — precisely where F-42 and F-43 would be caught.

**BioCirV Portal — not scanned.** Frontend is an unchecked-out submodule. Client-side hiding (default filter state, empty-value suppression, feature flags) is uninventoried. Zero means *unexamined*, not *clean*.

### One note on Staging vs Production

Table definitions live in a single `datamodels/models/` tree reaching both environments through the same alembic chain. No environment-conditional filtering exists anywhere in scope, so no rule can be assigned to one and not the other; they are kept as one combined stage. If the distinction matters, it belongs as a *column* ("confirmed live in staging / production"), not a stage. Open question: whether `biocirv-staging` is migrated through revision `0021`.

---

## 3. Stage-by-stage breakdown

What kind of filtering happens where, grouped by function.

### Google Sheets — 1 rule

| Function group | Rules | Notes |
|---|---|---|
| Analyst QC marking | 1 | F-48 |

The only rule in the system decided by a human rather than a predicate. An analyst sets `qc_result` during entry or review; F-17 acts on it downstream, hiding the record across **both** view stacks and all 11 record types. No version control, no documented criteria, no recorded reviewer. Arguably the highest-leverage inclusion decision in the system.

### Extract Scripts — 2 rules

| Function group | Rules | Notes |
|---|---|---|
| Geographic scoping | 2 | F-01 state = CA; F-02 the 58 CA county FIPS codes |

Both act on the USDA NASS pull. F-02 re-filters what F-01 already scoped, described in the code as a defensive "in case" measure. Note the extract pulls **all 58 counties** — the three-county narrowing (F-25) happens much later, at the view layer.

### Orchestration (Prefect flows) — 5 rules

| Function group | Rules | Notes |
|---|---|---|
| Silent failure paths | 2 | F-42 swallowed extract errors; F-43 empty-frame early return |
| Source-availability gating | 3 | F-45 already-archived skip; F-46 missing GSheet URL; F-47 malformed worksheet |

**This stage holds a different *kind* of exclusion from every other.** Elsewhere, records are removed because someone wrote a predicate. Here they vanish through error paths, at whole-dataset granularity, with no record-level accounting.

F-42 is the one to know: [analysis_records.py:65-67](src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_records.py#L65-L67) wraps an entire analysis-type extraction in `except (ValueError, IOError): return None`. A malformed proximate spreadsheet removes **every proximate record for that run** while the flow reports success. Only trace is one log line.

### Transform Scripts — 8 rules

| Function group | Rules | Notes |
|---|---|---|
| Missing required field → drop | 2 | F-03 null `record_id`; F-06 null `record_id`/`parameter_id`/`value` |
| Placeholder token → drop | 2 | F-04 `['-','nan','None','']`; F-08 experiment names |
| Deduplication | 2 | F-05 observation 4-key; F-11 almond NSJV composite key |
| Null coercion that changes inclusion | 1 | F-07 XRF/ICP null → 0 |
| Whole-source drop on bad input | 1 | F-44 `standard_clean` returns `None` |

F-07 deserves attention: it fills nulls with `0` for XRF/ICP fifty-five lines before F-06 drops null-valued rows. So the coercion is not cosmetic — it decides whether those rows are stored at all. A null XRF reading becomes a stored zero; a null reading of any other type is discarded.

Drops here are largely **silent**. Only some sites log, none write a reject table, and F-06 warns only when *all* rows in a dataframe are dropped — a source losing 90% of its rows says nothing.

### Load Scripts — 3 rules

| Function group | Rules | Notes |
|---|---|---|
| Missing-key drops | 2 | F-09 blank lookup names; F-10 null `resource_id` on residue factors |
| Upsert / overwrite | 1 | F-14 `ON CONFLICT DO UPDATE` / `DO NOTHING` |

F-14 has a reporting quirk: `success_count` increments even on `DO NOTHING`, so load logs overstate rows actually written.

F-10 is quietly consequential — a resource missing a residue factor is dropped here, and then excluded from volume estimation entirely by the inner joins in F-35.

### Staging + Production (table definitions) — 3 rules

| Function group | Rules | Notes |
|---|---|---|
| Unique constraints | 3 | F-12 observation 4-key; F-13 `record_id` on all record tables; F-15 residue factor per type |

**There is no model-level validation.** A search for `@field_validator`, `@validator`, `@model_validator` and `def validate` across all 128 files in `datamodels/` returns **zero matches**. Every SQLModel class is a plain schema declaration. Inclusion is decided in exactly three places — pandas transforms, DB constraints, view predicates — and nowhere else.

F-12 is the third implementation of the same dedup rule (twice in pandas, once as a constraint).

### Materialized Views — `data_portal` — 21 rules

The largest concentration by far. Grouped by what the rule is actually doing:

| Function group | Rules | IDs |
|---|---|---|
| Analytical validity bounds | 8 | F-18 ultimate whitelist, F-19 ultimate ≤100, F-20 ICP ppm, F-21 proximate sum 95–105, F-22 compositional sum 40–105, F-23 ICP ≤500,000 ppm, F-33 fermentation sugar consistency, F-34 fermentation yield 0–105 |
| Hardcoded exclusion lists | 3 | F-16 seven resource names, F-27 almond meats removal, F-28 six-pair commodity map |
| Geographic / temporal scoping | 3 | F-25 three counties, F-26 year ≥ 2017, F-32 NSJV geoid |
| Path gating and double-count guards | 3 | F-29 Path E anti-join, F-30 residue factor type, F-31 prune_trim_yield present |
| Record-type whitelists | 2 | F-24 eleven analytical types, F-36 pricing / end-use types |
| QC gate from the analyst flag | 1 | F-17 `qc_pass != 'fail'` across 11 record types |
| Join-based removal | 1 | F-35 inner joins to Resource / Place / ResidueFactor |

Seven of these (F-16 – F-22) originate in `common.py` and are inherited by the `ca_biositing` stack.

**`common.py` is the single densest concentration of inclusion logic in the repository** — seven rules in 221 lines, imported by both stacks. It executes nothing itself, which is exactly why it is easy to miss reading stage by stage. If one file is reviewed first, it should be this one.

F-35 is the quiet one: unmatched geoids, resources and residue factors disappear through inner joins with no warning anywhere.

### Materialized Views — `ca_biositing` — 2 rules

| Function group | Rules | Notes |
|---|---|---|
| Record-type routing | 1 | F-37 USDA census/survey excluded, routed to dedicated views |
| Inherited QC set | 1 | F-38 the full `common.py` filter set, via `views.py` import |

Consumers must query three views to see all observations.

### API Endpoints — 2 rules

| Function group | Rules | Notes |
|---|---|---|
| Pagination | 1 | F-40 hard cap of 100 records per request |
| Facet null-suppression | 1 | F-41 null `resource`/`geoid`/`parameter` omitted from facet lists |

F-41 has a navigational consequence: records with a null geoid exist in the view but cannot be reached through geoid-based UI navigation.

### Stale artifact — 1 rule

F-39, in [create_analytical_views.sql](resources/sql/create_analytical_views.sql). No live effect — see §4.G.

---

## 4. Cross-cutting patterns

The old per-finding list is replaced here by pattern categories. Each row is a question for human review, not a confirmed defect.

### A. Documentation contradicts code — 2 instances

| Where | Doc says | Code does | Consequence |
|---|---|---|---|
| [mv_biomass_composition.py:9](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py#L9), [mv_biomass_sample_stats.py:6](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_sample_stats.py#L6) | `qc_pass = 'pass'` | `qc_pass != 'fail'` | Also admits `NULL`, `pending`, `''`. **How many records have `qc_pass` outside `{pass, fail}`?** That count is the size of the gap |
| [mv_biomass_volume_estimate.py:428](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L428) | "UNION ALL … with precedence logic for selection" | Plain `UNION ALL`, no dedup | Comment also lists 4 paths; 5 are unioned. Path E was added without updating it |

The second matters beyond documentation: only Path E has a double-count guard (F-29). Paths A and C both read `CountyAgReportRecord` with no equivalent. **Can one (resource, county, year) qualify under both, and does `mv_biomass_search`'s `SUM` then double-count it?**

### B. One rule, many implementations — 5 instances

All currently agree. The risk is maintenance, not present behaviour — but §4.A shows the docstrings have already drifted.

| Rule | Places | Agree today? | Note |
|---|---|---|---|
| `qc_pass != 'fail'` | 8 | Yes | 1 central + 7 restatements |
| Three-county filter | 5 | Yes | Bare literal, not a named constant like `EXCLUDED_RESOURCES` |
| `year >= 2017` | 6 | Yes | Undocumented threshold |
| Observation dedup 4-key | 3 | Yes | 2 pandas + 1 DB constraint |
| Ultimate ≤ 100 bound | 2 | Yes, narrowly | Helper matches 3 string variants; inline copy matches only `'ultimate'` — fragile if the literal changes |

One near-miss: placeholder-token lists differ in case — `'None'` in [fermentation_record.py:164](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/fermentation_record.py#L164) and `pretreatment_record.py:131`, `'none'` in [gasification_record.py:148](src/ca_biositing/pipeline/ca_biositing/pipeline/etl/transform/analysis/gasification_record.py#L148). Equivalent only if `standard_clean` lowercases first in every path; call ordering was not traced.

### C. Same data, different criteria by output — 1 instance

| Rule | `data_portal` | `ca_biositing` | Status |
|---|---|---|---|
| ICP ≤ 500,000 ppm (F-23) | Applied | Not applied | **Confirmed in deployed SQL.** The same ICP experiment is hidden in the portal and visible via the API |

### D. Hardcoded literals with no named constant — 4 instances

Each fails silently if an upstream name changes.

| What | Where | Failure mode |
|---|---|---|
| Six-pair commodity name map | [mv_biomass_volume_estimate.py:199-214](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L199-L214) | Renamed `primary_ag_product` silently zeroes Path C volumes |
| Three county names | 5 locations in the same file | No constant to change in one place |
| Seeded parameter / unit integer IDs | [mv_biomass_volume_estimate.py:42-45](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L42-L45) | A differing seed matches the wrong parameter; records vanish with no error |
| Parameter-name whitelists (pricing, end uses) | `mv_biomass_pricing.py`, `mv_biomass_end_uses.py` | Renamed parameter disappears |

Almond-related records are shaped by three separate hardcoded lists: `EXCLUDED_RESOURCES`, the commodity map, and the `almond meats` removal in migration 0021.

### E. Silent failure paths — 1 pattern, 3 postures

The orchestration layer handles "source data unusable" three incompatible ways:

| Posture | Behaviour | Example |
|---|---|---|
| Silent skip, flow succeeds | Exception caught, `None` returned | [analysis_records.py:65-67](src/ca_biositing/pipeline/ca_biositing/pipeline/flows/analysis_records.py#L65-L67) |
| Early return, flow succeeds | Empty frame detected, return before load | [billion_ton_etl.py:37,57](src/ca_biositing/pipeline/ca_biositing/pipeline/flows/billion_ton_etl.py#L37) |
| Hard fail | `raise ValueError` | [gasification_archive_pipeline.py:34-42](src/ca_biositing/pipeline/ca_biositing/pipeline/flows/gasification_archive_pipeline.py#L34-L42) |

**Is there alerting on these log lines?** If not, a silently-empty analysis type is indistinguishable from "no new data this run" until someone notices a missing category in the portal.

### F. Questions needing domain input — 4 instances

Code cannot answer these; they need a person who knows the science or the project scope.

| Question | Rule | Why it matters |
|---|---|---|
| Is a null XRF/ICP reading "below detection" (≈0) or "not measured" (≠0)? | F-07 | Decides whether the row is stored at all, and shifts downstream averages |
| Why compositional sum ≥ 40 where proximate uses ≥ 95? | F-21, F-22 | No documented rationale for either bound |
| Why these seven excluded resource names? | F-16 | `#n/a` looks like a data artifact; `alfalfa` and `lab media` look deliberate. Possibly several rules, not one |
| Is three-county / CA-only a permanent boundary or a pilot scope? | F-25, F-01 | 55 counties' data is extracted, stored and indexed, then filtered out at the view layer |

### G. Resolved during the scan — 1 instance

[create_analytical_views.sql](resources/sql/create_analytical_views.sql) declares itself `[GENERATED] ... DO NOT EDIT MANUALLY` from `views.py`, but applies one filter where `views.py` applies seven. This was initially flagged as a live risk that the API might be serving QC-failed records.

**It is not.** Repository-wide search returns zero references to the file — nothing executes it. Probing the compiled SQL for `ca_biositing.analysis_data_view` inside migration 0021 (the newest):

| Marker | Occurrences |
|---|---|
| `qc_pass` | 21 |
| `sargassum` / `lab media` | 1 each |
| `proximate_sum`, `>= 95`, `<= 105` | 4 / 1 / 2 |
| `ppm` | 1 |
| `500000` | **0** (confirms §4.C) |

The deployed view carries the full QC filter set, compiled from `views.py`. **Recommend deleting or regenerating the `.sql` file** — as written it documents behaviour the system does not have, under a header that invites trust.

---

## 5. Discovery gaps

Areas relevant to the Phase 1 question that this scan could not fully inspect.

1. **Front end.** [frontend/](frontend/) is a git submodule (`sustainability-software-lab/cal-bioscape-frontend`) not checked out in this working copy. Client-side hiding — default filter state, empty-value suppression, pagination defaults, feature flags — is entirely uninventoried. The plan explicitly asks about records "displayed in the front end."

2. **Analyst spreadsheets.** `qc_result` originates in Google Sheets outside the repository. The criteria for marking a record `fail` are not in version control, and neither is the set of permitted values. `audit/` contains Sheets tooling ([anomaly_tracker.py](audit/skills/anomaly_tracker.py)) but was out of scope.

3. **Seeded parameter and unit IDs.** [mv_biomass_volume_estimate.py:42-45](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py#L42-L45) hardcodes integer IDs described as "stable across environments (seeded from migrations)". The seeds were not verified.

4. **`resource_analysis_map` join semantics.** [common.py:63-76](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L63-L76) joins observations to records on `resource_id == record_id`, comparing what appear to be different identifier spaces. Whether records are lost to case or type mismatch needs a row-count check against the live database.

5. **Staging migration state.** Whether `biocirv-staging` is migrated through revision `0021`. `SELECT version_num FROM alembic_version;` settles it, alongside `SELECT schemaname, matviewname FROM pg_matviews ORDER BY 1,2;`.

6. **`versions_old/` migrations.** Out of scope. Includes [3b255400a04e_update_analysis_data_view_to_filter_.py](alembic/versions_old/3b255400a04e_update_analysis_data_view_to_filter_.py), whose name suggests relevance to §4.G.

7. **`audit/`, `exports/`, `analysis/`, `scripts/`.** Out of scope. [exports/compiled_views.sql](exports/compiled_views.sql) may be closer to deployed reality than the Python sources.

8. **Refresh cadence.** Materialized views reflect base-table state only as of their last `REFRESH`. A record can satisfy every inclusion rule and still be absent because no refresh has run. No refresh *scheduling* was found in scope.

---

## 6. Possible follow-up

Encountered during the scan, outside Phase 1 scope, potentially significant later.

| Item | Why it could matter for inclusion |
|---|---|
| ICP unit coercion — [common.py:161-166](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L161-L166) requires `ppm` | Records in `mg/kg` (numerically identical) are excluded rather than converted |
| `ash` → `ash solids` rename, applied in two places | The proximate sum (F-21) matches on `"ash solids"`; a missed rename changes which experiments pass 95–105 |
| `lignin` vs `lignin+` handled two different ways | [common.py:212-214](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/common.py#L212-L214) coalesces; [mv_biomass_search.py:66-76](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py#L66-L76) prefers-and-falls-back. Affects the compositional sum |
| Percentile tag thresholds — [mv_biomass_search.py:149-190](src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_search.py#L149-L190) | Tags computed from the *already QC-filtered* population. If the front end filters by tag, they become an inclusion mechanism |
| Fermentation tolerance of 100% (F-33) | A 100% tolerance admits nearly everything. Intent unclear |
| `standard_clean` lowercasing order | §4.B's placeholder-token near-miss depends on it |

---

## 7. Limitations

- **No database access.** Every "how many records does this affect?" question is unanswered. This inventory records rule existence and location, not magnitude.
- **Compiled SQL in migrations was not read line by line.** Migrations 0004–0021 embed single-line compiled SQL up to several hundred KB. Rules were read from the Python sources they compile from; migrations were probed only for targeted questions (§4.C, §4.G). A hand-edit made after compilation would not have been detected.
- **The front end was not scanned at all.**
- **`versions_old/` and four top-level directories were excluded** by scope decision, listed in §5.
- **No claim is made about whether any rule is correct.** Where the repository documents no rationale, entries say `Unknown`.

Discovery followed imports and data flow — from view definitions backwards to transforms, forwards to API services — rather than grepping for `filter` / `exclude` / `validate`. Several rules found this way, including the three-county restriction, the commodity name map and the null-to-zero coercion, contain none of those words.
