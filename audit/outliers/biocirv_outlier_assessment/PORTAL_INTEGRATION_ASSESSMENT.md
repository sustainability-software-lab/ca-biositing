# Portal Integration Assessment — BioCirV Outlier/Precision Plots

**Question:** How hard would it be to get the BioCirV replicate-precision/outlier-assessment
plots (the existing heatmap, plus the Step 6 diagnostic scatter plots once built) displayed on
the existing Data Quality Portal, viewable via `pixi run -e portal serve-portal`?

**Sequencing note (addendum):** Do this integration **once, after Step 6 is built**, not now for
the heatmap alone. See §6 for the reasoning and for concrete conventions Step 6's script(s) should
follow so the eventual portal integration is near-zero-authoring rather than requiring rework.

**Scope note:** This is a read-only investigation. No portal files, no `audit/outliers/` files,
and no `pixi run -e portal ...` commands were modified/executed while producing this document.

---

## 1. How the portal actually works (cited)

The portal is generated, not hand-maintained, by
[`audit/portal/generate_portal.py`](../../portal/generate_portal.py) (261 lines, read in full).
Mechanics, in the order the script executes them:

1. **Finds the latest audit run.** [`generate_portal.py:9-17`](../../portal/generate_portal.py:9)
   scans `audit/output/` (currently `2026-07-28_13-27-51/` and `2026-07-29_13-50-15/`) and picks
   the lexicographically-latest timestamped directory. Everything downstream is scoped to that
   one run.
2. **One target = one `llm_synthesis_<target>.json`.**
   [`generate_portal.py:32-39`](../../portal/generate_portal.py:32) globs
   `latest_run.glob("llm_synthesis_*.json")` and derives `target_name` from the filename stem
   (stripping the `llm_synthesis_` prefix). This is the **only** signal that decides which target
   pages exist — there is no direct dependency on `audit/agent.py`'s `REGISTRY` at portal-generation
   time (see §2 for why this matters).
3. **Per-target `.qmd` is fully regenerated from scratch** at
   `audit/portal/targets/<target_name>.qmd` ([`generate_portal.py:42, 175`](../../portal/generate_portal.py:42)),
   with 4 tabs inside a `{.panel-tabset}` block ([`generate_portal.py:99`](../../portal/generate_portal.py:99)):
   - **Executive Summary** — literally `synth_data.get('executive_summary', ...)`
     ([`generate_portal.py:103`](../../portal/generate_portal.py:103)) inserted **verbatim as raw
     markdown** into the `.qmd`. This is a key fact exploited in §2/§3: whatever markdown you put
     in this JSON string (including `![]()` image syntax and relative paths) is rendered as-is.
   - **Evidently Profile** — an `<iframe src="../../output/<run>/evidently/<target>.html">`
     ([`generate_portal.py:52-61, 108-109`](../../portal/generate_portal.py:52)) if that HTML
     exists. Note this iframe path already reaches **two levels up and back out of
     `audit/portal/` entirely** into `audit/output/...` — i.e., referencing files outside the
     Quarto project root via relative paths is already a proven, working pattern in this portal
     (see §3/§4 for why this matters to our own asset paths).
   - **Flagged Observations** — reads `latest_run / f"flagged_{target_name}.csv"`
     ([`generate_portal.py:117`](../../portal/generate_portal.py:117)) and renders a fixed
     8-column markdown table with hard-coded column names (`record_id`, `resource_name`,
     `provider_codename`, `sample_date`, `parameter_name`, `observed_value`, `z_score`,
     `severity`) ([`generate_portal.py:126-141`](../../portal/generate_portal.py:126)).
   - **Custom Visuals ("Dynamic Asset Discovery")** —
     [`generate_portal.py:63-90`](../../portal/generate_portal.py:63): it globs **only two search
     roots**, `Path("analysis")` and `Path("exports/plots")`
     ([`generate_portal.py:65`](../../portal/generate_portal.py:65)), for filenames matching
     `{target_name}` (plus a couple of stemmed/pluralized variants — strip `mv_biomass_`/`mv_`
     prefix, drop a trailing `al`, or map `composition`→`compositional`;
     [`generate_portal.py:68-75`](../../portal/generate_portal.py:68)), using glob patterns
     `f"*{term}*"` and `f"{term}*"` ([`generate_portal.py:80`](../../portal/generate_portal.py:80))
     restricted to `.png`/`.html`/`.svg`/`.ipynb` suffixes
     ([`generate_portal.py:84`](../../portal/generate_portal.py:84)). Matches are **copied**
     (`shutil.copy2`) into `audit/portal/assets/<original-relative-path>/`
     ([`generate_portal.py:159-164`](../../portal/generate_portal.py:159)) and rendered as a
     **markdown link** (`[name](../assets/...)`), **not** an inline image
     ([`generate_portal.py:167-168`](../../portal/generate_portal.py:167)) — important: even when
     this discovery mechanism does find an asset, it only links to it, it does not embed it.
