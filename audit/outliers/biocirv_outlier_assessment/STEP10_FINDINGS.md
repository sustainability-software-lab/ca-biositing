# Step 10 Findings — Human-Review Priority Queue

Produced by [`10_build_review_priorities.py`](10_build_review_priorities.py),
reading `outputs/flagged_review_queue.csv` (427 rows), `outputs/replicate_group_summary.csv`
(2712 rows, all replicate groups, used for denominators and `source_record_ids`
traceability), `outputs/review_queue_by_analysis_parameter.csv`,
`outputs/review_queue_by_dimension_summary.csv`, and `outputs/investigation_packets.csv`
(114 rows) — all produced by Steps 1–9 and **not modified by this step**.

**Terminology note:** `flagged_review_queue.csv` (and this document) use the
Step-9-corrected human-readable names **provider** and
**sample preparation method** throughout (these columns are present verbatim
in `flagged_review_queue.csv`; the legacy `lab`/`method` names were not
found there). See [`STEP9_FINDINGS.md`](STEP9_FINDINGS.md) for the full
terminology-correction background.

**Throughout this document: a statistical flag is NOT a determination that
the underlying data is invalid, bad, or should be excluded.** This step
identifies where human review attention would be most efficiently spent
given the existing 427-group backlog from Step 9 — it does not filter,
delete, exclude, or invalidate any observation. Every replicate group
discussed below remains fully present, unaltered, in
`replicate_group_summary.csv`.

---

## 1. Input verification (performed before building on Step 9's outputs)

| Input file | Check | Result |
|---|---|---|
| `flagged_review_queue.csv` | Row count == 427 | **PASS** (427 rows) |
| `flagged_review_queue.csv` | Column naming | `provider` / `sample_preparation_method` present (Step-9-corrected names); legacy `lab` / `method` **not** present in this file |
| `review_queue_by_analysis_parameter.csv` | Loads without error | **PASS** (50 rows; columns: `analysis_type`, `parameter`, `n_flagged_groups`, `percent_of_total_flags`, `n_replicate_groups`, `flag_rate_percent`) |
| `review_queue_by_dimension_summary.csv` | Loads without error | **PASS** (116 rows; columns: `dimension`, `value`, `n_flagged_groups`, `percent_of_total_flags`, `n_replicate_groups_total`, `flag_rate_percent`) |
| `investigation_packets.csv` | Row count == 114 | **PASS** |
| `investigation_packets.csv` | `sum(n_flagged_groups_in_packet) == 427` | **PASS** |
| `replicate_group_summary.csv` | Row count == 2712 | **PASS** |

All input-verification checks passed — no inconsistency was found in the
Step 9 outputs this step depends on. `replicate_group_summary.csv` itself
retains the original upstream `lab`/`method` column headers (unchanged, as
documented in Step 9); `flagged_review_queue.csv` exposes the corrected
`provider`/`sample_preparation_method` names, which this document uses
consistently.

---

## 2. Review-target grain

Per the task scope, review targets below are built primarily at two grains:

- **`experiment_id`** (2 of the 7 selected priorities)
- **`analysis_type × parameter`** (5 of the 7 selected priorities)

`provider`, `resource_type`, `sample_preparation_method`, `flag_category`,
and `existing_QC_status` are used only as **supporting context** in the "why
review" text for each target below — none of these dimensions was promoted
to a standalone top-level target, because in every case examined
(`provider = rigging`, mixed `existing_QC_status` groups) the groups
involved were either too few (11 of 427 for mixed QC status) or almost
entirely already contained within an already-selected `experiment_id`
target (`rigging`: 41 of its 55 flagged groups fall inside
`experiment_id = 47`) to justify a separate, non-redundant top-level row.

As in Step 9, **`experiment_id` is retained here only as a convenient
review-grouping key** — this analysis does not establish that it
corresponds to a validated day/run/batch or a common-root-cause unit.

---

## 3. Human-review priority table

**Cumulative coverage note:** the "Cumulative % of 427 flagged groups
addressed" column is a true set-union calculation (see §4), not a naive sum
of "Flagged groups in target" — several of the `analysis_type × parameter`
targets below have **zero** overlap with each other and with the two
`experiment_id` targets by construction, but this was verified explicitly
in code rather than assumed.

