---
name: filter-inventory
description: Inventory every rule in the BioCirv codebase that decides whether a record reaches stored or user-facing outputs, and publish it as a reviewable table. Use this whenever someone asks where data is being filtered, excluded, dropped, hidden, or removed; why records are missing from the portal or API; whether a filter is applied in more than one place; or asks to re-run, update, or extend the filter audit. Also use it when someone asks a narrower version of the same question ("why doesn't resource X show up", "is qc_pass applied to the API too") — the inventory is usually the fastest way to answer, and answering from it keeps the inventory honest.
---

# Filter Inventory

Produce a first-pass inventory of every rule that affects **record inclusion** — anything that decides whether a record continues through the pipeline, is stored, appears in a view, is returned by an API, or is displayed to a user.

The question this answers: **where and why can data be removed from, excluded from, or hidden in BioCirv outputs?**

This is a *documentation* task, not a remediation task. Do not modify pipeline code, change configuration, decide where filters should ideally live, or judge whether a scientific rule is correct. Record what the repository shows and hand the judgement calls to humans.

## Four modes

**Mode A — full inventory.** No prior inventory exists, or scope has changed enough to warrant starting over. Follow the whole workflow below.

**Mode B — delta re-audit.** An inventory already exists. This is the common case and it is *not* a fresh scan. Read `audit/filter_inventory/filter-inventory.csv` first, then re-scan and reconcile:

- Rules still present and unchanged → keep the ID, keep the reviewer's columns
- Rules whose implementation moved or changed → keep the ID, update `Source` and `Effect`, note the change
- Rules that no longer exist → do **not** delete the row. Set `Effect` to describe the removal and let the reviewer close it out. A silently vanished rule looks identical to a rule you failed to find.
- Genuinely new rules → append with the next free ID

IDs are permanent. A reviewer's `Priority` and `Review status` are anchored to them, and renumbering destroys months of review work.

**Mode C — scoped inventory.** "Audit filtering for just <subsystem>." Neither A nor B fits: Mode A renumbers and destroys reviewer anchoring, and Mode B's "never delete a vanished rule" is wrong here, where most rows are absent because they are out of scope, not gone.

Do this instead: write the scope boundary down *before* scanning, carry in-scope existing rows across verbatim with their IDs and reviewer columns, and give genuinely new findings a provisional prefix (`G-` for gasification, etc.) so two scoped audits cannot both mint `F-49`. Add a column recording why each row is in scope. Produce the result as a separate file; do not overwrite the full inventory, and never push a partial row set to the Sheet — a push with missing IDs reports them as orphans and drops their reviewer edits.

**And scan, do not just filter the existing table.** A scoped request usually arrives precisely because the area is new and under-covered. Filtering the CSV would have returned 20 carried rows and missed 10 new ones, including two high-severity findings.

**Mode D — narrow question.** "Why doesn't resource X show up?" Answer from the existing inventory; two lines beat a full audit. But do not let the scope boundaries below stop you looking: they exist to bound a *full* audit, and for a single question the answer may well sit in `analysis/`, `resources/assets/`, or git history. If answering surfaces a rule the inventory lacks, say so plainly in the answer and offer to add it — the inventory only stays honest if questions feed back into it.

## Before scanning: settle scope

These four questions changed the shape of the work last time. Ask them up front rather than guessing.

1. **Frontend.** `frontend/` is a git submodule and is usually not checked out. Init it and scan, or skip and log as a gap?
2. **Directory scope.** Core is `src/`, `alembic/versions/`, `resources/sql/`, `.github/workflows/`. Also include `audit/`, `exports/`, `analysis/`, `scripts/`, `alembic/versions_old/`?
3. **Google Sheet.** Publish to the shared sheet, or produce local files only? If publishing, the service account needs Editor access.
4. **Deliverable location and commit.** Files land in `audit/filter_inventory/`. Commit, or leave uncommitted for review?

## Method

**Verify the premise before scanning.** If the request asserts something changed ("we merged X last week"), check it first. `git log <last-report-date>..HEAD -- src/` takes thirty seconds and can turn a full re-audit into a one-line answer. Two independent eval runs found that a "merged" branch was 16 commits ahead and not an ancestor of `main` — and that stale `__pycache__/*.pyc` with no adjacent `.py` made it look merged. Both nearly believed the `.pyc` files. Confirm with `git merge-base --is-ancestor <branch> main`, never by the presence of compiled artifacts.