4. **`index.qmd` is fully rewritten** ([`generate_portal.py:196-225`](../../portal/generate_portal.py:196))
   with a summary table built from the same per-target loop's `target_summaries` list, plus the
   run's `executive_audit_summary.md` content appended.
5. **`_quarto.yml`'s sidebar is fully rewritten every run.**
   [`generate_portal.py:227-255`](../../portal/generate_portal.py:227) loads the existing YAML,
   *replaces* `quarto_yml["website"]["sidebar"]["contents"]` with a freshly computed list built
   purely from `target_summaries` (i.e., purely from targets that had an
   `llm_synthesis_*.json` in the latest run —
   [`generate_portal.py:238-252`](../../portal/generate_portal.py:238)), then dumps the whole YAML
   file back out. **Any sidebar entry not backed by a discovered `llm_synthesis_*.json` in the
   latest run is silently dropped the next time `generate-portal` runs.** This is the central risk
   called out in the task brief, confirmed directly in code.

**Environment:** [`pixi.toml:29`](../../../../pixi.toml:29) defines
`portal = { features = ["datamodels", "portal"] }` as a **separate environment** from `default`
([`pixi.toml:13`](../../../../pixi.toml:13)), with its own `quarto` conda dependency per-platform
([`pixi.toml:530-541`](../../../../pixi.toml:530)) and its own tasks
`generate-portal` / `serve-portal` / `build-portal`
([`pixi.toml:542-545`](../../../../pixi.toml:542)). It does **not** include `webservice`,
`pipeline`, `gis`, etc. — meaning `pixi install -e portal` (or pixi's automatic env resolution when
you run `pixi run -e portal ...`) triggers a separate solve/install the first time it's used,
downloading `quarto` if it isn't already cached.

## 2. What a "target" formally requires (`audit/agent.py` / `REGISTRY`)

[`audit/targets/registry.py`](../../../targets/registry.py) defines `REGISTRY: Dict[str, AuditTarget]`,
where `AuditTarget` ([`registry.py:7-19`](../../../targets/registry.py:7)) is a dataclass requiring
`population_sql`, `observation_sql`, `group_by_cols`, `numeric_cols`, `id_cols`, etc. — i.e., a
formal `REGISTRY` entry is a **DB-backed audit target** that only matters when
[`audit/agent.py`](../../../agent.py)'s `AuditorAgent.run()` executes the full skill pipeline
(Evidently profiling, GX assertions, LLM synthesis) against a live database connection
([`agent.py:57-211`](../../../agent.py:57)) and writes `llm_synthesis_<name>.json` /
`flagged_<name>.csv` into a **new** `audit/output/<timestamp>/` run directory.

Critically, **`generate_portal.py` never imports or touches `REGISTRY` at all.** Its only input
contract (§1, step 2) is: *does a file named `audit/output/<latest_run>/llm_synthesis_<X>.json`
exist, and does it parse as JSON with (optionally) an `executive_summary` string, a
`grouped_issues` list, and a `flagged_count` int?* Every other field access in the generator uses
`.get(..., default)` ([`generate_portal.py:103, 178, 191`](../../portal/generate_portal.py:103))
so a minimal or even empty JSON object (`{}`) would not crash it — it would just render
"No summary available." / "No grouped anomalies detected." / `flagged_count: N/A`.

