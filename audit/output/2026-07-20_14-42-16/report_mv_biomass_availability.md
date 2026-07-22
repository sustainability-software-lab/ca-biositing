# 🔍 Detailed Target Audit: `mv_biomass_availability` — 2026-07-20

**Flagged Observations:** 0 (0 HIGH, 0 MEDIUM, 0 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

---

## 🧠 LLM Synthesis

The audit of the `mv_biomass_availability` dataset reveals a critical deficiency in data completeness, specifically regarding the primary metric of interest. With an 85.56% missingness rate in the `observed_value` column, the dataset currently serves more as a registry of resource names than a functional tool for biomass availability analysis. Out of 90 total records, only 13 contain valid observations, which severely limits any statistical inference or supply chain modeling that relies on these figures.

Furthermore, while the dataset identifies 90 unique resource names, the distribution of the existing 13 values is highly constrained, showing only 9 unique data points. The record ID sequence also shows gaps, with a maximum ID of 110 despite only 90 rows being present, suggesting potential record deletions or filtering in the view's underlying query. Immediate remediation is required to populate the missing availability data before this dataset is used for any downstream agricultural planning or research.
