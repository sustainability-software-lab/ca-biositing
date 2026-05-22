# ETL Kickoff Template — CA Biositing

> **Instructions for the human user:**
>
> Fill in this template **before** starting a new ETL session with an AI agent.
> The more completely you fill it in, the fewer back-and-forth clarification
> rounds you will need. Paste the completed form as your **first message** to
> the agent, along with the instruction:
>
> > "Read `agent_docs/etl_creation_guide.md` and
> > `agent_docs/etl_provenance_checklist.md`, then use this intake form to
> > produce a Column Population Plan (Phase 2). Do not write any code yet."
>
> Fields marked **[REQUIRED]** must be filled in. Fields marked **[OPTIONAL]**
> can be left blank — the agent will flag them as open questions if needed.

---

## Section 1 — Data Source

**[REQUIRED] Source name (short identifier, will be stored in DB):**
```
<e.g. "BEAM whitepaper NSJV almond county ag report">
```

**[REQUIRED] Full title of the source publication/report/dataset:**
```
<e.g. "Market and End-Use Analysis for the Biomass Feedstock Landscape in the North San Joaquin Valley">
```

**[REQUIRED] Brief description of what this source contains:**
```
<1–2 sentences>
```

**[OPTIONAL] URL or DOI of the source:**
```
<URL or leave blank>
```

**[REQUIRED] How was the data collected? (circle or describe):**
- [ ] Manual extraction from PDF/report
- [ ] Survey / interview
- [ ] Literature review / secondary source
- [ ] Government database / census
- [ ] Field measurement
- [ ] Other: _______________

---

## Section 2 — Data Location

**[REQUIRED] Where does the raw data live?**
- [ ] Google Sheet — Name: `_______________` / Tab(s): `_______________`
- [ ] Google Drive CSV — File name: `_______________`
- [ ] Google Drive GeoJSON — File name: `_______________`
- [ ] Local file — Path: `_______________`
- [ ] Other: `_______________`

**[OPTIONAL] Link to the source spreadsheet/file:**
```
<URL>
```

**[REQUIRED] List the specific sheet tabs / columns that contain the data to load:**
```
<e.g. Tab "county_prices": columns year, county, price_per_ton, production_tons>
```

---

## Section 3 — Target Database Tables

**[REQUIRED] What is the primary record table this ETL writes to?**
```
<e.g. resource_price_record, county_ag_report_record, fermentation_record>
```

**[REQUIRED] Does this ETL also write observations (numeric measurements linked to parameters)?**
- [ ] Yes — list the parameters: `_______________`
- [ ] No

**[REQUIRED] Is this data geographically scoped?**
- [ ] Yes — geographic level: `[ ] County  [ ] State region  [ ] State  [ ] National`
  - GEOIDs or region names: `_______________`
- [ ] No

**[REQUIRED] Is this data linked to a specific biomass resource?**
- [ ] Yes — resource name(s) as they should appear in the DB (lowercase):
  ```
  <e.g. "almond hulls", "almond shells">
  ```
- [ ] No

**[OPTIONAL] Does this ETL need to update any materialized views after loading?**
- [ ] Yes — view name(s): `_______________`
- [ ] No / Unsure

---

## Section 4 — Provenance Decisions

**[REQUIRED] Dataset name (short, descriptive, will be stored in DB):**
```
<e.g. "BEAM whitepaper county ag report almond prices">
```

**[REQUIRED] What date range does this dataset cover?**
```
Start year/date: _______________
End year/date:   _______________
```

**[REQUIRED] Method name (how was the data collected/derived — stored in DB):**
```
<e.g. "manual extraction of values from PDF report">
```

**[REQUIRED] Method category (usually reuse existing — check DB before creating new):**
- [ ] `research method` (most common — reuse existing row)
- [ ] `computational method`
- [ ] `field measurement`
- [ ] New category needed: `_______________`

**[OPTIONAL] Are there existing `data_source`, `dataset`, or `method` rows in the DB
that this ETL should link to (rather than creating new ones)?**
```
<describe or leave blank>
```

---

## Section 5 — Record ID / Deduplication

**[REQUIRED] What makes a record unique? (used to build `record_id` hash)**

List the columns from the source data that together uniquely identify one row:
```
<e.g. county + year + parameter_name>
<e.g. experiment_id + sample_id + analysis_type>
```

**[OPTIONAL] Is there an existing ETL in the repo that handles similar data
that this ETL should mirror?**
```
<e.g. "similar to county_ag_report_record ETL">
```

---

## Section 6 — Scope & Constraints

**[REQUIRED] What should this ETL NOT do?** (helps prevent scope creep)
```
<e.g. "Do not create new Resource rows — only link to existing ones">
<e.g. "Do not generate or apply Alembic migrations">
<e.g. "Do not modify the materialized view SQL">
```

**[OPTIONAL] Are there any known data quality issues in the source?**
```
<e.g. "Some rows have blank county names — skip those">
<e.g. "Price values sometimes include $ signs and commas">
```

**[OPTIONAL] Are there any columns in the source that should be ignored?**
```
<list column names to skip>
```

---

## Section 7 — Open Questions (fill in what you know)

List anything you are unsure about. The agent will use these as its starting
point for clarification questions.

```
1.
2.
3.
```

---

## Section 8 — Reference ETLs (agent will read these)

The agent will automatically read the most relevant existing ETL for reference.
If you know which one is closest, name it here:

```
<e.g. "almond_nsjv" ETL in load/analysis/>
<e.g. "county_ag_report_record" ETL>
<leave blank if unsure>
```

---

## Checklist Before Submitting This Form

- [ ] Section 1 (Data Source) is complete
- [ ] Section 2 (Data Location) is complete — especially the sheet/tab/column list
- [ ] Section 3 (Target Tables) is complete
- [ ] Section 4 (Provenance) is complete — especially dataset name and date range
- [ ] Section 5 (Record ID) is complete — the uniqueness columns are listed
- [ ] Section 6 (Scope) has at least one "should NOT do" constraint
- [ ] I have NOT asked the agent to run the ETL — that is a manual step I will do

---

## How to Start the Agent Session

Paste this completed form as your first message, preceded by:

```
Read the following agent docs before starting:
- agent_docs/etl_creation_guide.md
- agent_docs/etl_provenance_checklist.md
- agent_docs/namespace_packages.md
- agent_docs/testing_patterns.md
- docs/database_conventions.md
- src/ca_biositing/pipeline/AGENTS.md
- src/ca_biositing/datamodels/AGENTS.md

Then read the reference ETL I named in Section 8 of the intake form below.

Once you have read all docs, produce a Column Population Plan (Phase 2 from
etl_creation_guide.md). Do not write any code yet. Wait for my approval of
the plan before proceeding.

--- INTAKE FORM ---
[paste completed form here]
```

---

## Session Continuation (for new agent sessions mid-ETL)

If you need to start a new agent session partway through an ETL, paste this
context block at the start of the new session:

```
We are mid-way through building the <ETL name> ETL for ca-biositing.

Read these docs first:
- agent_docs/etl_creation_guide.md
- agent_docs/etl_provenance_checklist.md

Completed phases: <list phases done, e.g. "Phase 2 (plan approved), Phase 3 (extract done)">
Current phase: <e.g. "Phase 4 — Transform">
Files created so far: <list file paths>

The approved Column Population Plan is:
<paste the approved plan here>

Continue from Phase <N>. Do not re-do completed phases.
```