**Conclusion:** a lightweight, hand-authored `llm_synthesis_<fake_target>.json` absolutely can
piggyback a full page onto the existing generator **without modifying `generate_portal.py`,
without touching `REGISTRY`, and without running the DB-backed auditor pipeline at all** — as
long as it's dropped into whatever directory `generate_portal.py` currently considers "the latest
run" (`audit/output/<timestamp>/`) at the moment someone runs `pixi run -e portal generate-portal`.
That last clause is also this option's main fragility (see §3, Option C, and §4).

## 3. Integration options considered

| # | Option | Mechanism | Difficulty / Effort | Survives re-running `generate-portal`? | Key caveat |
|---|--------|-----------|----------------------|------------------------------------------|------------|
| A | **Rely on existing Dynamic Asset Discovery glob** | Drop PNGs into `analysis/` or `exports/plots/` hoping the glob (`generate_portal.py:65-90`) matches an existing target's `search_terms` | **Not viable as literally proposed** — 0 effort but 0 payoff | N/A | No existing `REGISTRY`/target name (`calorimetry`, `compositional`, `ftnir`, `icp`, `mv_biomass_*`, `pretreatment`, `proximate`, `ultimate`, `xrd`, `xrf`) semantically matches "biocirv"/"outlier"/"precision"/"heatmap"/"diagnostic", so there is no page for these assets to attach to. Forcing a match by naming a file e.g. `icp_precision_heatmap.png` would misleadingly attach outlier-QA content to an unrelated audit target's page, and even a real match only produces a **link**, not an inline image (`generate_portal.py:167-168`) — this option effectively collapses into Option C (needs a target to exist) with none of Option C's control over placement. **Rejected.** |
| B | **Hand-authored standalone `.qmd` page** | Manually create `audit/portal/targets/biocirv_precision_outliers.qmd` embedding the PNGs (`![](...)`) and any tables directly via relative paths from `audit/portal/targets/` (e.g. `../../outliers/biocirv_outlier_assessment/outputs/precision_review_heatmap.png`), and manually add one line, `targets/biocirv_precision_outliers.qmd`, to `_quarto.yml`'s `sidebar.contents` list | **Small / ~1–2 hrs** for the single heatmap; a little more once Step 6's 5–10 plots exist (mostly copy/paste of `![]()` blocks + captions) | **No — will be silently dropped** the next time anyone runs `pixi run -e portal generate-portal`, because `generate_portal.py:238-252` rebuilds `sidebar.contents` purely from the current run's `llm_synthesis_*.json` files and has no awareness of manually-added entries; the `.qmd` file itself is untouched (safe), but its sidebar link disappears | Cheapest **path to see it once**, but this is a real, code-confirmed regression risk if `generate-portal` is re-run for the normal audit purpose (which will happen routinely as the auditor pipeline is used) — must be treated as a "remember to re-add" manual step, or automated with a tiny post-processing script outside this task's scope |
| C | **Register a proper lightweight "target"** | Hand-write `audit/output/<latest_run>/llm_synthesis_biocirv_precision_outliers.json` with just `{"executive_summary": "<markdown text with embedded ![]() image links>", "grouped_issues": [], "flagged_count": 0}`, then run `generate-portal` — it will auto-create the `.qmd` page, add it to `index.qmd`'s table, and add it to `_quarto.yml`'s sidebar entirely through existing, unmodified code | **Small / ~1–2 hrs** — most of the effort is composing the `executive_summary` markdown (which can literally be the existing [`STEP4_5_FINDINGS.md`](outputs/STEP4_5_FINDINGS.md) text, or a trimmed version of it, with `![Heatmap](../../outliers/biocirv_outlier_assessment/outputs/precision_review_heatmap.png)` inserted) | **Yes** — as long as this JSON file physically exists inside whatever directory is "latest" at generation time, it is rediscovered and regenerated identically on every future `generate-portal` run, with zero manual re-application | The JSON must live under `audit/output/<run>/`, which is timestamp-keyed and picked by "latest run" — if a *newer* real audit run directory is created later (by `pixi run -e auditor run-auditor`) **without** also copying this stub JSON into the new directory, the page disappears again on the next generate. This is a lighter-weight version of Option B's fragility, not immune to it, but self-healing as long as the stub JSON is copied forward (e.g., a tiny "seed latest run with stub" step, or simply keeping the stub in the oldest/frozen run dir and pointing `OUTPUT_ROOT`/`--run-dir` at it — out of scope to design in a read-only assessment). Also: because `executive_summary` is inserted **raw** into the `.qmd` ([`generate_portal.py:103`](../../portal/generate_portal.py:103)), embedding `![]()` markdown there is the *only* way to get an inline image via this path — the generator's own "Custom Visuals" discovery only produces download-style links, never embeds (§1). |
| D | **Small additive code change to `generate_portal.py`** | Add a special-case branch (e.g., a hard-coded list of "static markdown findings" pages, or a second glob root pointing at `audit/outliers/**/outputs/`) that is additive to existing logic | **Moderate / half day** — needs design + testing to avoid breaking existing target generation, plus it's explicitly against this task's guardrail (no modification of `generate_portal.py`) | Yes, and arguably the most "correct" long-term fix | Out of scope per this task's guardrails; noted only as the option to pursue if this integration becomes a recurring/permanent need rather than a one-off MVP artifact |

