# Step 9 Findings — Review-Queue / Workload Analysis

Produced by [`09_build_review_queue.py`](09_build_review_queue.py) and
[`09b_analyze_backlog_concentration.py`](09b_analyze_backlog_concentration.py),
reading `outputs/replicate_group_summary.csv` (2712 rows), `outputs/replicate_group_3xSD_flags.csv`
(2712 rows), `outputs/candidate_rule_overlap_summary.csv`, and
`outputs/candidate_rule_comparison.csv` — all produced by Steps 1–8 and
**not modified by this step**.

**Throughout this document: a statistical flag is NOT a determination that
the underlying data is invalid, bad, or should be excluded.** This step
measures review burden and organizes investigation only. It does not
filter, delete, exclude, or invalidate any observation. Every replicate
group discussed below remains fully present, unaltered, in
`replicate_group_summary.csv`.

---

## 1. Raw review backlog

Across all 2712 replicate groups, **427 (15.7%)** were flagged by at least
one of the three candidate screens (RSD > 20%, Dixon's Q at α = 0.05, or
the exploratory pooled 3×SD check) — this figure is reused as-is from
`candidate_rule_overlap_summary.csv`'s `flagged_by_any` row, not
recomputed. `outputs/flagged_review_queue.csv` contains exactly these 427
replicate groups, one row each, with a `flag_category` column.

`flag_category` breakdown (validated to match
`candidate_rule_overlap_summary.csv` exactly, see §6 below):

| flag_category | Count | % of 427 |
|---|---:|---:|
| Dixon_only | 224 | 52.5% |
| RSD_only | 140 | 32.8% |
| 3xSD_only | 23 | 5.4% |
| RSD_and_3xSD | 18 | 4.2% |
| RSD_and_Dixon | 12 | 2.8% |
| all_three | 7 | 1.6% |
| Dixon_and_3xSD | 3 | 0.7% |
| **Total** | **427** | **100%** |

Dixon-only flags are the largest single category (52.5% of the queue),
consistent with Step 8's finding that Dixon most often fires on isolated
extreme values that RSD and the pooled 3×SD check do not also catch.

---

## 2. Where flags are concentrated

### Top analysis_type × parameter contributors

From `outputs/review_queue_by_analysis_parameter.csv` (one row per
`analysis_type × parameter` present in the queue, with both raw counts and
flag rates against the total replicate-group count for that combination,
per the guardrail against reporting counts without denominators):

| analysis_type | parameter | n_flagged_groups | % of 427 | n_replicate_groups | flag_rate_percent |
|---|---|---:|---:|---:|---:|
| xrf | rb | 30 | 7.0% | 52 | 57.7% |
| xrf | cu | 26 | 6.1% | 55 | 47.3% |
| xrf | sr | 24 | 5.6% | 54 | 44.4% |
| xrf | u | 23 | 5.4% | 55 | 41.8% |
| proximate | ash | 21 | 4.9% | 115 | 18.3% |
| xrf | k | 15 | 3.5% | 55 | 27.3% |
| proximate | volatile solids | 14 | 3.3% | 115 | 12.2% |
| xrf | mn | 14 | 3.3% | 55 | 25.5% |
| xrf | zn | 14 | 3.3% | 55 | 25.5% |
| proximate | total solids | 13 | 3.0% | 115 | 11.3% |

**Top-5 combinations account for 29.0% of all 427 flags.**
**Top-10 combinations account for 45.4% of all 427 flags.**

The top contributors are dominated by `xrf` trace-element parameters
(rb, cu, sr, u, k, mn, zn) with very high flag *rates* (42–58% of their own
replicate groups flagged) alongside high absolute counts — these are small
denominators (52–55 groups each) with unusually concentrated flagging, not
just large categories generating proportionally few flags.

### By analysis_type

| analysis_type | n_flagged_groups | % of 427 | n_replicate_groups (all) | flag_rate_percent |
|---|---:|---:|---:|---:|
| xrf | 254 | 59.5% | 1315 | 19.3% |
| icp | 62 | 14.5% | 518 | 12.0% |
| proximate | 59 | 13.8% | 460 | 12.8% |
| compositional | 52 | 12.2% | 352 | 14.8% |

`xrf` contributes the majority of raw flags (59.5%) but its flag *rate*
(19.3%) is not dramatically higher than the other three analysis types
(12.0–14.8%) — `xrf`'s dominance in raw counts is driven substantially by
it having the largest population (1315 of 2712 groups), not by a uniquely
higher per-group flag propensity.

### Clustering by experiment_id, resource_id, lab, method, protocol_version

(counts AND rates, `dropna=False` throughout; full detail in
`outputs/review_queue_by_dimension_summary.csv`)

- **experiment_id**: 35 of 48 distinct experiment_ids appear in the
  flagged queue. **A single experiment_id (`47.0`) accounts for 59.5% of
  all 427 flags** (254 flags out of that experiment's own 925 replicate
  groups — a 27.5% flag rate for that experiment, similar to the overall
  15.7% baseline but on a much larger base). Only 1 experiment_id is
  needed to reach ≥50% of all flags. `experiment_id=43.0` is the second
  largest, contributing another 14.3% (61 of 336 groups, 18.2% rate).
