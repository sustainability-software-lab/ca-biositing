# 🔍 Detailed Target Audit: `pretreatment` — 2026-07-20

**Flagged Observations:** 232 (0 HIGH, 2 MEDIUM, 230 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The data quality audit for the 'pretreatment' dataset reveals a substantial number of low-severity anomalies, with approximately 31% of the records flagged. The primary parameters of concern are glucose and xylose yields, which exhibit significant variance across different biomass resources. While the majority of anomalies are characterized by low Z-scores (1.0–1.5), the presence of maximum values reaching 118.0 suggests potential calculation errors or calibration shifts, as yields exceeding 100% of the theoretical maximum are physically impossible in standard biomass pretreatment contexts.

A significant structural deficiency in the dataset is the complete absence of qualitative metadata. The 'note' and 'analyst_name' columns are entirely unpopulated across all 741 records. While 'analyst_email' correctly attributes the work to akrishnamoorthy@lbl.gov, the lack of contextual notes makes it difficult to distinguish between legitimate experimental variation (e.g., optimized pretreatment conditions) and measurement error. Furthermore, the dataset shows a strong clustering of anomalies by provider (e.g., 'maplewood', 'energetic', 'caterpillar'), suggesting that specific batches or source locations are driving the observed statistical deviations.

Immediate attention is required to validate yield calculation formulas and calibrate the HPLC or equivalent instruments used for sugar quantification, particularly for records showing yields near or above theoretical limits. The consistency of results within provider groups like 'caterpillar' and 'maplewood' suggests high precision but potentially biased accuracy, which should be investigated through the use of standardized biomass reference materials.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| buty007-8d08 | grape pomace | maplewood | — | glucose_yld | 42.7000 | 1.21 | LOW |
| buty008-128b | grape pomace | maplewood | — | glucose_yld | 40.1000 | 1.37 | LOW |
| buty009-f6f6 | grape pomace | maplewood | — | glucose_yld | 43.0000 | 1.19 | LOW |
| buty058-c478 | grape pomace | ebony | — | xylose_yld | 79.7000 | 1.30 | LOW |
| buty059-af88 | grape pomace | ebony | — | xylose_yld | 76.7000 | 1.14 | LOW |
| buty060-09f3 | grape pomace | ebony | — | xylose_yld | 83.3000 | 1.48 | LOW |
| buty106-5d8b | tomato pomace | oakleaf | — | xylose_yld | 86.4000 | 1.40 | LOW |
| buty107-4b83 | tomato pomace | oakleaf | — | xylose_yld | 81.7000 | 1.21 | LOW |
| buty272-6b9b | almond hulls | tiny | — | glucose_yld | 11.0000 | 1.52 | LOW |
| buty346-f978 | walnut tree sticks | energetic | — | xylose_yld | 16.6000 | 1.03 | LOW |
| buty347-8f10 | walnut tree sticks | energetic | — | xylose_yld | 16.0000 | 1.07 | LOW |
| buty348-e7b5 | walnut tree sticks | energetic | — | xylose_yld | 16.7000 | 1.02 | LOW |
| buty367-7ab1 | almond branches | vibrant | — | glucose_yld | 11.8000 | 1.13 | LOW |
| buty369-947d | almond branches | vibrant | — | glucose_yld | 11.5000 | 1.14 | LOW |
| buty391-1d2c | walnut shells | energetic | — | glucose_yld | 81.5000 | 1.03 | LOW |
| buty392-448d | walnut shells | energetic | — | glucose_yld | 83.7000 | 1.11 | LOW |
| buty393-de8d | walnut shells | energetic | — | glucose_yld | 89.0000 | 1.33 | LOW |
| buty442-04c1 | corn stover husks | caterpillar | — | xylose_yld | 72.5000 | 1.02 | LOW |
| buty466-ab89 | corn stover cobs | caterpillar | — | xylose_yld | 68.1000 | 1.14 | LOW |
| buty468-c171 | corn stover cobs | caterpillar | — | xylose_yld | 69.3000 | 1.18 | LOW |
| buty533-a4f3 | olive stems / leaves | excellent | — | glucose_yld | 38.0400 | 1.77 | LOW |
| buty534-a669 | olive stems / leaves | excellent | — | glucose_yld | 33.2800 | 1.24 | LOW |
| buty843-68cd | olive pomace | jaguar | — | glucose_yld | 64.6400 | 1.74 | LOW |
| buty844-c581 | olive pomace | jaguar | — | glucose_yld | 63.0600 | 1.63 | LOW |
| buty845-aae3 | olive pomace | jaguar | — | xylose_yld | 69.7500 | 1.75 | LOW |
| buty846-ecc5 | olive pomace | jaguar | — | xylose_yld | 70.3500 | 1.77 | LOW |
| buty849-f303 | olive stems / leaves | jaguar | — | xylose_yld | 41.6400 | 2.15 | LOW |
| buty850-2987 | olive stems / leaves | jaguar | — | xylose_yld | 38.7100 | 1.90 | LOW |
| chol002-bfed | grape pomace | maplewood | — | glucose_yld | 77.4000 | 1.01 | LOW |
| chol003-ed34 | grape pomace | maplewood | — | glucose_yld | 80.3000 | 1.19 | LOW |
| chol004-671c | grape pomace | maplewood | — | xylose_yld | 34.4000 | 1.02 | LOW |
| chol025-5b64 | grape stem | maplewood | — | glucose_yld | 26.9000 | 1.27 | LOW |
| chol026-ad28 | grape stem | maplewood | — | glucose_yld | 25.4000 | 1.36 | LOW |
| chol027-1686 | grape stem | maplewood | — | glucose_yld | 24.6000 | 1.41 | LOW |
| chol050-3b04 | grape pomace | ebony | — | glucose_yld | 78.9000 | 1.10 | LOW |
| chol268-ac25 | almond hulls | tiny | — | xylose_yld | 6.9000 | 1.12 | LOW |
| chol337-9361 | walnut tree sticks | energetic | — | glucose_yld | 54.5000 | 1.70 | LOW |
| chol338-f021 | walnut tree sticks | energetic | — | glucose_yld | 52.9000 | 1.59 | LOW |
| chol339-16ac | walnut tree sticks | energetic | — | glucose_yld | 49.5000 | 1.35 | LOW |
| chol340-3a85 | walnut tree sticks | energetic | — | xylose_yld | 54.0000 | 1.55 | LOW |
| chol341-e110 | walnut tree sticks | energetic | — | xylose_yld | 55.8000 | 1.67 | LOW |
| chol342-e95b | walnut tree sticks | energetic | — | xylose_yld | 50.1000 | 1.28 | LOW |
| chol409-eccf | sweet potato culls | tackle | — | glucose_yld | 72.0000 | 1.59 | LOW |
| chol410-cd0d | sweet potato culls | tackle | — | glucose_yld | 75.7000 | 1.76 | LOW |
| chol411-c3ee | sweet potato culls | tackle | — | glucose_yld | 70.9000 | 1.54 | LOW |
| chol414-44e5 | sweet potato culls | tackle | — | xylose_yld | 20.7000 | 1.22 | LOW |
| chol433-db88 | corn stover husks | caterpillar | — | glucose_yld | 104.5000 | 1.43 | LOW |
| chol434-3bb5 | corn stover husks | caterpillar | — | glucose_yld | 102.6000 | 1.37 | LOW |
| chol436-27b6 | corn stover husks | caterpillar | — | xylose_yld | 75.2000 | 1.11 | LOW |
| chol437-f0f1 | corn stover husks | caterpillar | — | xylose_yld | 73.3000 | 1.05 | LOW |
| chol458-9402 | corn stover cobs | caterpillar | — | glucose_yld | 97.6000 | 1.37 | LOW |
| chol459-4393 | corn stover cobs | caterpillar | — | glucose_yld | 93.5000 | 1.26 | LOW |
| chol461-d4dd | corn stover cobs | caterpillar | — | xylose_yld | 70.5000 | 1.22 | LOW |
| chol462-8e7c | corn stover cobs | caterpillar | — | xylose_yld | 65.7000 | 1.05 | LOW |
| chol481-bf9a | corn stover stalks | caterpillar | — | glucose_yld | 91.0000 | 1.22 | LOW |
| chol482-17bb | corn stover stalks | caterpillar | — | glucose_yld | 90.8000 | 1.21 | LOW |
| chol483-9b58 | corn stover stalks | caterpillar | — | glucose_yld | 89.9000 | 1.19 | LOW |
| chol484-3dc7 | corn stover stalks | caterpillar | — | xylose_yld | 71.3000 | 1.11 | LOW |
| chol485-9b7f | corn stover stalks | caterpillar | — | xylose_yld | 70.2000 | 1.06 | LOW |
| chol517-fce8 | olive stems / leaves | excellent | — | glucose_yld | 36.2400 | 1.57 | LOW |
| chol518-1f1f | olive stems / leaves | excellent | — | glucose_yld | 35.7700 | 1.52 | LOW |
| chol594-b244 | wheat straw | possessive | — | glucose_yld | 34.8000 | 1.69 | LOW |
| chol595-9b05 | wheat straw | possessive | — | glucose_yld | 57.4000 | 1.40 | LOW |
| chol597-0e21 | wheat straw | possessive | — | xylose_yld | 14.0000 | 1.57 | LOW |
| chol599-1024 | rice straw | possessive | — | glucose_yld | 39.5000 | 1.48 | LOW |
| chol600-282f | rice straw | possessive | — | glucose_yld | 43.2000 | 1.27 | LOW |
| chol602-93bc | rice straw | possessive | — | xylose_yld | 14.7000 | 1.55 | LOW |
| chol603-78cf | rice straw | possessive | — | xylose_yld | 19.1000 | 1.25 | LOW |
| chol605-2922 | wheat straw | wardrobe | — | glucose_yld | 56.2000 | 1.24 | LOW |
| chol606-9627 | wheat straw | wardrobe | — | glucose_yld | 37.1000 | 1.37 | LOW |
| chol607-358c | wheat straw | wardrobe | — | glucose_yld | 34.8000 | 1.69 | LOW |
| chol608-7d61 | wheat straw | wardrobe | — | xylose_yld | 33.9000 | 1.43 | LOW |
| chol610-1cab | wheat straw | wardrobe | — | xylose_yld | 16.5000 | 1.19 | LOW |
| chol612-ed7c | peach seeds | rushes | — | glucose_yld | 60.3000 | 1.49 | LOW |
| chol615-2dd1 | peach seeds | rushes | — | xylose_yld | 9.1000 | 1.33 | LOW |
| chol618-4e26 | tomato pomace | oakleaf | — | glucose_yld | 93.3000 | 1.61 | LOW |
| chol619-3575 | tomato pomace | oakleaf | — | glucose_yld | 90.6000 | 1.44 | LOW |
| chol620-06c5 | tomato pomace | oakleaf | — | xylose_yld | 7.7000 | 1.75 | LOW |
| chol621-cc06 | tomato pomace | oakleaf | — | xylose_yld | 11.5000 | 1.60 | LOW |
| chol622-38a1 | tomato pomace | oakleaf | — | xylose_yld | 10.4000 | 1.64 | LOW |
| chol624-5123 | tomato pomace | pinecrest | — | glucose_yld | 96.7000 | 1.82 | LOW |
| chol625-e307 | tomato pomace | pinecrest | — | glucose_yld | 26.6000 | 2.50 | LOW |
| chol626-e546 | tomato pomace | pinecrest | — | xylose_yld | 24.7000 | 1.07 | LOW |
| chol628-c00c | tomato pomace | pinecrest | — | xylose_yld | 12.5000 | 1.56 | LOW |
| chol629-95b0 | tomato pomace | gossamer | — | glucose_yld | 42.2000 | 1.54 | LOW |
| chol632-44e2 | tomato pomace | gossamer | — | xylose_yld | 6.2000 | 1.81 | LOW |
| chol633-6239 | tomato pomace | gossamer | — | xylose_yld | 3.8000 | 1.91 | LOW |
| chol634-4b8d | tomato pomace | gossamer | — | xylose_yld | 4.0000 | 1.90 | LOW |
| chol635-f935 | tomato pomace | gainful | — | glucose_yld | 48.0000 | 1.18 | LOW |
| chol636-885b | tomato pomace | gainful | — | glucose_yld | 45.4000 | 1.34 | LOW |
| chol637-878c | tomato pomace | gainful | — | glucose_yld | 20.1000 | 2.90 | LOW |
| chol638-827e | tomato pomace | gainful | — | xylose_yld | 20.1000 | 1.26 | LOW |
| chol639-6514 | tomato pomace | gainful | — | xylose_yld | 5.4000 | 1.84 | LOW |
| chol640-e50a | tomato pomace | gainful | — | xylose_yld | 20.7000 | 1.23 | LOW |
| chol693-2c7c | walnut hulls | energetic | — | xylose_yld | 19.4000 | 1.10 | LOW |
| chol694-8a88 | walnut hulls | energetic | — | xylose_yld | 28.3000 | 1.14 | LOW |
| chol698-8304 | unused oak stick | maplewood | — | xylose_yld | 48.2000 | 1.02 | LOW |
| chol701-a51f | spent oak chips | maplewood | — | glucose_yld | 41.0000 | 1.81 | LOW |
| chol702-95b4 | spent oak chips | maplewood | — | glucose_yld | 44.7000 | 1.56 | LOW |
| chol720-3426 | spent oak chips | rigging | — | glucose_yld | 86.4000 | 1.30 | LOW |

*...and 132 more observations. See `flagged_pretreatment.csv` for full data.*