**Both Option B and Option C exploit the same underlying fact** confirmed by reading the code:
the Evidently-Profile iframe already references files **outside the `audit/portal/` Quarto
project root** via a relative path two directories up and back out
(`../../output/<run>/evidently/<target>.html>`,
[`generate_portal.py:59`](../../portal/generate_portal.py:59)), and this is the portal's normal,
working behavior today. There is nothing structurally different about referencing
`../../outliers/biocirv_outlier_assessment/outputs/precision_review_heatmap.png` from
`audit/portal/targets/*.qmd` instead — it is the same kind of relative traversal to a sibling
directory under `audit/`, so this pattern is already de-risked by the portal's own existing,
working Evidently integration rather than being a novel/untested technique.

## 4. Blockers / friction points

- **`portal` pixi environment is separate from `default`.** [`pixi.toml:12-29`](../../../../pixi.toml:12)
  shows `portal = { features = ["datamodels", "portal"] }` is its own environment; if it has never
  been used in this workspace/session, the *first* `pixi run -e portal ...` invocation triggers a
  fresh solve/install of `quarto` (and `datamodels`) for that environment, which is a one-time,
  possibly multi-minute cost unrelated to this specific task's content but a real first-run
  friction point.
- **No special Quarto syntax needed for PNG embedding.** Standard CommonMark `![alt](relative/path.png)`
  is sufficient inside a `.qmd`; Quarto (Pandoc-based) renders it as a normal `<img>` tag. No
  extra fencing or shortcode is required for a single static image (an iframe, as already used for
  Evidently HTML, is a different/heavier construct only needed for embedding another full HTML
  document, not a plain image).
- **`serve-portal` vs. `build-portal` behave differently for out-of-project assets.**
  `serve-portal` runs `quarto preview audit/portal`, which serves rendered pages while resolving
  relative paths against files still on disk in their original locations — exactly how the
  existing Evidently iframe already works today, so this task's target use case (`serve-portal`)
  is well covered by precedent. `build-portal` (`quarto render audit/portal --output-dir _site`)
  produces a self-contained static site; Quarto does not reliably bundle resources referenced via
  `../../` paths that point *outside* the project root the way it bundles project-internal assets.
  This is exactly why the existing "Custom Visuals" discovery mechanism physically `shutil.copy2`s
  matched assets into `audit/portal/assets/` before linking them
  ([`generate_portal.py:159-164`](../../portal/generate_portal.py:159)) rather than linking them
  in place. **Practical implication:** Options B/C as described (direct relative-path embedding,
  no copying) are low-friction and correct for `pixi run -e portal serve-portal` (this task's
  explicit target), but would need an extra "copy the PNG(s) into `audit/portal/assets/`" step
  added if a fully self-contained `build-portal` static export is ever required later — not needed
  for this MVP's stated goal.