| Priority | Review target | Grain | Flagged groups in target | Flag rate | Enrichment vs baseline | Cumulative % of 427 flagged groups addressed | Why review / suggested focus |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | experiment_id = 47 | experiment_id | 254 | 27.5% | 1.74x | 59.5% | Largest single target (59.5% of all flags), most elevated large-denominator flag rate in the dataset. Almost entirely `xrf` trace-element parameters (see §5 sub-focus list). Dixon_only-dominant flag-category mix. Provider `rigging` contributes 41/254 groups (context only). |
| 2 | experiment_id = 43 | experiment_id | 61 | 18.2% | 1.15x | 73.8% | Second-largest experiment target, entirely `icp` trace-element parameters (see §5). RSD_only-dominant flag-category mix (53/61 = 87%) — a distinct signature from experiment 47's Dixon-dominant pattern. Includes 3 mixed-status (`fail,pass`) `icp/na` groups (context only). |
| 3 | proximate x ash | analysis_type x parameter | 21 | 18.3% | 1.16x | 78.7% | Largest `proximate` parameter target, zero overlap with experiment 47/43 (spread across many small experiments). Dixon_only-dominant (14/21). Includes 1 `fail` and 2 mixed-status groups — useful cross-check candidates. |
| 4 | proximate x volatile solids | analysis_type x parameter | 14 | 12.2% | 0.77x | 82.0% | Second `proximate` target, shares the mass-balance parameter family with `ash`; below-baseline rate but included for absolute count and family relationship. |
| 5 | compositional x xylan | analysis_type x parameter | 13 | 19.1% | 1.21x | 85.0% | Largest `compositional` parameter target, spread across 9 distinct experiment_ids (27, 30, 31, 32, 35, 36, 37, 38, 40) — a genuinely different concentration pattern than the two experiment-level targets. |
| 6 | proximate x total solids | analysis_type x parameter | 13 | 11.3% | 0.72x | 88.1% | Third `proximate` target, same mass-balance family as `ash`/`volatile solids`; below-baseline rate, included for absolute count. |
| 7 | compositional x xylose | analysis_type x parameter | 11 | 16.7% | 1.06x | 90.6% | Second `compositional` target, often measured alongside `xylan` in the same batch; grouped adjacently for reviewer convenience though it is a separate top-level target. |

**Final cumulative unique coverage: 90.6%** of the 427 flagged groups (387 of
427 distinct `replicate_group_id`s) are addressed by these 7 priorities.

Full `replicate_group_id` and `source_record_ids` lists for every priority
are in `outputs/human_review_priorities.csv` (not reproduced in this table
to keep it readable).

---

## 4. How cumulative coverage was calculated

Each priority target (e.g. "experiment_id = 47", "proximate x ash") is
first materialized as an explicit Python `set` of `replicate_group_id`
values drawn from the 427-row `flagged_review_queue.csv`. Starting from an
empty running set, each successive priority's group-id set is combined into
the running set with a **set union** (`running_set = running_set |
target_set`), and the reported "Cumulative % of 427 flagged groups
addressed" is `len(running_set) / 427 * 100` at that point. Because set
union automatically de-duplicates, any replicate group that happens to
belong to more than one selected target (for example, a group could in
principle belong to both an `experiment_id` target and an
`analysis_type × parameter` target) is only counted once toward the
cumulative percentage, rather than being double-counted by a naive running
sum of "flagged groups in target." In this particular selection, the five
`analysis_type × parameter` targets turned out to have zero overlap with the
two `experiment_id` targets and with each other (verified in code, not
assumed) — but the union-based calculation would have handled overlap
correctly regardless.

---

## 5. Sub-focus notes for the largest experiment-level reviews

### Experiment 47 (254 flagged groups) — flags concentrated in `xrf` trace elements:

- `xrf/rb` — 30 groups
- `xrf/cu` — 26 groups
- `xrf/sr` — 24 groups
- `xrf/u` — 23 groups
- `xrf/k` — 15 groups
- `xrf/mn` — 14 groups
- `xrf/zn` — 14 groups
- `xrf/mo` — 12 groups
- `xrf/ba` — 12 groups
- `xrf/ca` — 11 groups

These 10 `xrf` parameters alone account for 181 of experiment 47's 254
flagged groups (71%). Each of these parameters' flagged groups is **100%
contained within** experiment 47 (verified in code) — consistent with
STEP9_FINDINGS.md's identification of `xrf` trace-element parameters as the
top individual contributors to the overall 427-group backlog. They are
listed here as sub-focuses of the experiment_id = 47 priority rather than as
separate top-level rows, per the task's redundancy-avoidance guidance.

### Experiment 43 (61 flagged groups) — flags concentrated in `icp` trace elements:

- `icp/p` — 8 groups
- `icp/al` — 7 groups
- `icp/na` — 7 groups
- `icp/ti` — 6 groups
- `icp/cu` — 6 groups
- `icp/fe` — 5 groups
- `icp/si` — 5 groups
- `icp/nd` — 5 groups
- `icp/s` — 4 groups
- `icp/zn` — 3 groups

All 61 of experiment 43's flagged groups are `icp` parameters (no other
analysis type appears in this experiment's flagged rows), and its
flag-category mix (87% `RSD_only`) is notably different from experiment 47's
Dixon-dominant pattern — a potentially useful distinction for a reviewer
prioritizing by likely flag mechanism.

---

## 6. Reminder

**A statistical flag is not a determination that the underlying observation
is wrong, invalid, or should be excluded.** This priority list identifies
where human review attention would be most efficiently spent across the
existing 427-group backlog — it is a working triage aid, not a data-quality
verdict on any individual replicate group, experiment, parameter, provider,
or sample preparation method named above.
