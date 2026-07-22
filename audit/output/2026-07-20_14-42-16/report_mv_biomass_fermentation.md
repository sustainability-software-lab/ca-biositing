# 🔍 Detailed Target Audit: `mv_biomass_fermentation` — 2026-07-20

**Flagged Observations:** 926 (136 HIGH, 8 MEDIUM, 782 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The data quality audit of the `mv_biomass_fermentation` dataset reveals significant systemic integrity issues, most notably a total lack of parameter identification for nearly one-third of the dataset and the presence of biophysically impossible negative values. The discovery of 123 duplicated rows and non-unique record IDs (2,996 rows vs. 2,870 unique IDs) suggests a failure in the data ingestion pipeline or an erroneous bulk-upload event. Furthermore, the dataset suffers from severe metadata stagnation, where fields such as 'qc_pass' and 'sample_date' are constants, rendering temporal analysis and quality control filtering impossible in the current state.

From a domain perspective, the high frequency of anomalies in olive-derived biomass (pomace and stems) and tomato pomace indicates potential feedstock-specific processing errors or sensor interference caused by the high phenolic content of these materials. The provider 'caterpillar' is associated with a high volume of flagged 'corn stover cobs' records, suggesting a potential calibration drift or systematic bias in their reporting of fermentation yields. Immediate remediation is required to populate missing parameter names and units, as the current 'observed_value' column lacks the necessary context for scientific interpretation.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| proco04-0008 | corn stover cobs | caterpillar | — |  | 5.1700 | 1.17 | LOW |
| proco04-101d | lab media | — | — |  | 112.5000 | 1.48 | LOW |
| proco04-1246 | corn stover cobs | caterpillar | — |  | 13.2600 | 1.29 | LOW |
| proco04-15e1 | corn stover cobs | caterpillar | — |  | 14.1000 | 1.54 | LOW |
| proco04-1758 | corn stover cobs | caterpillar | — |  | 25.9600 | 1.87 | LOW |
| proco04-20ff | corn stover cobs | caterpillar | — |  | 7.0000 | 1.05 | LOW |
| proco04-240e | lab media | — | — |  | 33.4900 | 1.07 | LOW |
| proco04-25b9 | corn stover cobs | caterpillar | — |  | 85.3900 | 1.36 | LOW |
| proco04-28af | lab media | — | — |  | 59.7300 | 1.07 | LOW |
| proco04-2c9b | corn stover cobs | caterpillar | — |  | 74.4400 | 1.66 | LOW |
| proco04-3321 | corn stover cobs | caterpillar | — |  | 84.0000 | 1.16 | LOW |
| proco04-3a23 | corn stover cobs | caterpillar | — |  | 13.2600 | 1.29 | LOW |
| proco04-3e6e | corn stover cobs | caterpillar | — |  | 48.2200 | 1.64 | LOW |
| proco04-45eb | corn stover cobs | caterpillar | — |  | 5.6000 | 1.04 | LOW |
| proco04-5878 | corn stover cobs | caterpillar | — |  | 29.9900 | 1.18 | LOW |
| proco04-8297 | corn stover cobs | caterpillar | — |  | 28.0400 | 1.08 | LOW |
| proco04-8404 | corn stover cobs | caterpillar | — |  | 93.8954 | 1.25 | LOW |
| proco04-91ee | corn stover cobs | caterpillar | — |  | 57.2368 | 2.24 | LOW |
| proco04-9e10 | corn stover cobs | caterpillar | — |  | 84.0000 | 1.16 | LOW |
| proco04-adef | corn stover cobs | caterpillar | — |  | 83.0000 | 1.41 | LOW |
| proco04-b178 | corn stover cobs | caterpillar | — |  | 71.8500 | 1.49 | LOW |
| proco04-b75d | corn stover cobs | caterpillar | — |  | 55.1600 | 1.35 | LOW |
| proco04-b8a7 | corn stover cobs | caterpillar | — |  | 26.2200 | 1.69 | LOW |
| proco04-c0e1 | lab media | — | — |  | 86.8421 | 1.56 | LOW |
| proco04-c7e2 | corn stover cobs | caterpillar | — |  | 14.1000 | 1.54 | LOW |
| proco04-cade | corn stover cobs | caterpillar | — |  | 5.1700 | 1.17 | LOW |
| proco04-cbfb | corn stover cobs | caterpillar | — |  | 91.7000 | 2.00 | LOW |
| proco04-d473 | corn stover cobs | caterpillar | — |  | 84.6900 | 1.16 | LOW |
| proco04-d610 | corn stover cobs | caterpillar | — |  | 30.2300 | 1.36 | LOW |
| proco04-de6b | corn stover cobs | caterpillar | — |  | 92.9257 | 1.02 | LOW |
| proco04-e2d6 | corn stover cobs | caterpillar | — |  | 33.9200 | 1.14 | LOW |
| proco04-eb1d | corn stover cobs | caterpillar | — |  | 54.7000 | 1.16 | LOW |
| proco04-f2eb | corn stover cobs | caterpillar | — |  | 33.7600 | 1.08 | LOW |
| proco04-fa08 | corn stover cobs | caterpillar | — |  | 5.6000 | 1.04 | LOW |
| proco07-0423 | olive pomace | excellent | — |  | 16.6498 | 1.05 | LOW |
| proco07-0603 | olive stems / leaves | excellent | — |  | 179.5900 | 1.06 | LOW |
| proco07-91b2 | olive pomace | excellent | — |  | 25.7300 | 1.09 | LOW |
| proco07-e319 | olive pomace | excellent | — |  | 129.8900 | 1.52 | LOW |
| proco08-0017 | olive stems / leaves | jaguar | — |  | 70.5060 | 2.07 | LOW |
| proco08-00d3 | olive stems / leaves | jaguar | — |  | 27.3289 | 1.52 | LOW |
| proco08-0532 | olive pomace | jaguar | — |  | 21.2200 | 2.16 | LOW |
| proco08-1644 | olive stems / leaves | jaguar | — |  | 42.5800 | 1.57 | LOW |
| proco08-1d97 | olive pomace | jaguar | — |  | 26.9700 | 1.29 | LOW |
| proco08-2aa8 | olive pomace | jaguar | — |  | 28.1700 | 1.48 | LOW |
| proco08-3fa6 | olive pomace | jaguar | — |  | 25.7700 | 1.10 | LOW |
| proco08-4196 | olive pomace | jaguar | — |  | 44.0000 | 2.16 | LOW |
| proco08-43f2 | olive stems / leaves | jaguar | — |  | 23.0200 | 2.08 | LOW |
| proco08-443a | olive pomace | jaguar | — |  | 48.1840 | 1.82 | LOW |
| proco08-46ed | olive stems / leaves | jaguar | — |  | 47.4900 | 2.03 | LOW |
| proco08-4872 | olive stems / leaves | jaguar | — |  | 45.0300 | 1.80 | LOW |
| proco08-5d02 | olive stems / leaves | jaguar | — |  | 21.0000 | 1.80 | LOW |
| proco08-5e1b | olive pomace | jaguar | — |  | 30.0000 | 1.11 | LOW |
| proco08-83cb | olive pomace | jaguar | — |  | 50.8200 | 2.05 | LOW |
| proco08-8745 | olive pomace | jaguar | — |  | 22.6500 | 2.40 | LOW |
| proco08-9a75 | olive pomace | jaguar | — |  | 19.4957 | 1.49 | LOW |
| proco08-a5a2 | olive pomace | jaguar | — |  | 45.5490 | 1.59 | LOW |
| proco08-ac0d | olive stems / leaves | jaguar | — |  | 67.0420 | 1.87 | LOW |
| proco08-bbd6 | olive stems / leaves | jaguar | — |  | 63.5790 | 1.68 | LOW |
| proco08-ccdb | olive stems / leaves | jaguar | — |  | 27.9726 | 1.59 | LOW |
| proco08-d991 | olive stems / leaves | jaguar | — |  | 26.6320 | 1.44 | LOW |
| proco08-e67f | olive pomace | jaguar | — |  | 18.8292 | 1.39 | LOW |
| proco08-f03b | olive stems / leaves | jaguar | — |  | 22.0100 | 1.94 | LOW |
| proco08-f9ab | olive pomace | jaguar | — |  | 19.7800 | 1.91 | LOW |
| proco09-007f | olive pomace | excellent | — |  | 19.8834 | 1.55 | LOW |
| proco09-0747 | olive stems / leaves | excellent | — |  | 40.0000 | 1.15 | LOW |
| proco09-1146 | olive stems / leaves | excellent | — |  | 37.0900 | 1.07 | LOW |
| proco09-131b | olive stems / leaves | excellent | — |  | 16.8100 | 1.22 | LOW |
| proco09-171a | olive pomace | excellent | — |  | 34.0300 | 2.43 | LOW |
| proco09-1d0c | olive stems / leaves | excellent | — |  | 52.7510 | 1.08 | LOW |
| proco09-5186 | olive pomace | excellent | — |  | 22.2985 | 1.93 | LOW |
| proco09-5e65 | olive pomace | excellent | — |  | 50.2490 | 2.00 | LOW |
| proco09-7570 | olive stems / leaves | excellent | — |  | 53.9040 | 1.14 | LOW |
| proco09-77e9 | olive pomace | excellent | — |  | 38.0000 | 1.71 | LOW |
| proco09-9385 | olive pomace | excellent | — |  | 62.0000 | 3.52 | MEDIUM |
| proco09-96c2 | olive pomace | excellent | — |  | 30.9800 | 1.94 | LOW |
| proco09-9950 | olive stems / leaves | excellent | — |  | 94.0000 | 3.84 | MEDIUM |
| proco09-a1a0 | olive pomace | excellent | — |  | 18.1900 | 1.65 | LOW |
| proco09-a36c | olive pomace | excellent | — |  | 17.7400 | 1.57 | LOW |
| proco09-a643 | olive stems / leaves | excellent | — |  | 16.7100 | 1.20 | LOW |
| proco09-a93e | olive pomace | excellent | — |  | 32.5100 | 2.18 | LOW |
| proco09-ab43 | olive pomace | excellent | — |  | 21.0973 | 1.74 | LOW |
| proco09-b002 | olive pomace | excellent | — |  | 52.2210 | 2.18 | LOW |
| proco09-b5ea | olive stems / leaves | excellent | — |  | 51.5980 | 1.01 | LOW |
| proco09-b966 | olive stems / leaves | excellent | — |  | 16.7600 | 1.21 | LOW |
| proco09-bc95 | olive pomace | excellent | — |  | 48.2760 | 1.83 | LOW |
| proco09-db95 | olive pomace | excellent | — |  | 17.2900 | 1.50 | LOW |
| proco10-14b8 | lab media | — | — |  | 3.8700 | 1.41 | LOW |
| proco10-458a | lab media | — | — |  | 28.5910 | 1.38 | LOW |
| proco10-ad86 | lab media | — | — |  | 26.9995 | 1.14 | LOW |
| proco10-c416 | lab media | — | — |  | 93.3850 | 1.18 | LOW |
| proco10-c5ec | lab media | — | — |  | 3.8737 | 1.41 | LOW |
| proco10-d4e2 | lab media | — | — |  | 65.4700 | 1.57 | LOW |
| proco10-e78e | lab media | — | — |  | 36.5800 | 1.66 | LOW |
| proco10-f7d2 | lab media | — | — |  | 96.0000 | 1.25 | LOW |
| proco11-0780 | olive pomace | jaguar | — |  | 0.0000 | 1.54 | LOW |
| proco11-14a5 | olive stems / leaves | jaguar | — |  | 0.0000 | 1.26 | LOW |
| proco11-2051 | olive pomace | jaguar | — |  | 36.5118 | 2.59 | LOW |
| proco11-2264 | olive pomace | jaguar | — |  | 18.0000 | 1.87 | LOW |
| proco11-23c2 | olive stems / leaves | jaguar | — |  | 0.0000 | 1.48 | LOW |
| proco11-2997 | olive stems / leaves | jaguar | — |  | 7.8900 | 1.00 | LOW |

*...and 826 more observations. See `flagged_mv_biomass_fermentation.csv` for full data.*