- **Step 6's 5–10 diagnostic PNGs vs. today's single heatmap.** The mechanics don't change with
  more files — it's still just more `![]()` lines (Option B) or more lines inside one
  `executive_summary` markdown string (Option C) — but a single flat wall of 5–10 full-width
  images may want light presentation structure (e.g., a markdown `##` sub-heading per plot, or a
  simple 2-column grid via a Quarto `layout-ncol` div) to stay readable; this is a few extra
  minutes of markdown authoring, not a mechanism change.
- **Sidebar-overwrite risk is real and code-confirmed** (§1 step 5, §3 Option B/C caveats) — any
  approach that touches `_quarto.yml`'s sidebar by hand (Option B) will be silently reverted the
  next time `pixi run -e portal generate-portal` is run for its normal purpose. Option C reduces
  but does not eliminate this risk (tied to "latest run" directory rather than to a permanent
  file).
- **No hard blocker was found** that would prevent any of Options B/C from working today — no
  missing Quarto feature, no environment incompatibility, no code path that would reject an
  externally-referenced image or a minimal/empty-ish `llm_synthesis_*.json`.

## 5. Recommendation

**Recommended: Option C** (hand-authored minimal `llm_synthesis_biocirv_precision_outliers.json`
stub, using `executive_summary` as a markdown-with-embedded-images field, dropped into the
current/latest `audit/output/<timestamp>/` run directory), **not** Option B.

Rationale, given this is explicitly an MVP/one-off exploratory assessment (per the handoff's
repeated "MVP" framing) rather than a permanent dashboard feature:

- It achieves the same visual outcome as Option B (one page, images embedded, linked from the
  sidebar) for essentially the same effort (~1–2 hrs, dominated by writing/trimming the
  `executive_summary` text — the existing [`STEP4_5_FINDINGS.md`](outputs/STEP4_5_FINDINGS.md) can
  be reused almost verbatim).
- Unlike Option B, it flows through **entirely unmodified** `generate_portal.py` code
  (§2), so it does not require touching `_quarto.yml`, `index.qmd`, or any `targets/*.qmd` by
  hand — satisfying this task's "do not modify" guardrails as a *pattern* for whoever implements
  it next, and avoiding Option B's guaranteed sidebar-drop on the very next routine
  `generate-portal` run.
- It correctly reflects that this pipeline "has no relationship at all" to `REGISTRY` (per the
  task's own framing) while still using the portal's real page-per-target mental model, rather
  than inventing a parallel, undocumented, hand-maintained page that the rest of the team won't
  expect to find or maintain the same way.
- Its one weakness — needing the stub JSON physically present in whatever directory is "latest" —
  is a **lower-frequency, lower-severity** version of Option B's problem (it breaks only when a
  *new* audit run directory appears without the stub copied forward, not on every
  `generate-portal` invocation), and is easy to re-apply (copy one small JSON file) when it does
  happen.

**Total effort estimate for the full ask (heatmap now + Step 6 plots later):**
- Heatmap only, today: **~1 hour** (write the stub JSON with one embedded `![]()` line, run
  `pixi run -e portal generate-portal`, verify via `pixi run -e portal serve-portal`).
- Once Step 6's 5–10 diagnostic PNGs exist: **+30–60 minutes** to extend the same stub JSON's
  `executive_summary` with additional `![]()` lines/captions and re-run `generate-portal`.
- **Total: ~1.5–2 hours of hands-on effort**, none of it requiring changes to
  `generate_portal.py`, `_quarto.yml`, `index.qmd`, or existing `targets/*.qmd` files.

If this integration is ever promoted from MVP to a permanent, recurring feature of the Data
Quality Portal (e.g., outlier/precision review becomes a standing part of the audit cycle rather
than a one-off), Option D (a small additive glob/special-case change to `generate_portal.py`
itself) becomes the more maintainable long-term choice, since it would stop depending on the
"latest run directory" fragility altogether.

