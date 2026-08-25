## 2026-08-27 — Re-validation: `experiment_id` added to `REPLICATE_GROUP_KEYS`

**Design decision:** `experiment_id` was added to `analysis_config.REPLICATE_GROUP_KEYS`
(now `['sample_id', 'analysis_type', 'parameter', 'unit', 'method', 'experiment_id']`,
previously `['sample_id', 'analysis_type', 'parameter', 'unit', 'method']`). This is a
natural analog to the handoff's optional `method / protocol_version`, `lab` additions:
it prevents accidentally pooling technical replicates that were actually measured in
genuinely different experimental runs. This makes `replicate_group_summary.csv` (Step 1,
built in a later task) keyed at one-group-per-experimental-run granularity, while
`sample_level_summary.csv` (Step 2) will genuinely aggregate ACROSS `experiment_id` when
a sample was analyzed in more than one experiment — a real, non-trivial distinction
between the two outputs that did not previously exist.

**`experiment_id` column confirmed present** in `raw_extract_20260825.csv` (6155 rows).
Null/missing `experiment_id`: **27 rows (0.44% of total rows)**. Per the updated config
comment, any downstream `groupby(REPLICATE_GROUP_KEYS, ...)` call (notably in the
future `01_build_replicate_summary.py`) must pass `dropna=False` so these 27 rows form
their own group rather than being silently dropped. `00_validate_replicate_grouping.py`
already used `dropna=False` in all of its `groupby()` calls prior to this change, so no
script fix was required for this re-validation pass to be correct.

**Group-count comparison (OLD key, no `experiment_id` vs NEW key, with `experiment_id`):**

| analysis_type | OLD n_groups | NEW n_groups | delta |
| --- | --- | --- | --- |
| xrf | 1315 | 1315 | +0 |
| proximate | 424 | 460 | +36 |
| compositional | 345 | 352 | +7 |
| icp | 410 | 518 | +108 |
| ultimate | 57 | 57 | +0 |
| xrd | 10 | 10 | +0 |
| **TOTAL** | **2561** | **2712** | **+151** |

- Total groups **increased from 2561 to 2712 (+151, +5.9%)**, confirming the expected
  direction (splitting by `experiment_id` can only increase or maintain group count).
- This delta of **151** `sample_id × analysis_type × parameter × unit × method`
  combinations is the population that spanned **more than one `experiment_id`** in the
  raw extract — i.e., the set of cases Step 2's `sample_level_summary.csv` will need to
  genuinely aggregate over. Without `experiment_id` in the key, these 151 combinations
  were each being treated as one pooled replicate group; now each is split into 2+
  per-experiment groups.
- `icp` shows by far the largest impact (+108 groups, ~26% increase over its old count
  of 410), followed by `proximate` (+36) and `compositional` (+7). `xrf`, `ultimate`,
  and `xrd` are unaffected (+0), meaning none of their pre-existing groups spanned more
  than one `experiment_id`.
- Singleton rate rose slightly, from **25.5% (653/2561)** under the old key to
  **27.5% (746/2712)** under the new key — expected, since splitting groups by
  `experiment_id` converts some previously-multi-row groups into singletons whenever a
  sample's replicates for a given run happened to fall into different experiments (or a
  once-larger group is split into a mix of singleton + multi-row groups).
- No other change in `method` behavior: the WITH/WITHOUT-`method` delta remains 0
  (method still does not discriminate any groups beyond what the other keys already do).

Full re-generated diagnostic output (per-`analysis_type` breakdown, sanity-check
samples, stop-condition assessment) using the new key follows below, written fresh by
`00_validate_replicate_grouping.py`.

---

## Step 0 Findings

Source raw extract: `raw_extract_20260825.csv`

Total rows: 6155

Confirmed current `analysis_config.REPLICATE_GROUP_KEYS`: `['sample_id', 'analysis_type', 'parameter', 'unit', 'method', 'experiment_id']`


### Null `sample_id`

- Rows with null/missing `sample_id`: 0 (0.0% of total rows). These rows cannot be grouped by this key at all and were excluded from all grouping analysis below.


### Grouping with current key (WITH `method`)

- Total groups: 2712

- Singleton groups (n=1): 746 (27.5% of groups)

- Groups with n>=2 (usable for SD): 1966 (72.5% of groups)