- **resource_id**: 35 of 42 distinct resource_ids appear in the flagged
  queue; 7 resource_ids account for ≥50% of the 427 flags. The single
  largest (`resource_id=25`) contributes 50 flags out of 311 replicate
  groups for that resource (16.1% rate) — near the dataset-wide 15.7%
  baseline, i.e. not an outlier rate despite being the top raw contributor.
- **lab**: 28 of 31 distinct labs appear in the flagged queue; 6 labs
  account for ≥50% of flags. The single largest (`rigging`) contributes 55
  flags out of 178 groups (30.9% rate) — meaningfully above the 15.7%
  baseline, but still a minority of that lab's total groups.
- **method**: 8 of 10 distinct methods appear in the flagged queue; only 2
  methods (`knife mill (2mm)` and `oven dry + knife mill (2mm)`) account
  for ≥50% of flags (197 and 144 flags respectively). `knife mill (2mm)`'s
  own flag rate (20.7% of its 952 groups) is close to baseline;
  `oven dry + knife mill (2mm)` is somewhat higher (24.4% of 590 groups).
- **protocol_version**: 100% null across the entire 2712-row dataset (not
  just the flagged queue), so this dimension provides no discriminating
  information in the current data — every replicate group, flagged or not,
  has a missing `protocol_version`.

**Interpretation (descriptive, not causal):** raw flag counts are heavily
concentrated in a small number of experiments, resources, and labs simply
because those experiments/resources/labs contain many more replicate
groups overall — the corresponding flag *rates* are, in most cases, close
to the 15.7% dataset-wide baseline. The `rigging` lab and `unused oak stick`
resource type (53.6% flag rate, footnote: only 28 total groups, a small
denominator) are the two dimension-values whose rates are most elevated
relative to baseline. Per the guardrail, none of this is interpreted as
"this lab/method/resource is problematic" — only that review workload is
unevenly distributed and elevated rates on small denominators warrant
cautious interpretation.

### existing_QC_status overlap with statistical flags (descriptive only, no causal claim)

| existing_QC_status | n_flagged_groups | % of 427 | n_replicate_groups_total | flag_rate_percent |
|---|---:|---:|---:|---:|
| pass | 390 | 91.3% | 1994 | 19.6% |
| (missing) | 14 | 3.3% | 83 | 16.9% |
| fail | 12 | 2.8% | 233 | 5.2% |
| fail,pass | 7 | 1.6% | 8 | 87.5% |
| pass,provisional | 4 | 0.9% | 4 | 100.0% |

The large majority of flagged groups (91.3%) already carry an
`existing_QC_status` of `pass` — expected, since `pass` is the dominant
status across the whole dataset (1994 of 2712 groups, 73.5%). Groups
already marked `fail` are actually flagged at a *lower* rate (5.2%) than
the dataset average (15.7%), while compound statuses (`fail,pass`,
`pass,provisional` — likely reflecting multiple source records per group
with disagreeing analyst calls) show much higher flag rates (87.5% and
100%, respectively) but on extremely small denominators (8 and 4 groups).
This is reported purely descriptively: it does **not** establish that
statistical flags validate or contradict prior analyst QC calls, only that
their overlap is uneven and worth noting for anyone designing a combined
review workflow.

---

## 3. Consolidation into investigation packets

### Chosen grouping key

`analysis_type + parameter + experiment_id`, evaluated with
`dropna=False` so that groups with a null `experiment_id` form their own
explicit packet(s) rather than being silently dropped.

**Documented limitation:** `experiment_id` is used here as a convenience
batching key. **The data does not establish that `experiment_id`
corresponds to a specific day/run/batch in a way that guarantees an
analyst can investigate all flagged groups within one experiment as a
single coherent root-cause investigation** — this is a provisional MVP
simplification, not a validated investigation unit.

### Grouping-key comparison (Part C.2)

| grouping_key | n_packets | median_group_size | max_group_size | n_singleton_packets | % singleton |
|---|---:|---:|---:|---:|---:|
| base (analysis_type+parameter+experiment_id) | 114 | 2.0 | 30 | 53 | 46.5% |
| +resource_id | 340 | 1.0 | 5 | 273 | 80.3% |
| +lab | 297 | 1.0 | 6 | 211 | 71.0% |
| +method | 144 | 2.0 | 18 | 69 | 47.9% |
| +protocol_version | 114 | 2.0 | 30 | 53 | 46.5% |
| +resource_id+lab+method+protocol_version (all) | 379 | 1.0 | 4 | 338 | 89.2% |

Adding `resource_id` or `lab` to the base key sharply increases packet
count toward the raw 427-group count (i.e., most added splits produce
singleton packets), defeating the purpose of consolidation. Adding
`protocol_version` changes nothing (it is 100% null dataset-wide, so it
never actually splits any group). `+method` produces a modest increase
(114 → 144 packets). The base key was retained for this MVP because it
provides the most consolidation while remaining a plausible — if unproven
— review-batching unit.

### Packet build and validation