## 6. Sequencing: do this before or after Step 6?

**Recommendation: after Step 6, in a single pass.** Doing the portal integration now for the lone
heatmap and then again once Step 6's 5–10 diagnostic plots land is not a hard blocker either way
(Option C's mechanism is identical either time — you're only ever editing/appending `![]()` lines
inside one `executive_summary` string), but it is genuinely redundant work: the stub JSON, the
`generate-portal` run, and the `serve-portal` visual check would all be repeated a second time for
what is otherwise the same page. Since Step 6 is already scoped and next in the handoff's
sequence, and the whole point of Option C is "cheap to author," the efficient order is:

1. Finish Step 6 (`outputs/plots_selected/*.png` populated, per
   [`STEP4_5_FINDINGS.md` §4](outputs/STEP4_5_FINDINGS.md)'s 8 selected combinations).
2. Do the portal integration exactly once, embedding the heatmap **and** all Step 6 plots together
   in one `executive_summary` markdown block.

This also produces a materially better page: a heatmap-only page today would need restructuring
(headings, ordering, narrative flow) once 8 more images are added later anyway, so waiting avoids
that rework too, not just the JSON-editing rework.

### Making Step 6's plots "dashboard-ready" now, without doing the dashboard now

The two pieces of work are cleanly separable: **Step 6's job is only to produce well-named,
well-captioned image files in a predictable location; the portal integration's job is only to
turn a list of `(path, caption)` pairs into markdown.** If Step 6 is written with the following
conventions, the eventual Option C authoring step becomes almost mechanical (or fully scriptable)
rather than manual prose-writing:

- **Fixed, predictable output directory** — already true: `outputs/plots_selected/` is scaffolded
  and referenced by the handoff ([handoff §"Step 6"](../biocirv_outlier_assessment_handoff_v4.md:469)).
  Keep all Step 6 images there (no ad hoc subfolders) so a later integration step can glob one
  directory instead of hunting for files.
- **Self-describing filenames**, e.g. `icp_al_mean_vs_rsd.png`,
  `xrf_ba_mean_vs_rsd.png`, `proximate_total_solids_mean_vs_rsd.png` — encode
  `<analysis_type>_<parameter>_<plot-kind>` directly in the filename. This lets a caption be
  derived from the filename alone later (`icp / al — mean vs. RSD%`), rather than requiring the
  integrator to cross-reference `STEP4_5_FINDINGS.md` §4's table by hand for every image.
- **Emit a small manifest alongside the images** — e.g. `outputs/plots_selected/manifest.csv` (or
  `.json`) with one row per plot: `filename, analysis_type, parameter, reason` (the `reason` column
  can be copied straight from the §4 table Step 6 is already implementing:
  [`STEP4_5_FINDINGS.md`](outputs/STEP4_5_FINDINGS.md:180)). This single artifact is what a future
  "build the stub JSON" step would read to auto-generate every `![]()` line + one-line caption —
  turning the portal-integration step from "write markdown by hand" into "run a 15-line script
  that reads `manifest.csv` and writes `llm_synthesis_biocirv_precision_outliers.json`." This is
  the single highest-leverage thing Step 6 can do to make the later dashboard step close to free.
- **Consistent image sizing/DPI** across all Step 6 plots (matching whatever
  `05_build_review_heatmap.py` already uses for the heatmap) so the portal page doesn't show
  wildly differently-scaled images side by side.
- **Self-contained captions** — since the portal page will show these images with only a short
  caption and no surrounding interactive context (unlike a notebook), keep each plot's title/axis
  labels fully spelled out (units, `analysis_type`/`parameter` name) rather than relying on
  external context to interpret it.

None of this requires deciding anything about the portal now — it only requires Step 6 to write
its outputs in a way that is trivially indexable later, so the actual portal-integration work
(§3 Option C) stays at its estimated ~1–1.5 hours **total**, done once, after Step 6 is complete.
