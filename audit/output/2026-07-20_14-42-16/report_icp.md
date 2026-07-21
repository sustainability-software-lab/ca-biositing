# 🔍 Detailed Target Audit: `icp` — 2026-07-20

**Flagged Observations:** 147 (0 HIGH, 0 MEDIUM, 147 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The audit of the Inductively Coupled Plasma (ICP) dataset, comprising 668 records, reveals a generally stable collection of elemental mass fractions across various agricultural biomass residues, specifically tomato pomace and almond-related byproducts. The majority of flagged observations (147) are categorized as low severity, representing statistical deviations (Z-scores typically between 1.0 and 2.4) rather than catastrophic data failures. These variances are predominantly seen in macronutrients like Potassium (K) and Sodium (Na), as well as trace metals such as Manganese (Mn) and Zinc (Zn).

However, a critical concern was identified in the dataset summary: a minimum observed value of -244.0 mg/kg. In ICP analysis, negative values are physically impossible and typically indicate failed background subtraction or severe calibration drift during the laboratory run. While the analyst mduran@lbl.gov is consistently associated with these records, the complete absence of data in the 'analyst_name' field and 'sample_date' column for many records limits the ability to perform a temporal drift analysis. The silicon (Si) outliers observed in tomato pomace remain within the expected range for soil-contact residues and are treated with low priority per domain standards.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| (26)7272 | tomato pomace | oakleaf | — | ti | 3.4800 | 1.67 | LOW |
| (26)0be0 | tomato pomace | oakleaf | — | s | 1530.0000 | 1.03 | LOW |
| (26)a23d | tomato pomace | oakleaf | — | zn | 43.0000 | 2.38 | LOW |
| (69)3b52 | tomato pomace | pinecrest | — | al | 17.8000 | 1.48 | LOW |
| (69)66e5 | tomato pomace | pinecrest | — | ca | 2570.0000 | 1.14 | LOW |
| (69)fb3a | tomato pomace | pinecrest | — | k | 20300.0000 | 1.24 | LOW |
| (69)7ba0 | tomato pomace | pinecrest | — | mg | 1550.0000 | 1.43 | LOW |
| (69)1bde | tomato pomace | pinecrest | — | mn | 17.8000 | 1.47 | LOW |
| (69)eb00 | tomato pomace | pinecrest | — | na | 1440.0000 | 1.09 | LOW |
| (69)0335 | tomato pomace | pinecrest | — | nd | 7.1100 | 1.07 | LOW |
| (69)1a06 | tomato pomace | pinecrest | — | p | 2540.0000 | 1.12 | LOW |
| (69)c905 | tomato pomace | pinecrest | — | si | 15.0000 | 1.71 | LOW |
| (69)f2b1 | tomato pomace | pinecrest | — | ca | 2730.0000 | 1.41 | LOW |
| (69)8315 | tomato pomace | pinecrest | — | cu | 14.6000 | 1.08 | LOW |
| (69)0f35 | tomato pomace | pinecrest | — | k | 21000.0000 | 1.34 | LOW |
| (69)dd28 | tomato pomace | pinecrest | — | mn | 18.3000 | 1.42 | LOW |
| (69)5280 | tomato pomace | pinecrest | — | na | 1530.0000 | 1.25 | LOW |
| (69)aa3d | tomato pomace | pinecrest | — | nd | 7.3100 | 1.15 | LOW |
| (6d)a6af | tomato pomace | riverstone | — | mg | 2560.0000 | 1.11 | LOW |
| (6d)c741 | tomato pomace | riverstone | — | na | 232.0000 | 1.06 | LOW |
| (6d)4e82 | tomato pomace | riverstone | — | p | 4120.0000 | 1.25 | LOW |
| (6d)3e18 | tomato pomace | riverstone | — | na | 232.0000 | 1.06 | LOW |
| (6d)a2d8 | tomato pomace | riverstone | — | nd | 0.0000 | 1.54 | LOW |
| (6d)241f | tomato pomace | riverstone | — | s | 1520.0000 | 1.12 | LOW |
| (fe)f915 | grape pomace | maplewood | — | mg | 1040.0000 | 1.07 | LOW |
| (fe)6131 | grape pomace | maplewood | — | ti | 0.0000 | 1.50 | LOW |
| (fe)64dd | grape pomace | maplewood | — | al | 14.8000 | 1.50 | LOW |
| (fe)8bdb | grape pomace | maplewood | — | na | -55.0000 | 1.49 | LOW |
| (fe)9b50 | grape pomace | maplewood | — | nd | 7.4000 | 1.20 | LOW |
| (fe)3456 | grape pomace | maplewood | — | si | 18.0000 | 1.20 | LOW |
| (1b)7f08 | grape pomace | ebony | — | mn | 7.0000 | 1.08 | LOW |
| (1b)c568 | grape pomace | ebony | — | s | 1000.0000 | 1.03 | LOW |
| (1b)764e | grape pomace | ebony | — | zn | 14.2000 | 1.07 | LOW |
| (1b)82c1 | grape pomace | ebony | — | cu | 7.0000 | 1.57 | LOW |
| (1b)c1da | grape pomace | ebony | — | mn | 7.0000 | 1.08 | LOW |
| (1b)d08e | grape pomace | ebony | — | p | 1700.0000 | 1.34 | LOW |
| (1b)b586 | grape pomace | ebony | — | s | 921.0000 | 1.33 | LOW |
| (1b)21a6 | grape pomace | ebony | — | si | 28.5000 | 1.17 | LOW |
| (37)b44a | almond shells | vibrant | — | mn | 7.0000 | 1.74 | LOW |
| (37)ebd4 | almond shells | vibrant | — | ti | 4.0000 | 2.04 | LOW |
| (31)09a4 | almond hulls | vibrant | — | al | 11.0000 | 1.48 | LOW |
| (31)2103 | almond hulls | vibrant | — | k | 16400.0000 | 1.39 | LOW |
| (31)4f76 | almond hulls | vibrant | — | mn | 7.0000 | 1.42 | LOW |
| (31)f463 | almond hulls | vibrant | — | p | 468.0000 | 1.07 | LOW |
| (31)fb32 | almond hulls | vibrant | — | s | 172.0000 | 1.99 | LOW |
| (31)ff2f | almond hulls | vibrant | — | si | 11.0000 | 1.82 | LOW |
| (31)cd71 | almond hulls | vibrant | — | mg | 1110.0000 | 1.31 | LOW |
| (31)3a96 | almond hulls | vibrant | — | mn | 7.0000 | 1.42 | LOW |
| (31)0574 | almond hulls | vibrant | — | na | -220.0000 | 1.02 | LOW |
| (31)fdcb | almond hulls | vibrant | — | nd | 4.0000 | 1.03 | LOW |
| (c7)0f03 | almond branches | vibrant | — | mn | 33.0000 | 1.32 | LOW |
| (c7)15a4 | almond branches | vibrant | — | nd | 18.0000 | 1.45 | LOW |
| (c7)a0ff | almond branches | vibrant | — | s | 436.0000 | 1.35 | LOW |
| (c7)1321 | almond branches | vibrant | — | zn | 32.7000 | 1.07 | LOW |
| (24)9f55 | almond shells | tiny | — | ca | 3460.0000 | 1.23 | LOW |
| (24)a0f9 | almond shells | tiny | — | cu | 7.0000 | 1.68 | LOW |
| (24)8df9 | almond shells | tiny | — | k | 20700.0000 | 1.10 | LOW |
| (24)ab4b | almond shells | tiny | — | mg | 650.0000 | 1.23 | LOW |
| (24)95c2 | almond shells | tiny | — | na | 111.0000 | 1.26 | LOW |
| (24)6339 | almond shells | tiny | — | nd | 11.0000 | 1.29 | LOW |
| (24)4cc3 | almond shells | tiny | — | p | 872.0000 | 1.21 | LOW |
| (24)bad4 | almond shells | tiny | — | s | 336.0000 | 1.28 | LOW |
| (24)09a9 | almond shells | tiny | — | zn | 10.7000 | 1.26 | LOW |
| (24)0a68 | almond shells | tiny | — | ca | 3560.0000 | 1.35 | LOW |
| (24)264d | almond shells | tiny | — | k | 21400.0000 | 1.28 | LOW |
| (24)b7bb | almond shells | tiny | — | mg | 651.0000 | 1.25 | LOW |
| (24)cf04 | almond shells | tiny | — | na | 118.0000 | 1.30 | LOW |
| (24)eec2 | almond shells | tiny | — | nd | 11.0000 | 1.29 | LOW |
| (24)4f15 | almond shells | tiny | — | p | 847.0000 | 1.06 | LOW |
| (24)fade | almond shells | tiny | — | s | 343.0000 | 1.39 | LOW |
| (24)9d6c | almond shells | tiny | — | zn | 10.7000 | 1.26 | LOW |
| (03)9388 | almond hulls | tiny | — | cu | 11.0000 | 1.13 | LOW |
| (03)4572 | almond hulls | tiny | — | mg | 669.0000 | 1.27 | LOW |
| (03)d962 | almond hulls | tiny | — | zn | 7.1100 | 1.42 | LOW |
| (03)6da0 | almond hulls | tiny | — | cu | 11.0000 | 1.13 | LOW |
| (03)66c1 | almond hulls | tiny | — | mg | 712.0000 | 1.02 | LOW |
| (03)73d1 | almond hulls | tiny | — | mn | 15.0000 | 1.31 | LOW |
| (03)623d | almond hulls | tiny | — | na | -227.0000 | 1.08 | LOW |
| (03)7d30 | almond hulls | tiny | — | zn | 7.3400 | 1.57 | LOW |
| (13)bd21 | almond shells | humorous | — | zn | 4.0000 | 1.19 | LOW |
| (13)c1b2 | almond shells | humorous | — | al | 71.5000 | 1.76 | LOW |
| (13)8f20 | almond shells | humorous | — | k | 12300.0000 | 1.08 | LOW |
| (13)7a99 | almond shells | humorous | — | mg | 561.0000 | 1.02 | LOW |
| (13)1d63 | almond shells | humorous | — | p | 447.0000 | 1.33 | LOW |
| (13)e7cd | almond shells | humorous | — | s | 189.0000 | 1.00 | LOW |
| (13)a199 | almond shells | humorous | — | zn | 4.0000 | 1.19 | LOW |
| (15)1b12 | almond hulls | humorous | — | al | 18.0000 | 1.63 | LOW |
| (15)a295 | almond hulls | humorous | — | ca | 2100.0000 | 1.55 | LOW |
| (15)1cdf | almond hulls | humorous | — | cu | 4.0000 | 1.17 | LOW |
| (15)5ad4 | almond hulls | humorous | — | k | 24100.0000 | 1.18 | LOW |
| (15)6d1e | almond hulls | humorous | — | na | 36.0000 | 1.14 | LOW |
| (15)1f4f | almond hulls | humorous | — | nd | 4.0000 | 1.03 | LOW |
| (15)68af | almond hulls | humorous | — | p | 1130.0000 | 1.80 | LOW |
| (15)b384 | almond hulls | humorous | — | cu | 11.0000 | 1.13 | LOW |
| (15)89d8 | almond hulls | humorous | — | nd | 11.0000 | 1.68 | LOW |
| (a0)9bfb | almond branches | humorous | — | al | 29.0000 | 1.40 | LOW |
| (a0)7b53 | almond branches | humorous | — | cu | 14.0000 | 1.06 | LOW |
| (a0)9e7e | almond branches | humorous | — | k | 2250.0000 | 1.14 | LOW |
| (a0)d8d7 | almond branches | humorous | — | na | -212.0000 | 1.15 | LOW |
| (a0)badc | almond branches | humorous | — | s | 226.0000 | 1.06 | LOW |

*...and 47 more observations. See `flagged_icp.csv` for full data.*
