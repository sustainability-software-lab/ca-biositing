# 🔍 Detailed Target Audit: `mv_biomass_sample_stats` — 2026-07-20

**Flagged Observations:** 0 (0 HIGH, 0 MEDIUM, 0 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

---

## 🧠 LLM Synthesis

The audit of the `mv_biomass_sample_stats` dataset reveals a distribution characterized by extreme positive skewness and a significant concentration of baseline values. With 68% of the observed values recorded as exactly '1.0' and a maximum value of 6752, the dataset exhibits a standard deviation (~1070) that is more than triple the mean (~312). This statistical profile is indicative of either a mixture of distinct measurement scales (e.g., unit mismatches) or a 'long-tail' distribution where a few resources contribute the vast majority of biomass metrics while most remain at a nominal baseline.

While the data integrity is high in terms of completeness—showing zero missing values and a 1:1 relationship between records and resource names—the extreme outliers in the upper quartiles warrant immediate investigation. The jump from the 75th percentile (51.5) to the maximum (6752) suggests that the highest values may be the result of data entry errors, such as the failure to convert mass units (e.g., kg vs g) or the inadvertent inclusion of cumulative totals rather than individual sample statistics.
