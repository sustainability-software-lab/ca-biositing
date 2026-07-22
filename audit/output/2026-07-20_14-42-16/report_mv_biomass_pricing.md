# 🔍 Detailed Target Audit: `mv_biomass_pricing` — 2026-07-20

**Flagged Observations:** 16 (0 HIGH, 0 MEDIUM, 16 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The audit of the `mv_biomass_pricing` dataset, consisting of 73 records, reveals significant statistical dispersion and metadata deficiencies. The dataset maintains a mean price of 361.9, yet the median sits at a much lower 72.2, with a standard deviation of 779.95. This extreme right-skew is primarily driven by 'almond hash' records, which reach values as high as 3,140, contrasted against 'almond shells' which average near 30. The absence of specific parameter names for all flagged records complicates the distinction between different market grades or processing levels.

The most critical finding is the potential unit or scale mismatch within the 'almond hash' and 'almond hulls' resources. While the 'price_unit' column is constant across the dataset, the observed values suggest that some resources may be priced per truckload or per container rather than the standard ton, or they may reflect currency conversion errors. Furthermore, the total lack of 'parameter_name' metadata across the flagged observations prevents a definitive assessment of whether these values represent spot prices, contract prices, or delivered costs, which significantly hinders the utility of the data for comparative economic analysis.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| 39 | almond shells | — | — |  | 39.3000 | 2.07 | LOW |
| 31 | almond hulls | — | — |  | 252.2600 | 2.72 | LOW |
| 34 | almond shells | — | — |  | 38.3500 | 1.99 | LOW |
| 10 | almond hulls | — | — |  | 217.0000 | 2.03 | LOW |
| 64 | almond hash | — | — |  | 1614.0000 | 1.11 | LOW |
| 72 | almond hash | — | — |  | 3140.0000 | 1.61 | LOW |
| 73 | almond hash | — | — |  | 3140.0000 | 1.61 | LOW |
| 65 | almond hash | — | — |  | 1614.0000 | 1.11 | LOW |
| 37 | almond shells | — | — |  | 34.8800 | 1.72 | LOW |
| 32 | almond hulls | — | — |  | 213.0000 | 1.95 | LOW |
| 38 | almond shells | — | — |  | 29.6700 | 1.30 | LOW |
| 8 | almond hulls | — | — |  | 209.0000 | 1.87 | LOW |
| 41 | almond shells | — | — |  | 29.1000 | 1.25 | LOW |
| 36 | almond shells | — | — |  | 32.0200 | 1.49 | LOW |
| 1 | almond hulls | — | — |  | 194.5500 | 1.59 | LOW |
| 35 | almond shells | — | — |  | 37.0000 | 1.89 | LOW |
