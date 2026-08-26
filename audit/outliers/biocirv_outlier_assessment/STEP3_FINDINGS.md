# Step 3 Findings — Candidate Replicate-Level Flags

Script: [`03_add_candidate_flags.py`](03_add_candidate_flags.py)
Output: [`outputs/replicate_group_summary.csv`](outputs/replicate_group_summary.csv)
(enriched **in place** — same file as Step 1, still 2712 rows)

## What this step adds

Three exploratory, non-production candidate flag/status sets, added as new
columns on the existing Step 1 replicate-group table:

1. `rsd_gt_{threshold}` for each threshold in
   `analysis_config.RSD_BENCHMARK_THRESHOLDS` (currently `[10, 20]`) —
   comparison benchmarks only, not proposed BioCirV thresholds.
2. `dixon_q_statistic`, `dixon_candidate_record_id`, `dixon_flag_0_05`,
   `dixon_status` — classical Dixon's Q test (r10 statistic), single-pass,
   flag-only (never removes/reruns).
3. `rout_status`, `rout_status_reason` — placeholder only; ROUT was not
   implemented from scratch per handoff guardrail.

## RSD sensitivity flags

- RSD undefined (`RSD_percent` is NaN): **757 groups (27.9%)**
- `rsd_gt_10 == True`: **400 groups** (14.7% of all 2712 groups; 20.5% of
  the 1955 RSD-defined groups)
- `rsd_gt_20 == True`: **171 groups** (6.3% of all groups; 8.7% of
  RSD-defined groups)

## Dixon Q test

Critical-value table source: Rorabacher, D. B. (1991), *Analytical
Chemistry* 63(2), 139-146 — standard extended two-tailed alpha=0.05 Dixon's
Q critical values, n = 3 to 30.

`dixon_status` breakdown (2712 total groups):

| dixon_status | count | % |
| --- | --- | --- |
| `calculated` | 1447 | 53.4% |
| `not_applicable_n_out_of_range` (n<3 or n>30) | 1238 | 45.6% |
| `not_applicable_zero_range` (all values identical) | 27 | 1.0% |
| `skipped_data_mismatch` | 0 | 0.0% |

- `dixon_flag_0_05 == True`: **246 of 1447 calculated groups (17.0%)**
- No `values`/`source_record_ids` length mismatches were encountered in the
  full dataset (0 groups skipped for this reason).

### Spot-check (manually verified)

`replicate_group_id=8`, sample 148, compositional/xylan, n=3,
`values = [15.17, 17.03, 17.04]`:

- sorted: `[15.17, 17.03, 17.04]`
- `range_val = 17.04 - 15.17 = 1.87`
- `Q_low = (17.03-15.17)/1.87 = 0.99465`; `Q_high = (17.04-17.03)/1.87 = 0.00535`
- `dixon_q_statistic = max = 0.99465`; candidate record = `(04)68e4` (the
  low extreme, since `Q_low >= Q_high`)
- critical value for n=3 (alpha=0.05) = `0.970`
- `0.99465 > 0.970` → `dixon_flag_0_05 = True` ✓

For an n=2 group (`replicate_group_id=56`), `dixon_status` correctly reads
`not_applicable_n_out_of_range`, with `dixon_q_statistic`/
`dixon_candidate_record_id`/`dixon_flag_0_05` all null.

## RSD (>20%) × Dixon (0.05) overlap — 2×2 cross-tab

Preview of the "candidate rule comparison" work planned for a later step;
useful now as a sanity check that the two methods are not simply redundant.

| | Dixon flagged | Dixon not flagged | Row total |
| --- | --- | --- | --- |
| **RSD>20 flagged** | 19 | 152 | 171 |
| **RSD>20 not flagged** | 227 | 2314 | 2541 |
| **Column total** | 246 | 2466 | 2712 |

Only 19 groups are flagged by both methods; each method independently
flags a substantial, largely non-overlapping set of additional groups
(152 RSD-only, 227 Dixon-only). This indicates the two candidate rules are
sensitive to different failure patterns (RSD>20 flags overall spread
regardless of shape; Dixon flags a single extreme value relative to the
group's range) and should be compared side by side in later review rather
than treated as interchangeable.

## ROUT placeholder

`rout_status == "not_calculated"` confirmed for all **2712/2712** rows.
`rout_status_reason` is populated from `analysis_config.ROUT_STATUS_REASON`
on every row.

## Guardrails honored

- Dixon is a flag only — no `values`/rows were modified or excluded based
  on the Dixon result.
- Single-pass Dixon calculation; no sequential remove-and-rerun.
- ROUT not implemented from scratch; explicit status/reason recorded
  instead of a silent omission.
- Every "not calculated" case (`n_out_of_range`, `zero_range`,
  `data_mismatch`) has an explicit `dixon_status` value rather than a bare
  NaN with no explanation.
