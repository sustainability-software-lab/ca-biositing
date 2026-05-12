# Comprehensive Database Audit Report: Local

**Date:** 2026-05-04 **Audit Scope:** AIM1 (Analytical) + AIM2 (Processing) +
Sample Lineage **Overall Status:** Phase 1 Complete - Data Governance
Remediation Required

## 1. Executive Summary

The CA Biositing analytical and processing warehouse shows strong record volume
(9,000+ rows) but critical governance gaps keep the system below production
readiness. The most acute failure is the absence of method attribution for the
highest-volume processing streams (fermentation and gasification) and for the
ICP metals panel, leaving 5,103 QC-qualified records without any reproducible
protocol trail and immediately blocking regulatory or scientific reuse. Given
compounding lineage gaps and missing experiment IDs across AIM1, the overall
**Data Quality Score is 4.8 / 10**.

AIM2 processing tables maintain high QC pass rates (>89%) yet store structural
metadata unevenly: analyst, strain, and vessel IDs are complete, but experiment
tracking is 0% and pretreatment method coverage collapses once downstream
fermentation begins. AIM1 primary assays retain 85% QC success but have weak
analyst coverage (55%) and lineage integrity (25%) with compositional and
proximate modules rarely linking back to Prepared Samples or Primary
Agricultural Products. The centralized lineage view reports 93.58% integrity for
296 prepared samples, but module-level joins show that most analytical datasets
are effectively siloed.

## 2. Key Findings by Severity

### 🔴 Severity 1: CRITICAL

- **Zero Method Traceability in High-Volume Modules**: Fermentation (3,736
  QC-qualified rows), gasification (382), and ICP (985) store 0% method
  identifiers despite being core ASTM-critical assays, rendering 5,103 records
  non-reproducible
  ([audit/output/audit_data.json](audit/output/audit_data.json)).
- **Experiment Lineage Missing Across AIM1 + AIM2**: Proximate, compositional,
  fermentation, pretreatment, gasification, xrf, xrd, and ultimate modules all
  report 0% experiment identifiers (9,606 records), breaking longitudinal study
  design controls
  ([audit/output/audit_data.json](audit/output/audit_data.json)).
- **XRF QC Not Run**: All 390 XRF measurements have neither pass nor fail
  evaluation, effectively blocking their release because no QC status can be
  certified ([audit/output/audit_data.json](audit/output/audit_data.json)).

### 🟠 Severity 2: HIGH

- **Mixed Measurement Units in USDA Imports**: Eleven parameters (area,
  production, yield, Ca/Mg/P/K, etc.) show 2–5 unit variants (e.g., acres vs.
  operations, ppm vs. percent), risking aggregation errors in downstream
  analytics ([audit/output/audit_data.json](audit/output/audit_data.json)).
- **Lineage Fragmentation in AIM1 Primary Modules**: Proximate (14.4%),
  compositional (25.5%), ICP (24.0%), and ultimate (35.7%) rarely link Prepared
  Samples to Primary Ag Products, which undermines sample provenance even though
  the global lineage inventory reports 93.58% integrity
  ([audit/output/audit_data.json](audit/output/audit_data.json)).
- **Gasification Stability Issues**: Gasification retains only 62.5% QC pass
  rate with 194 fails and 35 nulls, indicating either instrumentation drift or
  data-entry errors that need rapid remediation
  ([audit/output/audit_data.json](audit/output/audit_data.json)).

### 🟡 Severity 3: MEDIUM

- **Raw Data Attachments Missing**: Proximate (0% of 1,227 QC-non-fail records)
  and ultimate (3% of 66) lack raw files, preventing recalculation of QC
  failures ([audit/output/audit_data.json](audit/output/audit_data.json)).
- **Analyst Attribution Gaps**: Only 36% of proximate and 0% of ultimate runs
  capture analyst IDs, reducing accountability for 1,293 AIM1 records
  ([audit/output/audit_data.json](audit/output/audit_data.json)).
