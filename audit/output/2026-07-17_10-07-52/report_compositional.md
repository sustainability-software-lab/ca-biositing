# 🔍 Detailed Target Audit: `compositional` — 2026-07-17

**Flagged Observations:** 249 (0 HIGH, 0 MEDIUM, 249 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

---

## 🧠 LLM Synthesis

The compositional analysis audit for the 723-record dataset reveals a significant deficit in metadata and laboratory traceability. Specifically, the 'note' and 'analyst_name' columns are entirely empty, and the 'analyst_email' is missing for over half of the records. This lack of provenance complicates the interpretation of the 249 'LOW' severity flags identified across major carbohydrate and lignin parameters. While the data shows internal stoichiometric consistency—indicated by the parallel flagging of monomer/polymer pairs like glucose/glucan—the lack of qualitative notes makes it impossible to determine if deviations are due to experimental conditions or genuine biological variance.

The statistical flags are heavily concentrated in almond-derived biomass (shells, hulls, and branches) and pomace (tomato and grape). Tomato pomace, in particular, shows elevated glucan and lignin levels (approx. 19% and 31% respectively) compared to the reference baseline. These shifts suggest either a difference in the seed-to-skin ratio of the sampled pomace or a change in the extraction protocol that hasn't been documented. Given that all records are marked as 'qc_pass', the primary concern is not catastrophic failure but a systematic drift in compositional profiles for specific agricultural residues that requires updated reference baselines.

## 🚩 Flagged Observations (Top 100)

| Record ID | Parameter | Value | Z-Score | Severity |
|-----------|-----------|-------|---------|----------|
| (d2)cadf | glucan | 19.0400 | 1.31 | LOW |
| (d2)bdb6 | glucan | 18.9000 | 1.26 | LOW |
| (d2)62d0 | glucan | 18.9800 | 1.29 | LOW |
| (d2)a7f3 | glucose | 21.1500 | 1.31 | LOW |
| (d2)4d07 | glucose | 21.0000 | 1.26 | LOW |
| (d2)d758 | glucose | 21.0800 | 1.28 | LOW |
| (d2)cea7 | xylan | 8.4600 | 1.14 | LOW |
| (d2)d344 | xylose | 9.6200 | 1.13 | LOW |
| (d2)2fae | lignin+ | 30.5300 | 1.51 | LOW |
| (d2)0b71 | lignin+ | 31.5700 | 1.27 | LOW |
| (d2)d96d | lignin+ | 31.9500 | 1.19 | LOW |
| (28)a602 | glucan | 11.7100 | 1.32 | LOW |
| (28)cfc4 | glucose | 13.0100 | 1.32 | LOW |
| (28)f0fe | xylan | 11.2600 | 1.69 | LOW |
| (28)847b | xylan | 11.0600 | 1.49 | LOW |
| (28)a3d2 | xylose | 12.8000 | 1.70 | LOW |
| (28)2429 | xylose | 12.5600 | 1.49 | LOW |
| (ab)e502 | xylan | 8.5200 | 1.33 | LOW |
| (ab)8cb1 | xylan | 8.1300 | 1.13 | LOW |
| (ab)9781 | xylan | 8.0600 | 1.10 | LOW |
| (ab)0af2 | xylose | 9.6900 | 1.21 | LOW |
| (ab)e013 | xylose | 9.2400 | 1.01 | LOW |
| (ab)c64d | lignin+ | 53.9600 | 1.11 | LOW |
| (4e)e137 | glucan | 5.5700 | 1.28 | LOW |
| (4e)e140 | glucose | 6.1900 | 1.29 | LOW |
| (4e)e143 | xylan | 2.9200 | 1.53 | LOW |
| (4e)e146 | xylose | 3.3200 | 1.54 | LOW |
| (4e)e151 | lignin | 47.8400 | 1.50 | LOW |
| (37)fb45 | glucan | 28.1400 | 1.39 | LOW |
| (37)3b10 | glucan | 28.6700 | 1.55 | LOW |
| (37)c333 | glucan | 28.6000 | 1.53 | LOW |
| (37)8ab5 | glucose | 31.2700 | 1.40 | LOW |
| (37)d647 | glucose | 31.8600 | 1.55 | LOW |
| (37)da91 | glucose | 31.7800 | 1.53 | LOW |
| (37)679f | xylan | 22.7900 | 1.18 | LOW |
| (37)2e71 | xylan | 23.5500 | 1.41 | LOW |
| (37)4504 | xylan | 23.3300 | 1.34 | LOW |
| (37)0930 | xylose | 25.8900 | 1.17 | LOW |
| (37)82b5 | xylose | 26.7600 | 1.41 | LOW |
| (37)9c26 | xylose | 26.5100 | 1.34 | LOW |
| (37)6df6 | lignin | 26.2300 | 1.03 | LOW |
| (37)99cb | lignin | 25.8000 | 1.18 | LOW |
| (31)749c | glucan | 30.6300 | 1.49 | LOW |
| (31)d8e4 | glucan | 31.0900 | 1.61 | LOW |
| (31)edc7 | glucan | 31.0600 | 1.60 | LOW |
| (31)eec3 | glucose | 34.0400 | 1.49 | LOW |
| (31)7265 | glucose | 34.5500 | 1.61 | LOW |
| (31)f0ca | glucose | 34.5200 | 1.61 | LOW |
| (31)8be1 | xylan | 16.5300 | 1.34 | LOW |
| (31)04ab | xylan | 16.6300 | 1.37 | LOW |
| (31)3fdc | xylan | 16.4200 | 1.31 | LOW |
| (31)9a9b | xylose | 18.7900 | 1.34 | LOW |
| (31)1e1b | xylose | 18.9000 | 1.37 | LOW |
| (31)52b7 | xylose | 18.6600 | 1.31 | LOW |
| (24)70e6 | glucan | 27.2200 | 1.12 | LOW |
| (24)42f3 | glucan | 26.9800 | 1.05 | LOW |
| (24)ec97 | glucose | 30.2400 | 1.12 | LOW |
| (24)fab3 | glucose | 29.9700 | 1.05 | LOW |
| (24)6b86 | xylan | 23.1800 | 1.29 | LOW |
| (24)1926 | xylan | 22.6400 | 1.13 | LOW |
| (24)0bc2 | xylan | 23.0300 | 1.25 | LOW |
| (24)ec7f | xylose | 26.3400 | 1.29 | LOW |
| (24)0b42 | xylose | 25.7300 | 1.13 | LOW |
| (24)7d8d | xylose | 26.1700 | 1.25 | LOW |
| (24)773e | lignin | 24.5700 | 1.62 | LOW |
| (24)a25e | lignin | 24.8000 | 1.53 | LOW |
| (24)ec0a | lignin | 24.7500 | 1.55 | LOW |
| (03)e36d | xylan | 16.9900 | 1.46 | LOW |
| (03)b32d | xylan | 17.3400 | 1.55 | LOW |
| (03)1f0b | xylan | 17.4600 | 1.58 | LOW |
| (03)d213 | xylose | 19.3100 | 1.46 | LOW |
| (03)8660 | xylose | 19.7000 | 1.54 | LOW |
| (03)e546 | xylose | 19.8400 | 1.58 | LOW |
| (03)677d | lignin | 19.4700 | 1.06 | LOW |
| (03)ad41 | lignin | 19.1500 | 1.19 | LOW |
| (56)d797 | glucan | 53.7500 | 1.04 | LOW |
| (56)b418 | glucose | 59.7200 | 1.04 | LOW |
| (56)ea26 | xylan | 3.1300 | 1.15 | LOW |
| (56)ea73 | xylose | 3.5600 | 1.15 | LOW |
| (56)40ab | lignin | 8.8500 | 1.02 | LOW |
| (82)8c1c | glucan | 10.2600 | 1.41 | LOW |
| (82)00ec | glucose | 11.4000 | 1.41 | LOW |
| (82)bdca | xylan | 20.7000 | 1.02 | LOW |
| (82)6771 | lignin | 48.9100 | 1.44 | LOW |
| (e7)4b15 | glucan | 12.4500 | 1.13 | LOW |
| (e7)7925 | glucose | 13.8300 | 1.13 | LOW |
| (e7)afea | xylan | 9.9400 | 1.01 | LOW |
| (e7)538c | xylose | 11.2900 | 1.01 | LOW |
| (e7)6d58 | lignin | 36.0000 | 1.15 | LOW |
| (c7)5eb1 | xylan | 15.2500 | 1.09 | LOW |
| (c7)749c | xylan | 15.2400 | 1.08 | LOW |
| (c7)71f6 | xylose | 17.3300 | 1.09 | LOW |
| (c7)548b | xylose | 17.3200 | 1.08 | LOW |
| (c7)f332 | lignin | 33.6200 | 1.06 | LOW |
| (c7)8b0b | lignin | 33.5700 | 1.07 | LOW |
| (c4)882a | glucan | 38.7800 | 1.08 | LOW |
| (c4)fccc | glucose | 43.0900 | 1.09 | LOW |
| (c4)5987 | xylan | 14.1100 | 1.06 | LOW |
| (c4)24f1 | xylose | 16.0400 | 1.05 | LOW |
| (c4)0589 | lignin | 36.2200 | 1.15 | LOW |

*...and 149 more observations. See `flagged_compositional.csv` for full data.*
