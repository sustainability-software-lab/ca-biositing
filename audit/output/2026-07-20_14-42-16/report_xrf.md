# 🔍 Detailed Target Audit: `xrf` — 2026-07-20

**Flagged Observations:** 613 (0 HIGH, 8 MEDIUM, 605 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The audit of the XRF (X-Ray Fluorescence) dataset, encompassing 2,431 records across 24 agricultural biomass resources, reveals a significant volume of statistical anomalies, particularly within almond-derived residues. While the data shows 100% completeness for core fields like 'observed_value' and 'analyst_email', the presence of over 600 flagged observations—mostly at 'LOW' severity but including critical 'MEDIUM' flags—suggests systematic variability in elemental concentration reporting. Notably, almond hulls and cotton stem mix exhibit the highest frequency of anomalous readings for both heavy metals (Zn, Th, U) and macronutrients (Si, K, S).

Statistically, the dataset is characterized by extreme skewness, with 'observed_value' ranging from 0 to 161,000. The prevalence of 0.0 values (8.1% of the dataset) likely represents 'Below Detection Limit' (BDL) results, though their high z-scores in specific parameters like Manganese (Mn) suggest these zeros are statistically significant departures from the expected mean. Variations in data patterns between providers 'tiny' and 'capstan' indicate potential differences in instrument calibration or sample preparation protocols. The total absence of data in the 'note' and 'analyst_name' fields, while partially mitigated by the presence of 'analyst_email', limits the ability to contextualize these quantitative outliers with qualitative experimental observations.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| (03)0161 | almond hulls | tiny | — | la | 0.0000 | 2.32 | LOW |
| (03)0663 | almond hulls | tiny | — | rb | 7.0000 | 1.45 | LOW |
| (03)1c00 | almond hulls | tiny | — | zn | 25.0000 | 3.61 | MEDIUM |
| (03)1dc2 | almond hulls | tiny | — | mo | 10.0000 | 2.00 | LOW |
| (03)2448 | almond hulls | tiny | — | th | 76.0000 | 3.40 | MEDIUM |
| (03)3e42 | almond hulls | tiny | — | s | 359.0000 | 1.17 | LOW |
| (03)645d | almond hulls | tiny | — | ca | 3850.0000 | 1.24 | LOW |
| (03)663c | almond hulls | tiny | — | si | 17900.0000 | 3.22 | MEDIUM |
| (03)68d1 | almond hulls | tiny | — | u | 21.0000 | 3.02 | MEDIUM |
| (03)6a5b | almond hulls | tiny | — | fe | 527.0000 | 1.76 | LOW |
| (03)79f8 | almond hulls | tiny | — | ti | 344.0000 | 2.28 | LOW |
| (03)82cf | almond hulls | tiny | — | p | 529.0000 | 2.06 | LOW |
| (03)bbdf | almond hulls | tiny | — | k | 39100.0000 | 1.40 | LOW |
| (03)d09a | almond hulls | tiny | — | nd | 0.0000 | 1.44 | LOW |
| (03)da2a | almond hulls | tiny | — | mn | 0.0000 | 3.32 | MEDIUM |
| (03)ea08 | almond hulls | tiny | — | ce | 42.0000 | 1.05 | LOW |
| (04)0a4a | almond shells | capstan | — | cu | 9.0000 | 1.33 | LOW |
| (04)0e4d | almond shells | capstan | — | pr | 147.0000 | 1.45 | LOW |
| (04)661b | almond shells | capstan | — | mn | 31.0000 | 1.18 | LOW |
| (04)9261 | almond shells | capstan | — | ce | 78.0000 | 1.27 | LOW |
| (04)c6e9 | almond shells | capstan | — | mn | 51.0000 | 1.67 | LOW |
| (04)f326 | almond shells | capstan | — | mn | 30.0000 | 1.32 | LOW |
| (15)0c45 | walnut shells | cutaway | — | sr | 17.0000 | 1.22 | LOW |
| (15)290b | walnut shells | cutaway | — | cu | 10.0000 | 1.05 | LOW |
| (15)7432 | walnut shells | cutaway | — | s | 291.0000 | 1.46 | LOW |
| (15)cc90 | walnut shells | cutaway | — | sr | 19.0000 | 1.22 | LOW |
| (24)3474 | grape pomace | boatswain | — | la | 3030.0000 | 2.27 | LOW |
| (24)4337 | grape pomace | boatswain | — | mn | 54.0000 | 1.19 | LOW |
| (24)55e4 | grape pomace | boatswain | — | u | 12.0000 | 1.22 | LOW |
| (24)5cba | grape pomace | boatswain | — | zn | 26.0000 | 1.36 | LOW |
| (24)7190 | grape pomace | boatswain | — | k | 20300.0000 | 1.15 | LOW |
| (24)80af | grape pomace | boatswain | — | fe | 380.0000 | 1.03 | LOW |
| (24)95d4 | grape pomace | boatswain | — | th | 36.0000 | 1.23 | LOW |
| (24)9d04 | grape pomace | boatswain | — | fe | 387.0000 | 1.12 | LOW |
| (24)b5ac | grape pomace | boatswain | — | si | 3270.0000 | 1.38 | LOW |
| (24)bc68 | grape pomace | boatswain | — | rb | 3.0000 | 1.07 | LOW |
| (24)bea0 | grape pomace | boatswain | — | k | 20300.0000 | 1.15 | LOW |
| (24)c423 | grape pomace | boatswain | — | si | 3220.0000 | 1.32 | LOW |
| (24)c76f | grape pomace | boatswain | — | ce | 3990.0000 | 2.27 | LOW |
| (24)c777 | grape pomace | boatswain | — | ba | 2090.0000 | 3.33 | MEDIUM |
| (24)c93f | grape pomace | boatswain | — | fe | 389.0000 | 1.15 | LOW |
| (24)e688 | grape pomace | boatswain | — | rb | 3.0000 | 1.07 | LOW |
| (24)ed40 | grape pomace | boatswain | — | si | 3290.0000 | 1.40 | LOW |
| (24)f8ff | grape pomace | boatswain | — | rb | 3.0000 | 1.07 | LOW |
| (27)0312 | almond hulls | tiny | — | fe | 463.0000 | 1.10 | LOW |
| (27)1859 | almond hulls | tiny | — | fe | 500.0000 | 1.48 | LOW |
| (27)65d2 | almond hulls | tiny | — | fe | 462.0000 | 1.09 | LOW |
| (27)8cf6 | almond hulls | tiny | — | ce | 65.0000 | 1.15 | LOW |
| (27)9af4 | almond hulls | tiny | — | s | 214.0000 | 1.14 | LOW |
| (27)edc1 | almond hulls | tiny | — | rb | 8.0000 | 1.29 | LOW |
| (29)0b5a | walnut shells | energetic | — | al | 0.0000 | 1.13 | LOW |
| (29)1def | walnut shells | energetic | — | fe | 41.0000 | 1.49 | LOW |
| (29)4607 | walnut shells | energetic | — | ca | 8200.0000 | 1.50 | LOW |
| (29)4b23 | walnut shells | energetic | — | k | 12700.0000 | 1.48 | LOW |
| (29)55e0 | walnut shells | energetic | — | ba | 36.0000 | 1.19 | LOW |
| (29)5c68 | walnut shells | energetic | — | rb | 0.0000 | 1.47 | LOW |
| (29)6322 | walnut shells | energetic | — | cu | 15.0000 | 1.05 | LOW |
| (29)7a00 | walnut shells | energetic | — | p | 705.0000 | 1.49 | LOW |
| (29)aa06 | walnut shells | energetic | — | ce | 0.0000 | 1.48 | LOW |
| (29)c080 | walnut shells | energetic | — | zn | 21.0000 | 1.48 | LOW |
| (29)c43e | walnut shells | energetic | — | si | 400.0000 | 1.47 | LOW |
| (29)e246 | walnut shells | energetic | — | pr | 0.0000 | 1.15 | LOW |
| (29)fbc4 | walnut shells | energetic | — | u | 22.0000 | 1.45 | LOW |
| (29)fdf5 | walnut shells | energetic | — | th | 72.0000 | 1.47 | LOW |
| (29)fe09 | walnut shells | energetic | — | ti | 0.0000 | 1.15 | LOW |
| (42)00bd | rice straw | possessive | — | th | 63.0000 | 1.46 | LOW |
| (42)2aba | rice straw | possessive | — | ti | 559.0000 | 1.14 | LOW |
| (42)2f18 | rice straw | possessive | — | mn | 920.0000 | 1.03 | LOW |
| (42)33af | rice straw | possessive | — | al | 8930.0000 | 1.05 | LOW |
| (42)33f4 | rice straw | possessive | — | mg | 9700.0000 | 1.30 | LOW |
| (42)5074 | rice straw | possessive | — | zn | 66.0000 | 1.07 | LOW |
| (42)646b | rice straw | possessive | — | si | 91600.0000 | 1.72 | LOW |
| (42)835a | rice straw | possessive | — | u | 23.0000 | 1.04 | LOW |
| (42)a467 | rice straw | possessive | — | cu | 24.0000 | 1.22 | LOW |
| (42)ae01 | rice straw | possessive | — | as | 8.0000 | 1.15 | LOW |
| (42)b359 | rice straw | possessive | — | ca | 10500.0000 | 1.15 | LOW |
| (42)d223 | rice straw | possessive | — | cu | 23.0000 | 1.07 | LOW |
| (42)d6ff | rice straw | possessive | — | p | 2560.0000 | 1.31 | LOW |
| (42)e4b6 | rice straw | possessive | — | sr | 34.0000 | 1.32 | LOW |
| (42)f66d | rice straw | possessive | — | th | 72.0000 | 1.26 | LOW |
| (48)0028 | spent oak chips | rigging | — | mn | 20.0000 | 1.10 | LOW |
| (48)098e | spent oak chips | rigging | — | ba | 25.0000 | 1.35 | LOW |
| (48)118d | spent oak chips | rigging | — | k | 32100.0000 | 1.91 | LOW |
| (48)1a28 | spent oak chips | rigging | — | mo | 4.0000 | 1.50 | LOW |
| (48)1f4d | spent oak chips | rigging | — | rb | 18.0000 | 1.30 | LOW |
| (48)435d | spent oak chips | rigging | — | ti | 252.0000 | 1.15 | LOW |
| (48)5469 | spent oak chips | rigging | — | s | 1660.0000 | 1.67 | LOW |
| (48)61cf | spent oak chips | rigging | — | k | 32000.0000 | 1.90 | LOW |
| (48)6513 | spent oak chips | rigging | — | u | 16.0000 | 1.14 | LOW |
| (48)690f | spent oak chips | rigging | — | th | 50.0000 | 1.87 | LOW |
| (48)9155 | spent oak chips | rigging | — | u | 15.0000 | 1.55 | LOW |
| (48)b713 | spent oak chips | rigging | — | s | 1620.0000 | 1.82 | LOW |
| (48)bd1e | spent oak chips | rigging | — | rb | 20.0000 | 1.73 | LOW |
| (48)c60a | spent oak chips | rigging | — | ca | 1720.0000 | 1.79 | LOW |
| (48)d3ca | spent oak chips | rigging | — | ca | 1730.0000 | 1.83 | LOW |
| (48)de20 | spent oak chips | rigging | — | si | 396.0000 | 1.31 | LOW |
| (48)e5b8 | spent oak chips | rigging | — | s | 1790.0000 | 1.22 | LOW |
| (48)e8ea | spent oak chips | rigging | — | ce | 44.0000 | 1.24 | LOW |
| (48)f8a1 | spent oak chips | rigging | — | rb | 20.0000 | 1.73 | LOW |
| (4c)0781 | almond branches | humorous | — | s | 798.0000 | 1.02 | LOW |

*...and 513 more observations. See `flagged_xrf.csv` for full data.*