**A rule can be an absence.** The most consequential rule found so far is F-50: `views.py` outer-joins nine record tables and omits two, so gasification and FTNIR observations coalesce to a NULL `resource_id` and vanish at the next inner join. Nobody wrote a predicate, so no keyword search finds it. When a view enumerates handlers per type, list the types the codebase has and diff against the ones the view handles.

**Use a positive control when claiming something is missing.** A count of zero proves nothing on its own — the query may be wrong. `gasification_record` appearing 0 times in the deployed SQL only became evidence beside `fermentation_record` appearing 12 times. Always pair an absence claim with a peer that should be present.

**Check which services bypass views entirely.** Confirming that every *view* applies a filter is not the same as confirming every *endpoint* is filtered. F-49 exists because `AvailabilityService` queries base tables directly and never touches a view, so the exclusion never applies. In `webservice/services/`, any service not importing from `_canonical_views.py` is reading raw tables — check those first.

**Follow data flow, not keywords.** Grepping for `filter`, `exclude`, `validate` will miss most of what matters. Last audit, the three-county restriction, the hardcoded commodity name map, and a null-to-zero coercion that decided whether rows were stored at all contained none of those words.

Work backwards from the outputs. Start at the view definitions — they concentrate the most rules and they name the tables they read. Then trace back into transforms and forward into API services.

**Read Python sources, probe compiled SQL.** Migrations embed single-line compiled SQL, hundreds of KB per file. Reading them directly will exhaust the context window for very little return. Read the Python that compiles into them, then verify what is *deployed* by counting markers in the newest migration:

```python
t = pathlib.Path("alembic/versions/00NN_<latest>.py").read_text(encoding="utf-8", errors="replace")
i = t.find("CREATE MATERIALIZED VIEW <schema>.<view>")
seg = t[i:i+40000]
end = seg.find("CREATE MATERIALIZED VIEW", 40)
seg = seg[:end] if end > 0 else seg
for probe in ["qc_pass", ">= 95", "500000", "<excluded name>"]:
    print(probe, seg.count(probe))
```

This distinguishes "the source says X" from "the database does X" cheaply, and it is the only way to settle drift questions without DB access.

**Verify a file is actually used before reporting on it.** Last audit nearly shipped a high-priority finding about a `.sql` file whose header read `[GENERATED] ... DO NOT EDIT MANUALLY`. A repo-wide grep for its name returned zero references — nothing executed it. The risk did not exist. Before writing up any artifact as live, grep for references to it.

**Check whether shared helpers are imported across stacks before calling anything duplicated.** Two directories both defining views look redundant until you find that one imports the other's helper module. Trace the imports.

**Record negative findings.** "There are no model-level validators anywhere in `datamodels/`" and "no CI workflow validates data content" are both real findings that change where rules could live. A stage with zero rules stays in the chart with its reason attached — an empty box makes the gap arguable; a missing box hides it.

## Coverage checklist

Every one of these produced rules last time. Work through all of them; the ones easiest to skip are the ones that got missed.

- [ ] `resources/assets/resource_info.csv` — **easily missed.** Analyst-maintained inclusion columns (`Include In Totals`, `Collected?`) that never appear in code searches. Also the only place any rationale for `EXCLUDED_RESOURCES` is recorded
- [ ] `scripts/csv_to_json.py` + `.github/workflows/gh-pages.yml` — a third published output path, separate from portal and API
- [ ] `pipeline/etl/extract/` — geographic and commodity scoping, API request parameters
- [ ] `pipeline/flows/` — **easily missed.** Prefect wrappers. Swallowed exceptions and empty-frame guards drop whole datasets while the flow reports success
- [ ] `pipeline/etl/transform/` — pandas `dropna`, `drop_duplicates`, boolean masks, placeholder-token lists
- [ ] `pipeline/utils/cleaning_functions/` — shared cleaners that can return `None` for a whole source
- [ ] `pipeline/etl/load/` — `ON CONFLICT` behaviour, pre-insert drops
- [ ] `datamodels/models/` — unique constraints, `nullable=False`; also grep `@field_validator|@validator|@model_validator|def validate`
- [ ] `datamodels/data_portal_views/` — including `common.py`, the densest single file
- [ ] `datamodels/views.py` — the second view stack; check what it imports
- [ ] `alembic/versions/` — filenames are informative; probe the newest for deployed state
- [ ] `resources/sql/` — check for orphans before trusting anything here
- [ ] `webservice/services/` and `v1/` — pagination caps, facet null-suppression, direct table reads
- [ ] `.github/workflows/` — does anything gate *data*, or only code and schema?
- [ ] `frontend/` — if in scope