- **Parameter Coverage Imbalance**: Core compositional markers
  (glucan/glucose/xylan) cover <20% of records, while fermentation KPI panels
  (e.g., ethanol titer/yield) cover 6–8% of 4,021 rows, indicating inconsistent
  experimental design execution
  ([audit/output/audit_data.json](audit/output/audit_data.json)).

## 3. Domain Performance Matrix

| Domain                                                         | Record Count | QC Pass % | Metadata % (Avg Analyst Coverage) | Lineage Integrity % | Status                                   |
| :------------------------------------------------------------- | -----------: | --------: | --------------------------------: | ------------------: | :--------------------------------------- |
| **AIM1 Primary** (proximate, compositional, ICP, ultimate)     |        3,544 |      85.0 |                              55.0 |                24.9 | ⚠️ Metadata + lineage remediation needed |
| **AIM1 Secondary** (XRF, XRD, FTNIR)                           |          418 |     6.5\* |                             100.0 |               25.0† | 🚨 QC not executed for XRF               |
| **AIM2 Processing** (fermentation, pretreatment, gasification) |        5,538 |      89.5 |                              99.0 |               41.9‡ | ⚠️ Method tracing missing                |

\*XRF lacks QC evaluation; percent reflects only XRD. †FTNIR has no records;
lineage average reflects XRF/XRD only. ‡Fermentation lineage metric not
reported; figure averages pretreatment (21.3%) and gasification (62.5%).

## 4. Lineage & Connectivity Analysis

Prepared Sample inventory (296 rows) is 93.58% connected to Primary Agricultural
Products, yet module-level linkage drops sharply once data leaves the lineage
view. AIM1 tables reference only 14–36% of their lineage fields, so Prepared
Samples cannot be deterministically mapped to analytical outputs. AIM2
processing maintains better continuity in gasification (62.5%) but pretreatment
and fermentation omit lineage IDs in 70–100% of records. As a result, the sample
chain breaks when analysts attempt to trace a fermented result back to its
feedstock lot or field sample.

## 5. Detailed Module Analysis

- **Proximate**: 1,339 records, 91.3% QC pass; analyst IDs (36%) and raw data
  (0%) missing; lineage integrity 14.4%; high parameter coverage for total
  solids/ash (~26%).
- **Compositional**: 968 records, 76.1% QC pass (737 of 968); analyst coverage
  52.9%; method coverage 100%; lineage integrity 25.5%; key carbohydrates only
  measured in ~20% of records.
- **ICP**: 1,153 records, 85.5% QC pass; analyst 83.9% but method 0% and lineage
  24%; Ca/Mg/P/K use mixed units.
- **Ultimate**: 84 records, 78.6% QC pass; analyst 0%, raw data 3%, lineage
  35.7%; nitrogen range 0.23–3.06 wt% with no negatives.
- **Fermentation**: 4,021 records, 92.9% QC pass; method/experiment tracking 0%;
  pretreatment metadata 93.8%; lineage metric not published; KPI parameters
  (e.g., ethanol titers) captured in ≤7% of records.
- **Pretreatment**: 906 records, 92.2% QC pass; analyst 94.9%, method 100%,
  experiment 0%; lineage 21.3%; glucose yield coverage 51.5%.
- **Gasification**: 611 records, 62.5% QC pass with 194 fails; method 0%;
  lineage 62.5%; gas composition parameters captured in only 5.5% of rows.
- **XRF/XRD/FTNIR**: XRF lacks QC disposition entirely; XRD has strong QC (96%)
  but no raw data; FTNIR has no records in this extract.

## 6. Recommended Action Plan

1. **Immediate Action**: Backfill method IDs for fermentation, gasification, and
   ICP by enforcing required fields in ETL uploads; block new records without
   method references.
2. **Near-term Remediation**: Implement lineage enforcement in Prefect flows so
   Prepared Samples, Field Samples, and Primary Ag Products are mandatory
   foreign keys for AIM1 modules; reprocess historical batches to elevate
   lineage integrity above 80%.
3. **Process Improvement**: Harmonize unit dictionaries for USDA-derived
   parameters and expand QC validation to XRF/secondary assays; couple this with
   a metadata completeness dashboard (analyst, experiment, raw data) to prevent
   future regressions.
