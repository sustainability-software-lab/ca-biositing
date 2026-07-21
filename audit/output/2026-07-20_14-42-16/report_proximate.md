# 🔍 Detailed Target Audit: `proximate` — 2026-07-20

**Flagged Observations:** 271 (0 HIGH, 1 MEDIUM, 270 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The proximate analysis dataset for agricultural biomass (912 records) demonstrates high internal consistency regarding the stoichiometric relationship between moisture and total solids. The majority of flagged observations (270 out of 271) are categorized as low severity, primarily reflecting the natural biological variance inherent in comparing disparate feedstock types—ranging from high-moisture tomato pomace and pistachio hulls to low-moisture woody residues like almond shells and spent oak chips. Z-score anomalies are largely driven by these distinct feedstock profiles rather than analytical failures.

Analytical attribution is partially maintained through the 'analyst_email' field, with xkang2@lbl.gov overseeing a significant portion of the flagged records, particularly for almond hulls and grape pomace. However, the 'analyst_name' field is 100% unpopulated across the dataset, and 'sample_date' values are missing for all records. Provider-specific patterns are evident, notably with provider 'humorous' delivering almond shells with higher-than-average moisture content (approx. 19%), and provider 'tripod' submitting high-moisture pistachio residues. These clusters suggest systematic differences in processing or storage conditions at the provider level.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| (03)b1b0 | almond hulls | tiny | — | moisture | 15.4400 | 1.05 | LOW |
| (03)ca72 | almond hulls | tiny | — | total solids | 84.5600 | 1.05 | LOW |
| (04)3ab3 | spent oak chips | maplewood | — | ash solids | 0.5200 | 1.31 | LOW |
| (04)4ab5 | spent oak chips | maplewood | — | moisture | 7.1900 | 1.01 | LOW |
| (04)93fb | spent oak chips | maplewood | — | total solids | 92.8100 | 1.01 | LOW |
| (04)986f | spent oak chips | maplewood | — | ash solids | 0.6600 | 1.51 | LOW |
| (04)f5c2 | almond shells | capstan | — | volatile solids | 87.8600 | 1.10 | LOW |
| (11)2322 | pistachio hulls | tripod | — | total solids | 19.6600 | 1.32 | LOW |
| (11)a4db | pistachio hulls | tripod | — | moisture | 80.3400 | 1.32 | LOW |
| (11)f212 | pistachio hulls | tripod | — | volatile solids | 14.9700 | 1.67 | LOW |
| (13)0c41 | grape pomace | ebony | — | moisture | 64.9800 | 1.31 | LOW |
| (13)124d | almond shells | humorous | — | ash solids | 3.6400 | 1.07 | LOW |
| (13)12b9 | almond shells | humorous | — | moisture | 19.0600 | 2.21 | LOW |
| (13)1443 | almond shells | humorous | — | volatile solids | 77.1800 | 2.09 | LOW |
| (13)1b04 | almond shells | humorous | — | moisture | 19.0000 | 2.20 | LOW |
| (13)2169 | almond shells | humorous | — | moisture | 19.0500 | 2.21 | LOW |
| (13)61f0 | grape pomace | ebony | — | total solids | 35.0200 | 1.31 | LOW |
| (13)6c40 | almond shells | humorous | — | ash solids | 3.7100 | 1.01 | LOW |
| (13)710c | almond shells | humorous | — | volatile solids | 77.3100 | 2.05 | LOW |
| (13)7fbd | almond shells | humorous | — | total solids | 80.9400 | 2.21 | LOW |
| (13)9fd0 | grape pomace | ebony | — | volatile solids | 33.1000 | 1.10 | LOW |
| (13)bae5 | almond shells | humorous | — | total solids | 80.9500 | 2.21 | LOW |
| (13)dda4 | almond shells | humorous | — | total solids | 81.0000 | 2.20 | LOW |
| (13)df67 | grape pomace | ebony | — | volatile solids | 30.8900 | 1.52 | LOW |
| (13)f8f6 | almond shells | humorous | — | volatile solids | 77.2900 | 2.06 | LOW |
| (14)bd40 | peach pomace | rushes | — | ash solids | 0.3300 | 1.15 | LOW |
| (14)e88d | peach pomace | rushes | — | total solids | 2.9200 | 1.10 | LOW |
| (14)eb17 | peach pomace | rushes | — | volatile solids | 2.6100 | 1.15 | LOW |
| (14)ff20 | peach pomace | rushes | — | moisture | 97.0800 | 1.10 | LOW |
| (15)19f2 | almond hulls | humorous | — | total solids | 84.5600 | 1.05 | LOW |
| (15)2ca0 | walnut shells | cutaway | — | ash solids | 1.0600 | 1.32 | LOW |
| (15)77aa | walnut shells | cutaway | — | volatile solids | 88.9100 | 1.10 | LOW |
| (15)9820 | olive stems / leaves | excellent | — | moisture | 46.1700 | 1.15 | LOW |
| (15)9a81 | almond hulls | humorous | — | total solids | 84.5100 | 1.09 | LOW |
| (15)9e63 | almond hulls | humorous | — | moisture | 15.4400 | 1.05 | LOW |
| (15)bdac | walnut shells | cutaway | — | ash solids | 1.0700 | 1.21 | LOW |
| (15)dec9 | olive stems / leaves | excellent | — | volatile solids | 51.3200 | 1.14 | LOW |
| (15)e432 | olive stems / leaves | excellent | — | total solids | 53.8300 | 1.15 | LOW |
| (15)efa4 | almond hulls | humorous | — | moisture | 15.4900 | 1.09 | LOW |
| (15)f3b8 | olive stems / leaves | excellent | — | ash solids | 2.1500 | 1.01 | LOW |
| (23)3d5d | peach screening waste | rushes | — | volatile solids | 2.2200 | 1.01 | LOW |
| (23)5b30 | peach screening waste | rushes | — | ash solids | 0.2600 | 1.15 | LOW |
| (23)6951 | peach screening waste | rushes | — | moisture | 97.0600 | 1.01 | LOW |
| (23)77d7 | peach screening waste | rushes | — | total solids | 2.9400 | 1.01 | LOW |
| (24)7d51 | almond shells | tiny | — | ash solids | 6.8100 | 1.38 | LOW |
| (24)bbda | almond shells | tiny | — | ash solids | 6.8300 | 1.39 | LOW |
| (24)ea69 | almond shells | tiny | — | ash solids | 7.3200 | 1.77 | LOW |
| (27)13cb | almond hulls | tiny | — | ash solids | 13.3700 | 3.29 | MEDIUM |
| (27)8c1d | almond hulls | tiny | — | volatile solids | 71.4400 | 2.87 | LOW |
| (28)17f4 | corn stover cobs | caterpillar | — | volatile solids | 84.1900 | 1.11 | LOW |
| (28)ec2a | corn stover cobs | caterpillar | — | ash solids | 10.9200 | 1.11 | LOW |
| (31)0a4b | grape stem | maplewood | — | ash solids | 3.1800 | 1.29 | LOW |
| (31)2091 | grape stem | maplewood | — | moisture | 70.3700 | 1.44 | LOW |
| (31)52a8 | almond hulls | vibrant | — | ash solids | 5.6000 | 1.22 | LOW |
| (31)797b | almond hulls | vibrant | — | volatile solids | 80.9100 | 1.07 | LOW |
| (31)9831 | grape stem | maplewood | — | volatile solids | 26.7100 | 1.43 | LOW |
| (31)ae33 | grape stem | maplewood | — | total solids | 29.6300 | 1.44 | LOW |
| (31)d70c | almond hulls | vibrant | — | ash solids | 5.4300 | 1.32 | LOW |
| (35)0520 | grape vine prunings | boatswain | — | volatile solids | 61.1100 | 1.09 | LOW |
| (35)4da8 | grape vine prunings | boatswain | — | moisture | 36.1600 | 1.12 | LOW |
| (35)7a98 | grape vine prunings | boatswain | — | ash solids | 2.6100 | 1.13 | LOW |
| (35)f6cd | grape vine prunings | boatswain | — | total solids | 63.8400 | 1.12 | LOW |
| (42)729d | rice straw | possessive | — | moisture | 6.7500 | 1.15 | LOW |
| (42)a5e2 | rice straw | possessive | — | ash solids | 11.8700 | 1.30 | LOW |
| (42)a6fe | rice straw | possessive | — | ash solids | 11.9700 | 1.11 | LOW |
| (42)c1de | rice straw | possessive | — | volatile solids | 81.2400 | 1.15 | LOW |
| (42)c366 | rice straw | possessive | — | total solids | 93.2500 | 1.15 | LOW |
| (53)9e2f | pistachio hulls | stuntman | — | volatile solids | 11.1500 | 1.25 | LOW |
| (53)b829 | pistachio hulls | stuntman | — | total solids | 12.2700 | 1.18 | LOW |
| (53)fc52 | pistachio hulls | stuntman | — | moisture | 87.7300 | 1.18 | LOW |
| (55)1963 | tomato pomace | pinecrest | — | ash solids | 0.8500 | 1.09 | LOW |
| (55)1e0d | tomato pomace | pinecrest | — | total solids | 19.2600 | 1.23 | LOW |
| (55)8c83 | tomato pomace | pinecrest | — | moisture | 80.7500 | 1.23 | LOW |
| (55)9fb3 | tomato pomace | pinecrest | — | total solids | 19.2500 | 1.23 | LOW |
| (55)a0cd | tomato pomace | pinecrest | — | moisture | 80.7400 | 1.23 | LOW |
| (55)ac67 | tomato pomace | pinecrest | — | volatile solids | 18.3000 | 1.23 | LOW |
| (55)afbf | tomato pomace | pinecrest | — | ash solids | 0.7600 | 1.60 | LOW |
| (55)bfa7 | tomato pomace | pinecrest | — | volatile solids | 18.4000 | 1.22 | LOW |
| (55)c24c | tomato pomace | pinecrest | — | moisture | 80.9300 | 1.25 | LOW |
| (55)d348 | tomato pomace | pinecrest | — | volatile solids | 18.3100 | 1.23 | LOW |
| (55)edd2 | tomato pomace | pinecrest | — | total solids | 19.0700 | 1.25 | LOW |
| (56)a5bd | pistachio stems & leaves | tripod | — | total solids | 40.6500 | 1.15 | LOW |
| (56)b3fe | pistachio stems & leaves | tripod | — | ash solids | 5.3900 | 1.02 | LOW |
| (56)e360 | pistachio stems & leaves | tripod | — | moisture | 59.3500 | 1.15 | LOW |
| (56)f5d2 | pistachio stems & leaves | tripod | — | volatile solids | 33.4300 | 1.06 | LOW |
| (5b)35b8 | corn stover stalks | caterpillar | — | total solids | 87.3000 | 1.15 | LOW |
| (5b)4d95 | corn stover stalks | caterpillar | — | moisture | 12.7000 | 1.15 | LOW |
| (5b)5997 | corn stover stalks | caterpillar | — | ash solids | 5.0600 | 1.05 | LOW |
| (5b)ace1 | corn stover stalks | caterpillar | — | volatile solids | 82.0900 | 1.15 | LOW |
| (63)074e | lees | maplewood | — | ash solids | 3.5200 | 1.15 | LOW |
| (63)20ff | lees | maplewood | — | total solids | 11.7700 | 1.13 | LOW |
| (63)5e8c | lees | maplewood | — | volatile solids | 8.2400 | 1.15 | LOW |
| (63)f7da | lees | maplewood | — | moisture | 88.2300 | 1.13 | LOW |
| (6b)0caf | walnut tree sticks | badger | — | total solids | 66.4700 | 1.07 | LOW |
| (6b)43a2 | walnut tree sticks | badger | — | moisture | 32.2500 | 1.50 | LOW |
| (6b)4a5c | walnut tree sticks | badger | — | volatile solids | 64.9300 | 1.49 | LOW |
| (6b)8b47 | walnut tree sticks | badger | — | volatile solids | 63.8700 | 1.09 | LOW |
| (6b)a75e | walnut tree sticks | badger | — | total solids | 67.7500 | 1.50 | LOW |
| (6b)a9b2 | walnut tree sticks | badger | — | volatile solids | 63.9600 | 1.13 | LOW |
| (6b)dcb2 | walnut tree sticks | badger | — | moisture | 33.5300 | 1.07 | LOW |

*...and 171 more observations. See `flagged_proximate.csv` for full data.*