## What counts as a rule

Include logic that explicitly includes or excludes records; rejects on validation; omits via SQL conditions; removes through join behaviour; discards during deduplication; uses analyst-provided flags; or hides records in an output. Also include validations that do not themselves remove records but clearly control a later inclusion decision — a null-to-zero coercion that determines whether a later `dropna` keeps the row belongs in the inventory.

Exclude routine normalisation, unit conversion, renaming, ordinary null replacement, aggregations that only summarise, warnings with no inclusion effect, and test fixtures — unless one reveals an otherwise undocumented production rule. Anything interesting but out of scope goes in a short "Possible follow-up" section rather than the table.

**One entry per meaningful rule, not per conditional.** When the same rule is implemented in several places, write one row and list every location in `Source`. That is what makes duplication visible without inflating the table. Last audit, `qc_pass != 'fail'` appeared in eight places and is one row.

## Stage taxonomy

Fixed, so inventories stay comparable across audits. `Pipeline stage` names the *place a reviewer would go looking*, in the team's own vocabulary:

```
Google Sheets                             analyst entry and QC marking
Extract Scripts                           python ingesting data into the codebase
Orchestration (Prefect flows)             flow wrappers; whole-dataset skips
Transform Scripts                         python performing data cleaning
Load Scripts                              python writing into the DB
Staging + Production (table definitions)  one models/ tree, both environments
GitHub Action Checks                      CI gates
Materialized Views - data_portal          mv_biomass_*, portal-facing
Materialized Views - ca_biositing         analysis_data_view etc., API-facing
API Endpoints                             REST API for developer access
BioCirV Portal                            frontend for users
Stale artifact (not deployed)             documented but executed by nothing
```

Shared helper modules are **not** stages. File each rule under the stage that consumes it and record the helper in the `Shared script` column — that way a diagram can group by helper without the stage list fragmenting, and the stage counts still answer "where does filtering happen".

## Inventory fields

`ID` · `Rule` · `Priority`\* · `Review status`\* · `Reviewer notes`\* · `File` · `Pipeline stage` · `Shared script` · `Data affected` · `Trigger` · `Effect` · `Source` · `Related rules` · `Questions`

\* Reviewer-owned. Emitted empty by the build and merged back from the live sheet on every push. Never populate these.

- **Rule** — plain language, one sentence, no jargon a non-engineer would trip on
- **Trigger** — the condition that fires it
- **Effect** — *removed* (never enters), *rejected* (dropped pre-load), *omitted* (excluded from an output), *hidden* (stored but not shown), or *flagged*. The removed/hidden distinction is what tells someone whether data is recoverable
- **File** — the ONE file to open to see this rule's code, full repo-relative path. Maintained in `PRIMARY_FILE_BY_ID` in `build_inventory.py`, which raises if a rule is missing an entry. Verify every path resolves before publishing
- **Source** — `file:line`, every location for a multi-site rule, full paths
- **Questions** — the uncertainty a human must resolve. Use `Unknown` where the repo documents no rationale; never invent a scientific or business justification

## Deliverables

Everything lands in `audit/filter_inventory/`:

| File | Role |
|---|---|
| `filter-inventory-report-<N>.md` | Narrative report. **Increment `<N>` each audit** — never overwrite a prior report |
| `build_inventory.py` | Source of truth for rows; emits the CSV. Edit `ROWS`, `STAGE_BY_ID`, `SHARED_SCRIPT_BY_ID` |
| `filter-inventory.csv` | Generated. Gitignored via the global `*.csv` rule — the Sheet is the shareable copy |
| `push_to_sheet.py` | `--inspect` (read-only) and `--push` (merges reviewer columns back by ID) |

Reuse the existing scripts. Do not rewrite them — the merge-back logic in `push_to_sheet.py` is what protects reviewer edits, and it has been tested.

```bash
pixi run -e auditor python audit/filter_inventory/build_inventory.py
pixi run -e auditor python audit/filter_inventory/push_to_sheet.py --inspect
pixi run -e auditor python audit/filter_inventory/push_to_sheet.py --push
```

Run `--inspect` before `--push` and report what is currently on the target tab. Never write placeholder or example values into the shared sheet to test behaviour — test merge logic offline against a stub worksheet instead.

## Report structure