### Grouping WITHOUT `method` (comparison)

- Total groups: 2712

- Singleton groups (n=1): 746 (27.5% of groups)

- Delta in group count (WITH - WITHOUT method): 0

- Rows with null/missing `method`: 890 (14.5% of groupable rows)

- Of 2712 WITHOUT-method groups, 0 (0.0%) contain >1 distinct `method` value, i.e. would be split further by adding `method` to the key.


### Per-`analysis_type` breakdown (current config key)



| analysis_type | n_rows | n_groups | n_singleton_groups | singleton_rate_pct | n_multi_groups |
| --- | --- | --- | --- | --- | --- |
| xrf | 2778 | 1315 | 536 | 40.8 | 779 |
| proximate | 1338 | 460 | 21 | 4.6 | 439 |
| compositional | 1044 | 352 | 2 | 0.6 | 350 |
| icp | 890 | 518 | 146 | 28.2 | 372 |
| ultimate | 78 | 57 | 40 | 70.2 | 17 |
| xrd | 27 | 10 | 1 | 10.0 | 9 |



### Sanity check: multi-row group `technical_replicate_no` samples

- Sample group 1 `{'sample_id': '65', 'analysis_type': 'compositional', 'parameter': 'glucan', 'unit': '% dry weight', 'method': 'oven dry + knife mill (2mm)', 'experiment_id': '40'}`: n=2, technical_replicate_no=['1', '2'], values=[11.82, 11.89] — looks OK (distinct replicate numbers)

- Sample group 2 `{'sample_id': '117', 'analysis_type': 'xrf', 'parameter': 'mo', 'unit': 'ppm', 'method': 'oven dry + knife mill (2mm)', 'experiment_id': '47'}`: n=3, technical_replicate_no=['2', '1', '3'], values=[4.0, 7.0, 5.0] — looks OK (distinct replicate numbers)

- Sample group 3 `{'sample_id': '85', 'analysis_type': 'xrf', 'parameter': 'sr', 'unit': 'ppm', 'method': 'oven dry + knife mill (2mm)', 'experiment_id': '47'}`: n=3, technical_replicate_no=['2', '3', '1'], values=[39.0, 40.0, 41.0] — looks OK (distinct replicate numbers)

- Sample group 4 `{'sample_id': '157', 'analysis_type': 'xrf', 'parameter': 'p', 'unit': 'ppm', 'method': 'knife mill (2mm)', 'experiment_id': '47'}`: n=3, technical_replicate_no=['1', '3', '2'], values=[1320.0, 1340.0, 1290.0] — looks OK (distinct replicate numbers)

- Sample group 5 `{'sample_id': '22', 'analysis_type': 'icp', 'parameter': 'cu', 'unit': 'ppm', 'method': nan, 'experiment_id': '43'}`: n=2, technical_replicate_no=['2', '1'], values=[14.4, 22.1] — looks OK (distinct replicate numbers)


### Recommendation

`method` does not change the grouping at all for this snapshot (0 WITHOUT-method groups would be split by adding `method`). It is safe to drop `method` from the key without losing any discrimination, though keeping it does no harm either since it produces the same groups. **Recommended: keep current REPLICATE_GROUP_KEYS = ['sample_id', 'analysis_type', 'parameter', 'unit', 'method', 'experiment_id']** (no change needed; method is harmless to retain, and retaining it keeps the key aligned with the handoff's suggested key of `sample_id + analysis_type + parameter + method/protocol_version + lab`).


### Stop-condition assessment (handoff Step 0)

Overall singleton rate with current key: 27.5% (746 / 2712 groups).

Sample sanity check: 0 / 5 sampled multi-row groups showed duplicate/suspicious `technical_replicate_no` values.


**STOP CONDITION: NOT TRIGGERED.** The singleton rate and replicate-number sanity check do not indicate a broken grouping key overall — it looks reasonable to proceed to Step 1 (Build the Replicate-Group Summary) using the recommended key above. Note that some individual `analysis_type` values with low row counts (e.g. `ultimate`, `xrd`) may still have high singleton rates purely due to low data volume — see the per-analysis_type breakdown above; these should be carried forward with n=1 documented per the handoff's "carry both forward" spirit, not treated as a general grouping failure.

