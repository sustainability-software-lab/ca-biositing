"""
00_validate_replicate_grouping.py — Step 0 diagnostic (throwaway/disposable script).

Purpose (handoff v4, "Step 0 — Determine the Technical Replicate Grouping Key"):
Validate that `analysis_config.REPLICATE_GROUP_KEYS` produces sensible technical
replicate groups from the raw extract BEFORE any replicate-summary statistics
(SD/RSD/Dixon) are built. This is a read-only diagnostic tool — it does not
write/modify the raw extract, extract_raw_data.py, or analysis_config.py, and it
does NOT build replicate_group_summary.csv (that's a separate, later task).

Outputs:
- stdout: full diagnostic report
- audit/outliers/biocirv_outlier_assessment/STEP0_FINDINGS.md: the
  "## Step 0 Findings" section, written fresh each run.

Usage:
    pixi run python audit/outliers/biocirv_outlier_assessment/00_validate_replicate_grouping.py
"""

from __future__ import annotations

import glob
import os
import sys

import pandas as pd

# Make analysis_config importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis_config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FINDINGS_PATH = os.path.join(HERE, "STEP0_FINDINGS.md")

REPLICATE_GROUP_KEYS = analysis_config.REPLICATE_GROUP_KEYS
KEYS_NO_METHOD = [k for k in REPLICATE_GROUP_KEYS if k != "method"]


def pick_latest_raw_extract() -> str:
    """Pick the most recent raw_extract_*.csv by filename (date-sortable)."""
    data_dir = os.path.join(HERE, "data")
    pattern = os.path.join(data_dir, "raw_extract_*.csv")
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No raw_extract_*.csv files found under {data_dir}")
    return candidates[-1]  # lexicographic sort == date sort for YYYYMMDD naming


