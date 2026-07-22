# 🔍 Detailed Target Audit: `mv_biomass_composition_extended` — 2026-07-20

**Flagged Observations:** 257 (0 HIGH, 0 MEDIUM, 257 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The audit of the `mv_biomass_composition_extended` dataset reveals a systematically maintained but metadata-deficient collection of agricultural biomass composition records. While the dataset contains 813 records covering 26 distinct resource types, there is a total absence of 'harvest_date' information, and temporal metadata ('sample_date' and 'created_at') is currently static, which limits the ability to analyze seasonal variations in biomass quality. The 257 flagged observations are exclusively of 'LOW' severity, suggesting they represent statistical outliers or natural biological variance rather than catastrophic data entry errors.

The primary anomalies are concentrated in structural carbohydrate and lignin profiles for almond-derived biomass (hulls, shells, and branches) and sargassum. Specific providers, such as 'tiny', 'capstan', and 'hairpin', show recurring patterns of elevated glucose and xylan concentrations. The strong correlation between glucan/glucose and xylan/xylose flags across these providers suggests that the anomalies may stem from specific hydrolysis efficiency or analytical calibration differences rather than isolated sample contamination. Recommendation focuses on backfilling harvest metadata and performing a cross-lab calibration check for the identified providers.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| (03)8c53 | almond hulls | tiny | — | glucose | 31.2700 | 1.14 | LOW |
| (03)9a1e | almond hulls | tiny | — | lignin | 19.8600 | 1.03 | LOW |
| (03)d213 | almond hulls | tiny | — | xylose | 19.3100 | 1.12 | LOW |
| (03)e36d | almond hulls | tiny | — | xylan | 16.9900 | 1.12 | LOW |
| (03)f1df | almond hulls | tiny | — | glucan | 28.1500 | 1.14 | LOW |
| (04)0340 | almond shells | capstan | — | lignin | 30.0200 | 1.11 | LOW |
| (04)5f38 | almond shells | capstan | — | glucan | 20.1800 | 1.10 | LOW |
| (04)68e4 | almond shells | capstan | — | xylan | 15.1700 | 1.15 | LOW |
| (04)a7a4 | almond shells | capstan | — | glucose | 22.4200 | 1.10 | LOW |
| (04)c1d7 | almond shells | capstan | — | xylose | 17.2400 | 1.15 | LOW |
| (0d)4993 | sargassum | hairpin | — | glucan | 10.1700 | 1.12 | LOW |
| (0d)4996 | sargassum | hairpin | — | glucose | 11.3000 | 1.13 | LOW |
| (0d)4999 | sargassum | hairpin | — | xylan | 4.8100 | 1.11 | LOW |
| (0d)5002 | sargassum | hairpin | — | xylose | 5.4600 | 1.11 | LOW |
| (0d)5006 | sargassum | hairpin | — | lignin | 26.3900 | 1.08 | LOW |
| (13)9bb5 | almond shells | humorous | — | xylan | 19.5700 | 1.00 | LOW |
| (15)1ee2 | almond hulls | humorous | — | xylan | 10.2300 | 1.09 | LOW |
| (15)65e3 | almond hulls | humorous | — | xylan | 10.8100 | 1.40 | LOW |
| (15)797a | walnut shells | cutaway | — | glucan | 11.8400 | 1.14 | LOW |
| (15)93e3 | walnut shells | cutaway | — | xylose | 22.5400 | 1.08 | LOW |
| (15)95c9 | walnut shells | cutaway | — | lignin | 50.7300 | 1.13 | LOW |
| (15)962e | almond hulls | humorous | — | xylose | 11.6300 | 1.09 | LOW |
| (15)968f | almond hulls | humorous | — | xylose | 12.2800 | 1.40 | LOW |
| (15)ab15 | walnut shells | cutaway | — | glucose | 13.1600 | 1.14 | LOW |
| (15)d283 | almond hulls | humorous | — | xylose | 11.6700 | 1.11 | LOW |
| (15)d98b | almond hulls | humorous | — | xylan | 10.2700 | 1.11 | LOW |
| (15)e1e0 | walnut shells | cutaway | — | xylan | 19.8300 | 1.09 | LOW |
| (24)6b86 | almond shells | tiny | — | xylan | 23.1800 | 1.02 | LOW |
| (24)70e6 | almond shells | tiny | — | glucan | 27.2200 | 1.03 | LOW |
| (24)ec7f | almond shells | tiny | — | xylose | 26.3400 | 1.02 | LOW |
| (24)ec97 | almond shells | tiny | — | glucose | 30.2400 | 1.03 | LOW |
| (28)7919 | tomato pomace | riverstone | — | xylose | 10.6400 | 1.15 | LOW |
| (28)8908 | corn stover cobs | caterpillar | — | lignin | 15.9700 | 1.05 | LOW |
| (28)8c33 | tomato pomace | riverstone | — | xylan | 9.3600 | 1.15 | LOW |
| (28)97be | corn stover cobs | caterpillar | — | glucose | 37.8100 | 1.10 | LOW |
| (28)9a1d | corn stover cobs | caterpillar | — | glucan | 34.0300 | 1.09 | LOW |
| (28)a602 | tomato pomace | riverstone | — | glucan | 11.7100 | 1.15 | LOW |
| (28)a764 | corn stover cobs | caterpillar | — | xylose | 28.5200 | 1.13 | LOW |
| (28)c6e6 | corn stover cobs | caterpillar | — | xylan | 25.0900 | 1.12 | LOW |
| (28)cfc4 | tomato pomace | riverstone | — | glucose | 13.0100 | 1.15 | LOW |
| (28)e48e | tomato pomace | riverstone | — | lignin+ | 39.7600 | 1.07 | LOW |
| (31)3fdc | almond hulls | vibrant | — | xylan | 16.4200 | 1.02 | LOW |
| (31)504a | almond hulls | vibrant | — | lignin | 20.9900 | 1.15 | LOW |
| (31)52b7 | almond hulls | vibrant | — | xylose | 18.6600 | 1.03 | LOW |
| (31)749c | almond hulls | vibrant | — | glucan | 30.6300 | 1.15 | LOW |
| (31)eec3 | almond hulls | vibrant | — | glucose | 34.0400 | 1.15 | LOW |
| (37)0930 | almond shells | vibrant | — | xylose | 25.8900 | 1.11 | LOW |
| (37)4b35 | almond shells | vibrant | — | lignin | 26.7600 | 1.03 | LOW |
| (37)679f | almond shells | vibrant | — | xylan | 22.7900 | 1.11 | LOW |
| (37)8ab5 | almond shells | vibrant | — | glucose | 31.2700 | 1.15 | LOW |
| (37)fb45 | almond shells | vibrant | — | glucan | 28.1400 | 1.15 | LOW |
| (3c)1efb | alfalfa | possessive | — | glucose | 27.1000 | 1.44 | LOW |
| (3c)3131 | alfalfa | possessive | — | glucan | 25.1000 | 1.03 | LOW |
| (3c)3fff | alfalfa | possessive | — | glucose | 27.8900 | 1.03 | LOW |
| (3c)4cb4 | alfalfa | possessive | — | glucan | 24.3900 | 1.44 | LOW |
| (3c)594e | alfalfa | possessive | — | xylan | 11.3200 | 1.16 | LOW |
| (3c)6726 | alfalfa | possessive | — | xylose | 12.8800 | 1.14 | LOW |
| (3c)933c | alfalfa | possessive | — | glucose | 27.3800 | 1.30 | LOW |
| (3c)c6b9 | alfalfa | possessive | — | xylan | 11.3300 | 1.14 | LOW |
| (3c)d0b2 | alfalfa | possessive | — | glucan | 24.6400 | 1.30 | LOW |
| (3c)fc9b | alfalfa | possessive | — | xylose | 12.8600 | 1.16 | LOW |
| (42)0211 | rice straw | possessive | — | glucose | 33.4300 | 1.45 | LOW |
| (42)0654 | rice straw | possessive | — | xylose | 17.7000 | 1.23 | LOW |
| (42)446d | rice straw | possessive | — | xylan | 15.5800 | 1.22 | LOW |
| (42)7a67 | rice straw | possessive | — | arabinose | 2.5700 | 1.15 | LOW |
| (42)8729 | rice straw | possessive | — | glucan | 30.0900 | 1.45 | LOW |
| (42)cbb9 | rice straw | possessive | — | arabinan | 2.2700 | 1.14 | LOW |
| (4c)0e12 | almond branches | humorous | — | glucan | 22.4100 | 1.09 | LOW |
| (4c)12e4 | almond branches | humorous | — | xylose | 14.7600 | 1.12 | LOW |
| (4c)6cf6 | almond branches | humorous | — | lignin | 38.5200 | 1.08 | LOW |
| (4c)c715 | almond branches | humorous | — | glucose | 24.9000 | 1.09 | LOW |
| (4c)ddb6 | almond branches | humorous | — | xylan | 12.9900 | 1.12 | LOW |
| (4d)2619 | walnut tree sticks | energetic | — | xylan | 13.0800 | 1.11 | LOW |
| (4d)3358 | walnut tree sticks | energetic | — | xylose | 14.8700 | 1.12 | LOW |
| (4d)86ca | walnut tree sticks | energetic | — | glucose | 26.6500 | 1.09 | LOW |
| (4d)8f9f | walnut tree sticks | energetic | — | glucan | 23.9800 | 1.09 | LOW |
| (4d)a3be | walnut tree sticks | energetic | — | lignin | 31.8800 | 1.15 | LOW |
| (4e)e137 | grape pomace | ebony | — | glucan | 5.5700 | 1.15 | LOW |
| (4e)e140 | grape pomace | ebony | — | glucose | 6.1900 | 1.15 | LOW |
| (4e)e143 | grape pomace | ebony | — | xylan | 2.9200 | 1.12 | LOW |
| (4e)e146 | grape pomace | ebony | — | xylose | 3.3200 | 1.12 | LOW |
| (4e)e149 | grape pomace | ebony | — | lignin | 49.7100 | 1.09 | LOW |
| (56)40ab | sweet potato culls | tackle | — | lignin | 8.8500 | 1.02 | LOW |
| (56)b418 | sweet potato culls | tackle | — | glucose | 59.7200 | 1.04 | LOW |
| (56)d797 | sweet potato culls | tackle | — | glucan | 53.7500 | 1.04 | LOW |
| (56)ea26 | sweet potato culls | tackle | — | xylan | 3.1300 | 1.15 | LOW |
| (56)ea73 | sweet potato culls | tackle | — | xylose | 3.5600 | 1.15 | LOW |
| (5b)3885 | corn stover stalks | caterpillar | — | lignin | 21.9500 | 1.08 | LOW |
| (5b)58d8 | corn stover stalks | caterpillar | — | glucose | 45.3300 | 1.15 | LOW |
| (5b)9d19 | corn stover stalks | caterpillar | — | glucan | 40.8000 | 1.15 | LOW |
| (5b)cb5c | corn stover stalks | caterpillar | — | xylan | 19.5100 | 1.09 | LOW |
| (5b)de58 | corn stover stalks | caterpillar | — | xylose | 22.1700 | 1.10 | LOW |
| (5c)335d | grape stem | maplewood | — | xylose | 9.1800 | 1.15 | LOW |
| (5c)76f6 | grape stem | maplewood | — | glucose | 27.3700 | 1.13 | LOW |
| (5c)7ce2 | grape stem | maplewood | — | glucan | 24.6300 | 1.13 | LOW |
| (5c)94a8 | grape stem | maplewood | — | xylan | 8.0800 | 1.14 | LOW |
| (5c)ad73 | grape stem | maplewood | — | lignin | 26.8200 | 1.14 | LOW |
| (62)418e | wheat straw | possessive | — | arabinose | 2.1800 | 1.14 | LOW |
| (62)50f3 | wheat straw | possessive | — | arabinan | 1.9200 | 1.14 | LOW |
| (62)5ab6 | wheat straw | possessive | — | xylose | 22.0500 | 1.15 | LOW |

*...and 157 more observations. See `flagged_mv_biomass_composition_extended.csv` for full data.*