`outputs/investigation_packets.csv` has **114 rows** (packets). Validation
performed by the script, all passing:

- `sum(n_flagged_groups_in_packet) == 427`: **PASS**
- No `replicate_group_id` appears in more than one packet: **PASS**
- Every one of the 427 flagged replicate groups appears in exactly one
  packet: **PASS**

### Packet statistics

- Total raw flagged groups: 427 (confirmed)
- Number of resulting packets: **114**
- Median flagged-groups-per-packet: **2.0**
- Max flagged-groups-in-one-packet: **30**
- Packets containing >1 flagged group: **61 (53.5% of 114 packets)**

Largest packets (for sanity-checking):

| packet_id | analysis_type | parameter | experiment_id | n_flagged_groups_in_packet |
|---|---|---|---|---:|
| xrf\|rb\|47 | xrf | rb | 47.0 | 30 |
| xrf\|cu\|47 | xrf | cu | 47.0 | 26 |
| xrf\|sr\|47 | xrf | sr | 47.0 | 24 |

All three largest packets share `experiment_id=47.0`, consistent with §2's
finding that this single experiment accounts for the majority of raw
flags.

---

## 4. Estimated analyst workload

**These are PLANNING SCENARIOS ONLY, not measured analyst-time
estimates.** No actual review-time data was collected; the numbers below
are simple minutes-per-review × unit-count arithmetic for planning
purposes only.

| Scenario | Minutes/review | Total minutes (427 raw groups) | Total hours (427 raw groups) | Total minutes (114 packets) | Total hours (114 packets) |
|---|---:|---:|---:|---:|---:|
| Fast | 5 | 2135 | 35.6 | 570 | 9.5 |
| Moderate | 10 | 4270 | 71.2 | 1140 | 19.0 |
| Thorough | 15 | 6405 | 106.8 | 1710 | 28.5 |

Approximate review rate, expressed per 100 replicate groups reviewed:

| Scenario | Min per 100 raw groups | Min per 100-raw-group-equivalent via packets |
|---|---:|---:|
| Fast (5 min/review) | 500 | ~133 |
| Moderate (10 min/review) | 1000 | ~267 |
| Thorough (15 min/review) | 1500 | ~400 |

(Packet consolidation ratio: 114 / 427 = 0.267 — i.e., reviewing by packet
instead of by raw replicate group reduces the number of review units by
~73%, assuming a packet takes roughly the same time to review as a single
replicate group, which is itself an unvalidated planning assumption.)

---

## 5. Implications for designing a practical BioCirV review workflow

The following observations are **descriptive and hedged, not prescriptive
production rules**:

- Packet-based review appears to reduce the effective queue size from 427
  individual replicate groups to 114 investigation units, suggesting
  investigation-level batching **may** be more efficient than reviewing
  every flagged replicate group independently — this is a planning
  observation, not a finalized workflow design.
- A disproportionate share of the raw backlog traces back to a small
  number of experiments (notably `experiment_id=47.0`, contributing 59.5%
  of all flags) and a handful of `xrf` trace-element parameters with high
  flag rates on modest denominators. A workflow **could** prioritize
  reviewing these high-concentration packets first, though this analysis
  does not establish that doing so is optimal or that these
  concentrations reflect anything beyond how the underlying screens
  (RSD, Dixon, 3×SD) behave on this particular data structure.
- Because `experiment_id` is not validated as a true batch/run identifier
  (see §3's documented limitation), any workflow built on
  `analysis_type + parameter + experiment_id` packets should treat that
  grouping as a starting hypothesis for investigation batching, not a
  guarantee that all groups within a packet share a common root cause.
- The overlap between statistical flags and existing `existing_QC_status`
  values (§2) is uneven but not straightforwardly interpretable — a
  workflow **could** consider cross-referencing statistical flags against
  existing QC status as one input among several, but this analysis does
  not establish that the two signals should be combined in any particular
  way.
- **None of the above implies that any flagged replicate group's
  underlying data is invalid, bad, or should be excluded.** This analysis
  organizes review workload; it does not make exclusion or validity
  determinations.

---

## 6. Validation summary

- `flagged_review_queue.csv`: **427 rows**, `flag_category` breakdown
  matches `candidate_rule_overlap_summary.csv` **exactly** across all 7
  mutually-exclusive categories (RSD_only=140, Dixon_only=224,
  3xSD_only=23, RSD_and_Dixon=12, RSD_and_3xSD=18, Dixon_and_3xSD=3,
  all_three=7).
- `investigation_packets.csv`: **114 packets**,
  `sum(n_flagged_groups_in_packet) == 427` confirmed, no replicate group
  duplicated or omitted across packets.
- Every by-dimension grouping in Part B (`analysis_type`, `resource_type`,
  `experiment_id`, `lab`, `method`, `protocol_version`,
  `existing_QC_status`) and the Part C packet grouping used
  `groupby(..., dropna=False)` so that null values (e.g., 10 groups with
  null `experiment_id` in the full dataset, 518 groups with null `method`,
  42 with null `lab`, all 2712 with null `protocol_version`) form their
  own explicit `(missing)` category rather than being silently dropped.
