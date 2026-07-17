# 🔍 Detailed Target Audit: `proximate` — 2026-07-17

**Flagged Observations:** 275 (0 HIGH, 1 MEDIUM, 274 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

---

## 🧠 LLM Synthesis

The proximate analysis audit of 912 records indicates a statistically stable but procedurally incomplete dataset. The dataset maintains an average observed value of 41.64%, which closely aligns with the reference mean of 40.96%. However, the current dataset shows a higher frequency of high-moisture agricultural residuals, such as tomato pomace and grape stems, compared to the reference distribution. This shift in feedstock profile has triggered 275 low-severity flags primarily due to z-score deviations in moisture and total solids content. While these values appear biologically plausible for fresh residuals (e.g., tomato pomace moisture at ~80%), they represent a departure from the historical baseline which likely favored drier biomass like shells or hulls.

Significant data quality concerns were identified regarding administrative metadata. The 'analyst_name' field is 100% null, and 'analyst_email' is missing for over 50% of the records. This represents a critical failure in laboratory traceability and chain of custody. Furthermore, while the mathematical relationship between Moisture and Total Solids (summing to 100%) is strictly maintained across flagged records, there is a minor but consistent mass balance discrepancy between Total Solids and the sum of Volatile Solids and Ash. This suggests either a small unmeasured fraction (such as fixed carbon) or a minor systematic drift in the gravimetric drying and ignition protocols used for these specific high-moisture resources.

## 🚩 Flagged Observations (Top 100)

| Record ID | Parameter | Value | Z-Score | Severity |
|-----------|-----------|-------|---------|----------|
| (73)9335 | ash solids | 0.6900 | 1.99 | LOW |
| (55)a0cd | moisture | 80.7400 | 1.23 | LOW |
| (55)c24c | moisture | 80.9300 | 1.25 | LOW |
| (55)8c83 | moisture | 80.7500 | 1.23 | LOW |
| (55)afbf | ash solids | 0.7600 | 1.60 | LOW |
| (55)1963 | ash solids | 0.8500 | 1.09 | LOW |
| (55)1e0d | total solids | 19.2600 | 1.23 | LOW |
| (55)edd2 | total solids | 19.0700 | 1.25 | LOW |
| (55)9fb3 | total solids | 19.2500 | 1.23 | LOW |
| (55)ac67 | volatile solids | 18.3000 | 1.23 | LOW |
| (55)d348 | volatile solids | 18.3100 | 1.23 | LOW |
| (55)bfa7 | volatile solids | 18.4000 | 1.22 | LOW |
| (31)2091 | moisture | 70.3700 | 1.44 | LOW |
| (31)0a4b | ash solids | 3.1800 | 1.29 | LOW |
| (31)ae33 | total solids | 29.6300 | 1.44 | LOW |
| (31)9831 | volatile solids | 26.7100 | 1.43 | LOW |
| (d2)dc17 | moisture | 59.1900 | 1.06 | LOW |
| (d2)7df7 | ash solids | 10.3700 | 1.15 | LOW |
| (d2)8f44 | total solids | 40.8100 | 1.06 | LOW |
| (d2)0e21 | volatile solids | 30.4400 | 1.13 | LOW |
| (04)4ab5 | moisture | 7.1900 | 1.01 | LOW |
| (04)986f | ash solids | 0.6600 | 1.51 | LOW |
| (04)3ab3 | ash solids | 0.5200 | 1.31 | LOW |
| (04)93fb | total solids | 92.8100 | 1.01 | LOW |
| (c5)1f33 | moisture | 10.7900 | 1.16 | LOW |
| (c5)24ec | total solids | 89.2100 | 1.16 | LOW |
| (c5)38cf | volatile solids | 88.6200 | 1.15 | LOW |
| (c4)370c | moisture | 1.3500 | 1.15 | LOW |
| (c4)2c69 | ash solids | 0.1700 | 1.15 | LOW |
| (c4)95d4 | total solids | 98.6500 | 1.15 | LOW |
| (c4)c0c2 | volatile solids | 98.3900 | 1.08 | LOW |
| (63)f7da | moisture | 88.2300 | 1.13 | LOW |
| (63)074e | ash solids | 3.5200 | 1.15 | LOW |
| (63)20ff | total solids | 11.7700 | 1.13 | LOW |
| (63)5e8c | volatile solids | 8.2400 | 1.15 | LOW |
| (13)0c41 | moisture | 64.9800 | 1.31 | LOW |
| (13)61f0 | total solids | 35.0200 | 1.31 | LOW |
| (13)9fd0 | volatile solids | 33.1000 | 1.10 | LOW |
| (13)df67 | volatile solids | 30.8900 | 1.52 | LOW |
| (31)d70c | ash solids | 5.4300 | 1.32 | LOW |
| (31)52a8 | ash solids | 5.6000 | 1.22 | LOW |
| (31)797b | volatile solids | 80.9100 | 1.07 | LOW |
| (24)bbda | ash solids | 6.8300 | 1.39 | LOW |
| (24)ea69 | ash solids | 7.3200 | 1.77 | LOW |
| (24)7d51 | ash solids | 6.8100 | 1.38 | LOW |
| (03)b1b0 | moisture | 15.4400 | 1.05 | LOW |
| (03)ca72 | total solids | 84.5600 | 1.05 | LOW |
| (72)4254 | moisture | 18.2700 | 1.14 | LOW |
| (72)d7d8 | ash solids | 4.6100 | 1.12 | LOW |
| (72)32e2 | total solids | 81.7300 | 1.14 | LOW |
| (72)111d | volatile solids | 76.7100 | 1.12 | LOW |
| (28)1cdc | moisture | 4.8900 | 1.00 | LOW |
| (28)37a3 | moisture | 4.9500 | 1.00 | LOW |
| (28)ec2a | ash solids | 10.9200 | 1.11 | LOW |
| (28)7463 | total solids | 95.1100 | 1.00 | LOW |
| (28)5dec | total solids | 95.0500 | 1.00 | LOW |
| (28)17f4 | volatile solids | 84.1900 | 1.11 | LOW |
| (5b)4d95 | moisture | 12.7000 | 1.15 | LOW |
| (5b)5997 | ash solids | 5.0600 | 1.05 | LOW |
| (5b)35b8 | total solids | 87.3000 | 1.15 | LOW |
| (5b)ace1 | volatile solids | 82.0900 | 1.15 | LOW |
| (13)2169 | moisture | 19.0500 | 2.21 | LOW |
| (13)1b04 | moisture | 19.0000 | 2.20 | LOW |
| (13)12b9 | moisture | 19.0600 | 2.21 | LOW |
| (13)124d | ash solids | 3.6400 | 1.07 | LOW |
| (13)6c40 | ash solids | 3.7100 | 1.01 | LOW |
| (13)bae5 | total solids | 80.9500 | 2.21 | LOW |
| (13)dda4 | total solids | 81.0000 | 2.20 | LOW |
| (13)7fbd | total solids | 80.9400 | 2.21 | LOW |
| (13)710c | volatile solids | 77.3100 | 2.05 | LOW |
| (13)f8f6 | volatile solids | 77.2900 | 2.06 | LOW |
| (13)1443 | volatile solids | 77.1800 | 2.09 | LOW |
| (15)efa4 | moisture | 15.4900 | 1.09 | LOW |
| (15)9e63 | moisture | 15.4400 | 1.05 | LOW |
| (15)9a81 | total solids | 84.5100 | 1.09 | LOW |
| (15)19f2 | total solids | 84.5600 | 1.05 | LOW |
| (a0)e490 | moisture | 18.1300 | 1.56 | LOW |
| (a0)5eca | moisture | 18.2500 | 1.60 | LOW |
| (a0)76dd | moisture | 18.2100 | 1.58 | LOW |
| (a0)8a8a | total solids | 81.8700 | 1.56 | LOW |
| (a0)3630 | total solids | 81.7500 | 1.60 | LOW |
| (a0)0798 | total solids | 81.7900 | 1.58 | LOW |
| (42)729d | moisture | 6.7500 | 1.15 | LOW |
| (42)a6fe | ash solids | 11.9700 | 1.11 | LOW |
| (42)a5e2 | ash solids | 11.8700 | 1.30 | LOW |
| (42)c366 | total solids | 93.2500 | 1.15 | LOW |
| (42)c1de | volatile solids | 81.2400 | 1.15 | LOW |
| (da)66a0 | moisture | 5.3100 | 1.41 | LOW |
| (da)fa91 | ash solids | 8.7200 | 1.76 | LOW |
| (da)f61e | total solids | 94.6900 | 1.41 | LOW |
| (da)b8d0 | volatile solids | 85.9700 | 1.68 | LOW |
| (14)ff20 | moisture | 97.0800 | 1.10 | LOW |
| (14)bd40 | ash solids | 0.3300 | 1.15 | LOW |
| (14)e88d | total solids | 2.9200 | 1.10 | LOW |
| (14)eb17 | volatile solids | 2.6100 | 1.15 | LOW |
| (23)6951 | moisture | 97.0600 | 1.01 | LOW |
| (23)5b30 | ash solids | 0.2600 | 1.15 | LOW |
| (23)77d7 | total solids | 2.9400 | 1.01 | LOW |
| (23)3d5d | volatile solids | 2.2200 | 1.01 | LOW |
| (f6)eefe | moisture | 68.9900 | 1.08 | LOW |

*...and 175 more observations. See `flagged_proximate.csv` for full data.*
