# Instructions for AI Agents: CA Biositing Database Audit

You are a data quality and database integrity specialist. You will be provided
with raw data from the `audit` system of the `ca-biositing` repository.

## Running the Audit

If you are asked to "run the audit" yourself as an agent:

1. Ensure the database is accessible.
2. For **local** checks, use: `pixi run audit`.
3. For **staging** checks, ensure the tunnel is up and use:
   `pixi run audit-staging`.
4. After execution, read the results from `audit/output/audit_summary.md`.

## Goal

Interpret the raw SQL query results and compile them into a comprehensive,
insight-driven audit report using the provided `REPORT_PROMPT.md` template.

## Interpretation Rules

### 1. QC Filtering & Record Counts

- **Total Records**: Total volume in the table.
- **QC Pass Rate**: Percentage where `qc_pass = 'pass'`.
- **Metrics/Averages**: Only include records where `qc_pass != 'fail'` in
  statistical metrics.

### 2. Lineage Integrity

- **Connectivity**: Verify the % of Prepared Samples that can be traced all the
  way back to a Primary Agricultural Product.
- **Resources**: Report the number of unique resources and field samples
  accounted for in each analysis type. High fragmentation (many records, few
  linked resources) is a finding.

### 3. Placeholder Values

- Flag "nd", "ND", "blank", "BLANK", or empty strings in `observation.value`.
- These are data gaps, even if stored as strings.

### 4. Metadata Completeness

- Critical fields: `analyst_id`, `method_id`, `experiment_id`, `dataset_id`.
- Processing-specific fields (AIM2): `strain_id`, `vessel_id`, `eh_method_id`,
  `pretreatment_method_id`.
- 0% coverage on these is a **Severity 1: Critical** issue.

### 5. Domain Performance Matrix

Use the summarized results to populate the performance matrix in the final
report.

## Reporting Severity Levels

- **CRITICAL (Severity 1)**: Blocks data usage (e.g., 0% method tracking, broken
  lineage, 100% QC fail).
- **HIGH (Severity 2)**: Significant quality issues (e.g., negative physical
  values, mixed units, missing monomer measurements).
- **MEDIUM (Severity 3)**: Metadata gaps or fragmentation.
- **LOW (Severity 4)**: Minor inconsistencies.
