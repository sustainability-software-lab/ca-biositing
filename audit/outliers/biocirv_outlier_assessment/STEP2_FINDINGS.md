# Step 2 Findings — Sample-Level Summary

Script: [`02_build_sample_level_summary.py`](02_build_sample_level_summary.py)
Output: [`outputs/sample_level_summary.csv`](outputs/sample_level_summary.csv)

## What this table is

One row per `sample_id × analysis_type × parameter × unit × method`
combination — one level up from `replicate_group_summary.csv` (Step 1),
which is keyed one level further down by also including `experiment_id`.
This collapses across `experiment_id` when a sample was analyzed in more
than one experimental run.

Two distinct variability statistics are reported side by side and must not
be confused:

- `pooled_SD` / `pooled_RSD_percent` — computed from ALL raw replicate
  values pooled together across every contributing experiment. Mixes
  within-experiment technical-replicate variation with between-experiment
  variation ("total variability" for the sample).
- `between_experiment_SD` / `between_experiment_RSD_percent` — computed
  only from the spread of the per-experiment group means (one value per
  contributing experiment, pulled from Step 1's `mean` column). Isolates
  inter-experiment agreement/disagreement and is only defined when
  `n_contributing_experiments > 1`.

## Key results

- **Total sample-level rows: 2561**
- **Rows spanning >1 experiment (`n_contributing_experiments > 1`): 151**
  (matches Step 0's confirmed count of 151 combinations that spanned more
  than one `experiment_id`)
- **Singleton pass-through rows (`n_contributing_experiments == 1`): 2410**
  — these rows' `pooled_SD`/`pooled_RSD_percent` are numerically identical
  to their single underlying Step 1 group's `standard_deviation`/
  `RSD_percent`, and `between_experiment_SD`/`between_experiment_RSD_percent`
  are NaN (undefined with only one contributing experiment, as expected).

### Row counts by `analysis_type`

| analysis_type | n_rows |
| --- | --- |
| xrf | 1315 |
| proximate | 424 |
| icp | 410 |
| compositional | 345 |
| ultimate | 57 |
| xrd | 10 |
| **TOTAL** | **2561** |

(These are the WITHOUT-`experiment_id` group counts from Step 0's
comparison table — expected, since Step 2 deliberately collapses back
across `experiment_id`.)

### `pooled_RSD_percent`

- Undefined (NaN): 663 rows (25.9%) — undefined when `n_replicates == 1`
  across all contributing experiments, or when `sample_mean` is
  (near-)zero, per the same `RSD_MEAN_EPSILON = 1e-9` convention used in
  Step 1.
- Median (where defined): **3.38%**
- Median by `analysis_type`:

  | analysis_type | median pooled_RSD_percent |
  | --- | --- |
  | ultimate | 0.00 |
  | xrd | 1.49 |
  | compositional | 1.68 |
  | proximate | 1.74 |
  | xrf | 5.40 |
  | icp | 6.72 |

  `icp` and `xrf` show visibly higher typical pooled RSD than the other
  characterization analyses — a candidate signal for later per-`analysis_type
  × parameter` review (Step 4+), not a conclusion in itself.

### `between_experiment_RSD_percent`

- Defined for exactly 151 rows (matches `n_contributing_experiments > 1`
  count above — by construction, undefined whenever only one experiment
  contributed).
- Median (where defined): **15.21%** — notably higher than the pooled-RSD
  median (3.38%), consistent with the expectation that inter-experiment
  disagreement is a materially different (and generally larger) source of
  variation than within-experiment technical-replicate spread. This is an
  observation for human review, not an automated conclusion (per handoff's
  "Core Statistical Principle" — Level 1 vs Level 2 variation must be kept
  separate).

## Reconciliation checks (from script's own validation output)

- `sum(n_replicates)` across all sample-level rows reconciles exactly
  against total raw rows (minus any excluded null-`sample_id` rows) — no
  double-counting or dropped rows.
- No metadata (`resource_id`/`resource_type`/`lab`/`protocol_version`)
  consistency warnings were unexpectedly high; any triggered warnings are
  logged by the script at runtime.

## Scope note

No filtering, flagging, or outlier logic is applied at this step — Step 2
is purely a re-aggregation of Step 1's data to the sample level. Candidate
flags (RSD benchmarks, Dixon Q, ROUT placeholder) are added to
`replicate_group_summary.csv` in Step 3, not here.