```markdown
# BioCirv Filter Inventory — Report <N>
  scan date, branch, rule count, scope scanned, scope excluded, link to the Sheet

## 1. Pipeline overview
  ASCII stage diagram with per-stage rule counts in brackets
  the two view stacks: how they relate, where they diverge, whether either is redundant
  where the analyst flag enters

## 2. Inventory at a glance
  stage table with counts; shared-script table; empty stages and why they are empty

## 3. Stage-by-stage breakdown          <- the bulk
  per stage: function-group table with subcounts, then what is distinctive here

## 4. Cross-cutting patterns
  labelled categories, mostly tables. Separate "same rule written N times, all agree"
  (a maintenance note) from genuine conflicts — mixing them buries the real findings

## 5. Discovery gaps
## 6. Possible follow-up
## 7. Limitations
```

Keep the bulk in §3. Categorise §4 rather than listing findings one by one — an unstructured list of a dozen findings reads as noise, and the important ones get lost among near-misses.

Write for a mixed audience of engineers and analysts. Prefer tables over prose for anything enumerable.

## Paths must disambiguate

Always write full repo-relative paths in `File` and `Source`. This repo nests packages doubly — `src/ca_biositing/<pkg>/ca_biositing/<pkg>/` — and several filenames exist in three trees at once. `calorimetry_record.py` is a models file (8 lines), a load file (54), *and* a transform file (134); a bare `calorimetry_record.py:99` is ambiguous and overruns two of the three. Report 1 shipped exactly that error in F-48.

Shorthand also costs every reader a lookup, which makes the "verify every `file:line`" check below far more expensive than it should be.

## Environment notes

- `python` is not on PATH in the Bash tool. Use `pixi run -e auditor python`, or PowerShell for one-liners.
- `openpyxl` is absent from every pixi env, so XLSX output is skipped. The writer is already in `build_inventory.py` and activates if the dependency is ever added. Do not add it — the plan prohibits configuration changes.
- Stale `__pycache__/*.pyc` survives with no adjacent `.py` after a branch checkout. It makes deleted or never-merged modules look present. Never infer that code exists from a `.pyc`.
- `plans/` is gitignored, as is `*.csv` globally. Verify with `git check-ignore -v <path>` rather than trusting an empty `git status`.
- Google Sheets auth follows `audit/skills/anomaly_tracker.py`: `gspread.service_account(filename="credentials.json")` at the repo root.

## Verification before reporting

- [ ] Every rule ID in `STAGE_BY_ID`, and the build raises on any that is missing
- [ ] Rule counts in the report match the build output exactly
- [ ] Every `File` path resolves on disk, and every `file:line` reference checked against the current tree
- [ ] Any absence-based claim paired with a positive control
- [ ] Any claim about deployed behaviour probed against the newest migration, not just the source
- [ ] Any file described as live confirmed to have inbound references
- [ ] Reviewer columns empty in the CSV, and the push reported preserved edits
- [ ] Orphaned rule IDs from the push output reported to the user, not silently dropped
- [ ] Report number incremented; the previous report untouched

## Maintaining this skill

The canonical, git-tracked copy is `audit/skills/filter_inventory/SKILL.md`. Copies under `.claude/` or `.agents/` are generated — both directories are gitignored, so anything written there is invisible to colleagues and is overwritten on the next sync.

Two rules keep that from going wrong:

**Improvements always go to the canonical file.** If this audit teaches you something worth remembering — a directory that hid rules, a check that caught a wrong claim, a pitfall you hit — edit the canonical path, not whichever copy you happen to be reading. Then:

```bash
python audit/skills/filter_inventory/scripts/sync_skill.py --apply
```

An improvement written into a generated copy helps exactly one person once, and then disappears.

**Verify currency before relying on the method.** Colleagues edit the canonical file, and pulling their commit does not announce that a skill changed. Before starting an audit:

```bash
python audit/skills/filter_inventory/scripts/sync_skill.py --check
```

Exit 0 means in sync. Upstream drift means re-run `--apply` and re-read before proceeding. Local drift means someone edited a generated copy directly — surface it to the user rather than silently overwriting, because that edit exists nowhere else.

## Handing off

Close with what a human must decide, separated from what the code says. Last audit the shortlist was: the analyst QC flag with no documented criteria, seven hardcoded excluded resource names with no stated rationale, a three-county restriction that may be pilot scope or permanent, and a silent whole-dataset failure path with no alerting.

Those four are decisions, not defects. Surfacing them clearly is the point of the exercise — the table is the evidence, the shortlist is the deliverable.
