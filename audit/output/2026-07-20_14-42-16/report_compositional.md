# 🔍 Detailed Target Audit: `compositional` — 2026-07-20

**Flagged Observations:** 245 (0 HIGH, 0 MEDIUM, 245 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The compositional analysis audit of agricultural biomass revealed a total of 245 low-severity flags out of 723 records. The data is characterized by a significant concentration of anomalies within almond-derived resources, specifically almond shells, hulls, and branches. These anomalies are primarily focused on structural carbohydrates (xylan/xylose and glucan/glucose) and lignin. A notable pattern is the simultaneous flagging of monomeric and polymeric forms (e.g., xylan and xylose), suggesting that the underlying variance stems from the initial hydrolysis stage or the conversion factors used to calculate anhydrous compositions.

Analyst xkang2@lbl.gov is associated with a large portion of the flagged records across multiple providers, including 'tiny' and 'humorous'. The consistent Z-scores (ranging from 1.0 to 1.6) across these records suggest a systematic laboratory bias or a slight departure from the global mean rather than random measurement errors. Furthermore, the dataset suffers from significant metadata gaps; the 'note' and 'analyst_name' columns are entirely empty, and the 'sample_date' and 'created_at' fields show zero variance, indicating a batch-upload process that may have stripped vital context regarding sample preparation or equipment calibration.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| (03)1f0b | almond hulls | tiny | — | xylan | 17.4600 | 1.58 | LOW |
| (03)677d | almond hulls | tiny | — | lignin | 19.4700 | 1.06 | LOW |
| (03)8660 | almond hulls | tiny | — | xylose | 19.7000 | 1.54 | LOW |
| (03)ad41 | almond hulls | tiny | — | lignin | 19.1500 | 1.19 | LOW |
| (03)b32d | almond hulls | tiny | — | xylan | 17.3400 | 1.55 | LOW |
| (03)d213 | almond hulls | tiny | — | xylose | 19.3100 | 1.46 | LOW |
| (03)e36d | almond hulls | tiny | — | xylan | 16.9900 | 1.46 | LOW |
| (03)e546 | almond hulls | tiny | — | xylose | 19.8400 | 1.58 | LOW |
| (04)68e4 | almond shells | capstan | — | xylan | 15.1700 | 1.14 | LOW |
| (04)c1d7 | almond shells | capstan | — | xylose | 17.2400 | 1.14 | LOW |
| (13)29f0 | almond shells | humorous | — | xylan | 15.5200 | 1.03 | LOW |
| (13)2c76 | almond shells | humorous | — | xylose | 16.4100 | 1.36 | LOW |
| (13)6f70 | almond shells | humorous | — | xylose | 17.6300 | 1.03 | LOW |
| (13)8405 | almond shells | humorous | — | glucose | 20.7900 | 1.39 | LOW |
| (13)aaf9 | almond shells | humorous | — | xylan | 14.4400 | 1.36 | LOW |
| (13)b6b6 | almond shells | humorous | — | glucan | 18.7100 | 1.39 | LOW |
| (13)ce37 | almond shells | humorous | — | glucose | 22.2600 | 1.00 | LOW |
| (15)0b07 | almond hulls | humorous | — | glucose | 23.5600 | 1.03 | LOW |
| (15)3f87 | almond hulls | humorous | — | glucose | 23.2700 | 1.10 | LOW |
| (15)797a | walnut shells | cutaway | — | glucan | 11.8400 | 1.12 | LOW |
| (15)849b | almond hulls | humorous | — | glucan | 20.9400 | 1.10 | LOW |
| (15)95c9 | walnut shells | cutaway | — | lignin | 50.7300 | 1.26 | LOW |
| (15)ab15 | walnut shells | cutaway | — | glucose | 13.1600 | 1.12 | LOW |
| (15)c93b | almond hulls | humorous | — | glucan | 21.2000 | 1.03 | LOW |
| (15)e1e0 | walnut shells | cutaway | — | xylan | 19.8300 | 1.73 | LOW |
| (24)0b42 | almond shells | tiny | — | xylose | 25.7300 | 1.13 | LOW |
| (24)0bc2 | almond shells | tiny | — | xylan | 23.0300 | 1.25 | LOW |
| (24)1926 | almond shells | tiny | — | xylan | 22.6400 | 1.13 | LOW |
| (24)42f3 | almond shells | tiny | — | glucan | 26.9800 | 1.05 | LOW |
| (24)6b86 | almond shells | tiny | — | xylan | 23.1800 | 1.29 | LOW |
| (24)70e6 | almond shells | tiny | — | glucan | 27.2200 | 1.12 | LOW |
| (24)773e | almond shells | tiny | — | lignin | 24.5700 | 1.62 | LOW |
| (24)7d8d | almond shells | tiny | — | xylose | 26.1700 | 1.25 | LOW |
| (24)a25e | almond shells | tiny | — | lignin | 24.8000 | 1.53 | LOW |
| (24)ec0a | almond shells | tiny | — | lignin | 24.7500 | 1.55 | LOW |
| (24)ec7f | almond shells | tiny | — | xylose | 26.3400 | 1.29 | LOW |
| (24)ec97 | almond shells | tiny | — | glucose | 30.2400 | 1.12 | LOW |
| (24)fab3 | almond shells | tiny | — | glucose | 29.9700 | 1.05 | LOW |
| (28)2429 | tomato pomace | riverstone | — | xylose | 12.5600 | 1.49 | LOW |
| (28)847b | tomato pomace | riverstone | — | xylan | 11.0600 | 1.49 | LOW |
| (28)8908 | corn stover cobs | caterpillar | — | lignin | 15.9700 | 1.05 | LOW |
| (28)97be | corn stover cobs | caterpillar | — | glucose | 37.8100 | 1.10 | LOW |
| (28)9a1d | corn stover cobs | caterpillar | — | glucan | 34.0300 | 1.09 | LOW |
| (28)a3d2 | tomato pomace | riverstone | — | xylose | 12.8000 | 1.70 | LOW |
| (28)a602 | tomato pomace | riverstone | — | glucan | 11.7100 | 1.32 | LOW |
| (28)a764 | corn stover cobs | caterpillar | — | xylose | 28.5200 | 1.13 | LOW |
| (28)c6e6 | corn stover cobs | caterpillar | — | xylan | 25.0900 | 1.12 | LOW |
| (28)cfc4 | tomato pomace | riverstone | — | glucose | 13.0100 | 1.32 | LOW |
| (28)f0fe | tomato pomace | riverstone | — | xylan | 11.2600 | 1.69 | LOW |
| (31)04ab | almond hulls | vibrant | — | xylan | 16.6300 | 1.37 | LOW |
| (31)1e1b | almond hulls | vibrant | — | xylose | 18.9000 | 1.37 | LOW |
| (31)3fdc | almond hulls | vibrant | — | xylan | 16.4200 | 1.31 | LOW |
| (31)52b7 | almond hulls | vibrant | — | xylose | 18.6600 | 1.31 | LOW |
| (31)7265 | almond hulls | vibrant | — | glucose | 34.5500 | 1.61 | LOW |
| (31)749c | almond hulls | vibrant | — | glucan | 30.6300 | 1.49 | LOW |
| (31)8be1 | almond hulls | vibrant | — | xylan | 16.5300 | 1.34 | LOW |
| (31)9a9b | almond hulls | vibrant | — | xylose | 18.7900 | 1.34 | LOW |
| (31)d8e4 | almond hulls | vibrant | — | glucan | 31.0900 | 1.61 | LOW |
| (31)edc7 | almond hulls | vibrant | — | glucan | 31.0600 | 1.60 | LOW |
| (31)eec3 | almond hulls | vibrant | — | glucose | 34.0400 | 1.49 | LOW |
| (31)f0ca | almond hulls | vibrant | — | glucose | 34.5200 | 1.61 | LOW |
| (37)0930 | almond shells | vibrant | — | xylose | 25.8900 | 1.17 | LOW |
| (37)2e71 | almond shells | vibrant | — | xylan | 23.5500 | 1.41 | LOW |
| (37)3b10 | almond shells | vibrant | — | glucan | 28.6700 | 1.55 | LOW |
| (37)4504 | almond shells | vibrant | — | xylan | 23.3300 | 1.34 | LOW |
| (37)679f | almond shells | vibrant | — | xylan | 22.7900 | 1.18 | LOW |
| (37)6df6 | almond shells | vibrant | — | lignin | 26.2300 | 1.03 | LOW |
| (37)82b5 | almond shells | vibrant | — | xylose | 26.7600 | 1.41 | LOW |
| (37)8ab5 | almond shells | vibrant | — | glucose | 31.2700 | 1.40 | LOW |
| (37)99cb | almond shells | vibrant | — | lignin | 25.8000 | 1.18 | LOW |
| (37)9c26 | almond shells | vibrant | — | xylose | 26.5100 | 1.34 | LOW |
| (37)c333 | almond shells | vibrant | — | glucan | 28.6000 | 1.53 | LOW |
| (37)d647 | almond shells | vibrant | — | glucose | 31.8600 | 1.55 | LOW |
| (37)da91 | almond shells | vibrant | — | glucose | 31.7800 | 1.53 | LOW |
| (37)fb45 | almond shells | vibrant | — | glucan | 28.1400 | 1.39 | LOW |
| (42)0211 | rice straw | possessive | — | glucose | 33.4300 | 1.45 | LOW |
| (42)0654 | rice straw | possessive | — | xylose | 17.7000 | 1.23 | LOW |
| (42)446d | rice straw | possessive | — | xylan | 15.5800 | 1.22 | LOW |
| (42)7a67 | rice straw | possessive | — | arabinose | 2.5700 | 1.15 | LOW |
| (42)8729 | rice straw | possessive | — | glucan | 30.0900 | 1.45 | LOW |
| (42)cbb9 | rice straw | possessive | — | arabinan | 2.2700 | 1.14 | LOW |
| (4e)e137 | grape pomace | ebony | — | glucan | 5.5700 | 1.28 | LOW |
| (4e)e140 | grape pomace | ebony | — | glucose | 6.1900 | 1.29 | LOW |
| (4e)e143 | grape pomace | ebony | — | xylan | 2.9200 | 1.53 | LOW |
| (4e)e146 | grape pomace | ebony | — | xylose | 3.3200 | 1.54 | LOW |
| (4e)e151 | grape pomace | ebony | — | lignin | 47.8400 | 1.50 | LOW |
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
| (71)0047 | almond shells | humorous | — | lignin | 33.9700 | 1.71 | LOW |
| (71)0d9d | almond shells | humorous | — | lignin | 32.5700 | 1.21 | LOW |
| (71)23e9 | almond shells | humorous | — | lignin | 34.3500 | 1.84 | LOW |
| (71)3ea0 | almond shells | humorous | — | xylose | 13.8700 | 2.04 | LOW |

*...and 145 more observations. See `flagged_compositional.csv` for full data.*