def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=True)
    # value is numeric; keep as float for later use, everything else stays string-like.
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def fmt_pct(n: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{100.0 * n / total:.1f}%"


def group_and_describe(df: pd.DataFrame, keys: list[str], label: str) -> dict:
    """Group df by keys (dropna=False so nulls form their own group rather than
    being silently dropped by pandas' default groupby behavior), and return a
    dict of summary stats."""
    grouped = df.groupby(keys, dropna=False, sort=False)
    sizes = grouped.size()
    n_groups = len(sizes)
    n_rows = len(df)
    singleton_groups = int((sizes == 1).sum())
    multi_groups = int((sizes >= 2).sum())

    print(f"\n--- Grouping: {label} (keys={keys}) ---")
    print(f"Total rows: {n_rows}")
    print(f"Total groups: {n_groups}")
    print(f"Singleton groups (n=1): {singleton_groups} ({fmt_pct(singleton_groups, n_groups)} of groups)")
    print(f"Groups with n>=2: {multi_groups} ({fmt_pct(multi_groups, n_groups)} of groups)")
    print("Group size distribution (value_counts of n_rows_per_group):")
    print(sizes.value_counts().sort_index().to_string())

    return {
        "label": label,
        "keys": keys,
        "n_rows": n_rows,
        "n_groups": n_groups,
        "singleton_groups": singleton_groups,
        "multi_groups": multi_groups,
        "sizes": sizes,
        "grouped": grouped,
    }


def df_to_markdown_table(df: pd.DataFrame) -> str:
    """Minimal dependency-free markdown table renderer (avoids requiring the
    optional `tabulate` package that pandas.DataFrame.to_markdown needs)."""
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body_lines = []
    for _, row in df.iterrows():
        body_lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join([header, sep, *body_lines])


def per_analysis_type_breakdown(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for atype, sub in df.groupby("analysis_type", dropna=False):
        sizes = sub.groupby(keys, dropna=False, sort=False).size()
        n_groups = len(sizes)
        n_singleton = int((sizes == 1).sum())
        rows.append(
            {
                "analysis_type": atype,
                "n_rows": len(sub),
                "n_groups": n_groups,
                "n_singleton_groups": n_singleton,
                "singleton_rate_pct": round(100.0 * n_singleton / n_groups, 1) if n_groups else float("nan"),
                "n_multi_groups": n_groups - n_singleton,
            }
        )
    out = pd.DataFrame(rows).sort_values("n_rows", ascending=False).reset_index(drop=True)
    return out


def sample_multi_row_groups(df: pd.DataFrame, keys: list[str], n_samples: int = 5) -> list[dict]:
    grouped = df.groupby(keys, dropna=False, sort=False)
    multi_group_keys = [g for g, sub in grouped if len(sub) >= 2]
    sampled = multi_group_keys[:n_samples] if len(multi_group_keys) <= n_samples else \
        [multi_group_keys[i] for i in
         sorted(set(int(x) for x in pd.Series(range(len(multi_group_keys))).sample(
             n=n_samples, random_state=42)))]
    results = []
    for gkey in sampled:
        sub = grouped.get_group(gkey)
        rep_nos = sub["technical_replicate_no"].tolist()
        values = sub["value"].tolist()
        record_ids = sub["record_id"].tolist()
        n = len(sub)
        n_distinct_rep_nos = len(set(str(x) for x in rep_nos))
        suspicious_dupe_rep_no = n_distinct_rep_nos < n
        results.append(
            {
                "group_key": dict(zip(keys, gkey if isinstance(gkey, tuple) else (gkey,))),
                "n_rows": n,
                "technical_replicate_no": rep_nos,
                "values": values,
                "record_ids": record_ids,
                "duplicate_replicate_numbers": suspicious_dupe_rep_no,
            }
        )
    return results


def main() -> None:
    raw_path = pick_latest_raw_extract()
    print(f"Loaded raw extract: {raw_path}")
    df = load_raw(raw_path)
    total_rows = len(df)
    print(f"Total rows: {total_rows}")
    print(f"Configured REPLICATE_GROUP_KEYS (analysis_config.py): {REPLICATE_GROUP_KEYS}")

    # --- Null sample_id check -------------------------------------------------
    null_sample_id_mask = df["sample_id"].isna() | (df["sample_id"].astype(str).str.strip() == "")
    n_null_sample_id = int(null_sample_id_mask.sum())
    print("\n--- Null / missing sample_id check ---")
    print(f"Rows with null/missing sample_id: {n_null_sample_id} ({fmt_pct(n_null_sample_id, total_rows)} of total rows)")

    df_groupable = df.loc[~null_sample_id_mask].copy()

    # --- Main grouping (current config key) -----------------------------------
    with_method = group_and_describe(df_groupable, REPLICATE_GROUP_KEYS, "WITH method (current config)")

    # --- Comparison grouping without method ------------------------------------
    without_method = group_and_describe(df_groupable, KEYS_NO_METHOD, "WITHOUT method")

    print("\n--- Method-key impact comparison ---")
    print(f"n_groups WITH method:    {with_method['n_groups']}")
    print(f"n_groups WITHOUT method: {without_method['n_groups']}")
    delta = with_method["n_groups"] - without_method["n_groups"]
    print(f"Delta (WITH - WITHOUT):  {delta}")

    n_null_method = int(df_groupable["method"].isna().sum() | (df_groupable["method"].astype(str).str.strip() == "").sum())
    n_null_method = int((df_groupable["method"].isna() | (df_groupable["method"].astype(str).str.strip() == "")).sum())
    print(f"Rows with null/missing method: {n_null_method} ({fmt_pct(n_null_method, len(df_groupable))} of groupable rows)")

    # How many WITHOUT-method groups get split into >1 WITH-method group?
    without_grouped = without_method["grouped"]
    split_count = 0
    without_group_keys_checked = 0
    for gkey, sub in without_grouped:
        without_group_keys_checked += 1
        n_method_variants = sub["method"].fillna("<NULL>").nunique()
        if n_method_variants > 1:
            split_count += 1
    print(
        f"Of {without_group_keys_checked} WITHOUT-method groups, "
        f"{split_count} ({fmt_pct(split_count, without_group_keys_checked)}) contain >1 distinct "
        f"`method` value (i.e. adding `method` to the key would split them further)."
    )

    # --- Per-analysis-type breakdown (using current config key) ----------------
    print("\n--- Per-analysis_type breakdown (current config key WITH method) ---")
    breakdown = per_analysis_type_breakdown(df_groupable, REPLICATE_GROUP_KEYS)
    print(breakdown.to_string(index=False))

    # --- Sanity check: sample of multi-row groups -------------------------------
    print("\n--- Sanity check: technical_replicate_no values within sample multi-row groups (current config key) ---")
    samples = sample_multi_row_groups(df_groupable, REPLICATE_GROUP_KEYS, n_samples=5)
    for i, s in enumerate(samples, start=1):
        print(f"\nSample group {i}: {s['group_key']}")
        print(f"  n_rows: {s['n_rows']}")
        print(f"  technical_replicate_no: {s['technical_replicate_no']}")
        print(f"  values: {s['values']}")
        print(f"  record_ids: {s['record_ids']}")
        flag = "SUSPICIOUS (duplicate replicate numbers)" if s["duplicate_replicate_numbers"] else "looks OK (distinct replicate numbers)"
        print(f"  assessment: {flag}")

    # --- Overall stop-condition assessment --------------------------------------
    overall_singleton_rate = 100.0 * with_method["singleton_groups"] / with_method["n_groups"] if with_method["n_groups"] else 0.0
    n_suspicious_samples = sum(1 for s in samples if s["duplicate_replicate_numbers"])
    stop_condition_triggered = overall_singleton_rate > 90.0 or n_suspicious_samples >= max(1, len(samples) // 2)

    # --- Build findings markdown -------------------------------------------------
    lines = []
    lines.append("## Step 0 Findings\n")
    lines.append(f"Source raw extract: `{os.path.basename(raw_path)}`\n")
    lines.append(f"Total rows: {total_rows}\n")
    lines.append(f"Confirmed current `analysis_config.REPLICATE_GROUP_KEYS`: `{REPLICATE_GROUP_KEYS}`\n")

    lines.append("\n### Null `sample_id`\n")
    lines.append(f"- Rows with null/missing `sample_id`: {n_null_sample_id} ({fmt_pct(n_null_sample_id, total_rows)} of total rows). These rows cannot be grouped by this key at all and were excluded from all grouping analysis below.\n")

    lines.append("\n### Grouping with current key (WITH `method`)\n")
    lines.append(f"- Total groups: {with_method['n_groups']}\n")
    lines.append(f"- Singleton groups (n=1): {with_method['singleton_groups']} ({fmt_pct(with_method['singleton_groups'], with_method['n_groups'])} of groups)\n")
    lines.append(f"- Groups with n>=2 (usable for SD): {with_method['multi_groups']} ({fmt_pct(with_method['multi_groups'], with_method['n_groups'])} of groups)\n")

    lines.append("\n### Grouping WITHOUT `method` (comparison)\n")
    lines.append(f"- Total groups: {without_method['n_groups']}\n")
    lines.append(f"- Singleton groups (n=1): {without_method['singleton_groups']} ({fmt_pct(without_method['singleton_groups'], without_method['n_groups'])} of groups)\n")
    lines.append(f"- Delta in group count (WITH - WITHOUT method): {delta}\n")
    lines.append(f"- Rows with null/missing `method`: {n_null_method} ({fmt_pct(n_null_method, len(df_groupable))} of groupable rows)\n")
    lines.append(f"- Of {without_group_keys_checked} WITHOUT-method groups, {split_count} ({fmt_pct(split_count, without_group_keys_checked)}) contain >1 distinct `method` value, i.e. would be split further by adding `method` to the key.\n")

    lines.append("\n### Per-`analysis_type` breakdown (current config key)\n")
    lines.append("\n")
    lines.append(df_to_markdown_table(breakdown))
    lines.append("\n")

    lines.append("\n### Sanity check: multi-row group `technical_replicate_no` samples\n")
    for i, s in enumerate(samples, start=1):
        flag = "SUSPICIOUS (duplicate replicate numbers)" if s["duplicate_replicate_numbers"] else "looks OK (distinct replicate numbers)"
        lines.append(f"- Sample group {i} `{s['group_key']}`: n={s['n_rows']}, technical_replicate_no={s['technical_replicate_no']}, values={s['values']} — {flag}\n")

    lines.append("\n### Recommendation\n")
    if delta == 0 and split_count == 0:
        method_recommendation = (
            "`method` does not change the grouping at all for this snapshot (0 WITHOUT-method groups "
            "would be split by adding `method`). It is safe to drop `method` from the key without losing "
            "any discrimination, though keeping it does no harm either since it produces the same groups. "
            f"**Recommended: keep current REPLICATE_GROUP_KEYS = {REPLICATE_GROUP_KEYS}** (no change needed; "
            "method is harmless to retain, and retaining it keeps the key aligned with the handoff's suggested "
            "key of `sample_id + analysis_type + parameter + method/protocol_version + lab`)."
        )
    elif split_count > 0 and n_null_method > 0 and (100.0 * n_null_method / len(df_groupable)) > 50:
        method_recommendation = (
            f"`method` is null/missing for {fmt_pct(n_null_method, len(df_groupable))} of groupable rows, "
            f"and adding it splits {split_count} pre-existing groups further. Because it is mostly null, "
            "much of that extra splitting is likely just fragmenting real technical-replicate groups apart "
            "on a null key rather than reflecting genuinely different methods. "
            f"**Recommended: drop `method` from REPLICATE_GROUP_KEYS -> use {KEYS_NO_METHOD}.**"
        )
    else:
        method_recommendation = (
            f"`method` is populated for the majority of rows and meaningfully discriminates groups "
            f"({split_count} of {without_group_keys_checked} WITHOUT-method groups contain >1 distinct method value). "
            f"**Recommended: keep current REPLICATE_GROUP_KEYS = {REPLICATE_GROUP_KEYS}** (method is doing real "
            "discriminating work and should not be dropped, per the handoff's caution against combining "
            "distinct experimental runs/methods unless shown to be true technical replicates)."
        )
    lines.append(method_recommendation + "\n")

    lines.append("\n### Stop-condition assessment (handoff Step 0)\n")
    lines.append(
        f"Overall singleton rate with current key: {overall_singleton_rate:.1f}% "
        f"({with_method['singleton_groups']} / {with_method['n_groups']} groups).\n"
    )
    lines.append(
        f"Sample sanity check: {n_suspicious_samples} / {len(samples)} sampled multi-row groups showed "
        "duplicate/suspicious `technical_replicate_no` values.\n"
    )
    if stop_condition_triggered:
        lines.append(
            "\n**STOP CONDITION: TRIGGERED.** Per the handoff (\"If true technical replicates cannot be "
            "identified reliably: Do not guess. Stop and report the grouping problem.\"), the singleton rate "
            "and/or replicate-number sanity check indicate the grouping key does not reliably identify true "
            "technical replicates for a large share of the data. This finding is documented here for human/"
            "orchestrator review; this script does not halt any downstream pipeline itself.\n"
        )
    else:
        lines.append(
            "\n**STOP CONDITION: NOT TRIGGERED.** The singleton rate and replicate-number sanity check do not "
            "indicate a broken grouping key overall — it looks reasonable to proceed to Step 1 (Build the "
            "Replicate-Group Summary) using the recommended key above. Note that some individual "
            "`analysis_type` values with low row counts (e.g. `ultimate`, `xrd`) may still have high "
            "singleton rates purely due to low data volume — see the per-analysis_type breakdown above; "
            "these should be carried forward with n=1 documented per the handoff's \"carry both forward\" "
            "spirit, not treated as a general grouping failure.\n"
        )

    findings_md = "\n".join(lines)

    with open(FINDINGS_PATH, "w", encoding="utf-8") as f:
        f.write(findings_md + "\n")

    print("\n" + "=" * 80)
    print(findings_md)
    print("=" * 80)
    print(f"\nFindings written to: {FINDINGS_PATH}")


if __name__ == "__main__":
    main()
