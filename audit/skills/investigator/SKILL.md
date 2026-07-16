# Audit Investigator Skill

## Purpose
Interactive investigation of audit findings from the latest run.
Load this skill when a developer asks to investigate, probe, or
root-cause specific anomalies from the audit platform.

## Context Loading
On activation, read:
1. `audit/output/<latest_run>/executive_audit_summary.md`
2. `audit/output/<latest_run>/llm_synthesis_*.json` files
3. Available `flagged_*.csv` files (do NOT load into memory — query via DuckDB)

## Available Tools
Use `audit/skills/investigator/query_helpers.py`:
- `query_flagged(target_name, sql=...)` — DuckDB SQL over flagged CSV
- `get_provider_history(provider_codename)` — all flags for a provider
- `get_parameter_summary(parameter_name)` — stats by resource for a parameter

## Investigation Lenses
When the user asks to investigate, probe through these lenses:
1. **Data Entry Errors** — impossible values, negative concentrations, >100% yields
2. **Unit Mismatches** — values in mg/kg instead of %, or vice versa
3. **Methodological Differences** — provider-specific systematic bias
4. **Temporal Drift** — did quality degrade after a specific date?
5. **Analyst-Specific Patterns** — record_id prefix clustering

## Triage Output
When the user confirms a root cause, output a structured triage decision:
```json
{
  "record_ids": ["..."],
  "root_cause": "...",
  "priority": "P1|P2|P3",
  "recommended_fix": "...",
  "requires_db_correction": true|false
}
```

## Workflow
1. Load executive summary and synthesis JSONs
2. Ask user which target/parameter/resource to investigate
3. Use query_helpers to pull relevant data
4. Propose hypotheses using the 5 lenses above
5. Confirm with user and output triage decision
