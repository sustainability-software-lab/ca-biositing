# 🔍 Detailed Target Audit: `ultimate` — 2026-07-20

**Flagged Observations:** 3 (0 HIGH, 0 MEDIUM, 3 LOW)

**Z-Score Threshold:** 1.0 | **Min Group Size:** 3

**[🔗 View and Manage Anomalies in Google Sheets](https://docs.google.com/spreadsheets/d/10aFbZznW6dH_3iZZqJm0dcDNPKXDqOFcE1FLAVGt52U)**

---

## 🧠 LLM Synthesis

The audit of the 'ultimate' (Ultimate Analysis) dataset reveals a small but structurally compromised collection of 15 records primarily focused on nitrogen content in biomass resources. While the observed nitrogen values (ranging from 0.23% to 2.98%) are within expected biological ranges for pomace and agricultural residues, the dataset suffers from a total collapse of analyst attribution metadata. Specifically, 100% of the 'analyst_name' and 'analyst_email' fields are missing, which fundamentally undermines the traceability and accountability of the laboratory results.

Furthermore, several records flagged for low-severity anomalies contain cryptic notations such as '10 dup' and '13 dup' in the notes field. These annotations, particularly on high-end nitrogen values for tomato and grape pomace from providers like Riverstone and Maplewood, suggest potential data entry duplication or the carry-over of values from previous batches without proper validation. The presence of constant 'sample_date' and 'created_at' values across all records further indicates a batch-processed export that has lost its original temporal granularity, making it difficult to assess seasonal or processing-time variances.

## 🚩 Flagged Observations (Top 100)

| Record ID | Resource | Provider | Sample Date | Parameter | Value | Z-Score | Severity |
|-----------|----------|----------|-------------|-----------|-------|---------|----------|
| )u73ee73 | tomato pomace | pinecrest | — | nitrogen | 2.2800 | 1.26 | LOW |
| )u91a791 | tomato pomace | riverstone | — | nitrogen | 2.9800 | 1.01 | LOW |
| )u87a587 | grape pomace | maplewood | — | nitrogen | 1.9300 | 1.01 | LOW |
