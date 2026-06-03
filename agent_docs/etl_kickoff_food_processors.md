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
CARB Food Processors
```

**[REQUIRED] Full title of the source publication/report/dataset:**

```
California Air Resources Board Food Processor Facilities Datasets
```

**[REQUIRED] Brief description of what this source contains:**

```
Food processors identified within CARB air quality districts
```

**[OPTIONAL] URL or DOI of the source:**

```
<URL or leave blank>
```

**[REQUIRED] How was the data collected? (circle or describe):**

- [ ] Manual extraction from PDF/report
- [ ] Survey / interview
- [ ] Literature review / secondary source
- [x] Government database / census
- [ ] Field measurement
- [ ] Other: **\*\***\_\_\_**\*\***

---

## Section 2 — Data Location

**[REQUIRED] Where does the raw data live?**

- [x] Google Sheet — Name: `food_manufacturers_and_processors_carb` / Tab(s):
      `all facilities`
- [ ] Google Drive CSV — File name: `_______________`
- [ ] Google Drive GeoJSON — File name: `_______________`
- [ ] Local file — Path: `_______________`
- [ ] Other: `_______________`

**[OPTIONAL] Link to the source spreadsheet/file:**

```
https://docs.google.com/spreadsheets/d/1SxO8VxCjdF3D5VuLcmrbrHFeUiUJGv0hApywCep7oPc/edit?gid=459548169#gid=459548169
```

**[REQUIRED] List the specific sheet tabs / columns that contain the data to
load:**

```
Tab "all facilities" all columns
```

---

## Section 3 — Target Database Tables

**[REQUIRED] What is the primary record table this ETL writes to?**

```
infrastructure_food_processing_facilities
```

**[REQUIRED] Does this ETL also write observations (numeric measurements linked
to parameters)?**

- [ ] Yes — list the parameters: `_______________`
- [x] No

**[REQUIRED] Is this data geographically scoped?**

- [x] Yes — geographic level:
      `[x] Lat/Long [ ] County  [ ] State region  [ ] State  [ ] National`
  - GEOIDs or region names: `_______________`
- [ ] No

**[REQUIRED] Is this data linked to a specific biomass resource?**

- [ ] Yes — resource name(s) as they should appear in the DB (lowercase):
  ```
  <e.g. "almond hulls", "almond shells">
  ```
- [x] No, many resources

**[OPTIONAL] Does this ETL need to update any materialized views after
loading?**

- [ ] Yes — view name(s): `_______________`
- [x] No / Unsure

---

## Section 4 — Provenance Decisions

**[REQUIRED] Dataset name (short, descriptive, will be stored in DB):**

```
Kieran Heeley CARB air district crop based food processor lists
```

**[REQUIRED] What date range does this dataset cover?**

```
Start year/date: 01/01/2022
End year/date:   12/31/2024
```

**[REQUIRED] Method name (how was the data collected/derived — stored in DB):**

```
Data requested from CARB air districts and assembled by Kieran Heeley (kheeley@ucdavis.edu).
```

**[REQUIRED] Method category (usually reuse existing — check DB before creating
new):**

- [x] `research method` (most common — reuse existing row)
- [ ] `computational method`
- [ ] `field measurement`
- [ ] New category needed: `_______________`

**[OPTIONAL] Are there existing `data_source`, `dataset`, or `method` rows in
the DB that this ETL should link to (rather than creating new ones)?**

No.

```
Add this to the method description:

Public information requests from government databases for processors, manual extraction from PDF reports (for throughput), literature analysis (for residue factors).

Throughput of the facilities is obtained from public information requests from individual air districts for all (except for tomatoes) with additional site locations also obtained from CDFA and crop management boards. For tomatoes, where throughput data was not available, capacity data was obtained from the individual crop management board (PTAB), with missing data filled in by estimating capacity based upon emissions data from carb.
For byproduct flows, the residue factors were taken from literature and interviews with relevant stakeholders, for all crops except tomatoes, which are combined with throughput to give a quantity of byproducts. For tomatoes, as exact throughput is not known, the total byproducts produced (as defined by BPDB) are split based the capacity of each facility.
```

---

## Section 5 — Record ID / Deduplication

**[REQUIRED] What makes a record unique? (used to build `record_id` hash)**

List the columns from the source data that together uniquely identify one row:

```
name + address
OR
name + lat + long
```

**[OPTIONAL] Is there an existing ETL in the repo that handles similar data that
this ETL should mirror?**

```
None/unsure.
```

---

## Section 6 — Scope & Constraints

**[REQUIRED] What should this ETL NOT do?** (helps prevent scope creep)

```
Do not create new relational tables: Do not create a normalized join table for byproducts. The infrastructure_food_processing_facilities table must remain strictly denormalized
Do not write geocoding code currently. Create empty section(s) for drop in code which will add columns to the transformed dataset for lat/long and geocode the address to popualte the lat/long columns. User will add geocoding as a separate task.
```

**[OPTIONAL] Are there any known data quality issues in the source?**

```
<e.g. "Some rows have blank county names — skip those">
<e.g. "Price values sometimes include $ signs and commas">

data will need to be cleaned extensively in the transform step
-zip code is sumptimes 5 digits sometimes 10 (ZIP+4). Truncate to 5-digit.
-process table capitalization is messy. standardize to Capitized First Letter.
-currently there are separate columns for byproducts 1-5 and in the final DB table we will want byproducts in one field as comma separated list. Same with the quantities in tons/year. These should be ordered so they byproduct 1 and quantity in the following column are correspondingly the first values in the comma separated list, second of each listed second and so on.
-address whitespace for geocoding: before passing the concatenated address string to the geocoding function, the script must strip leading/trailing whitespace and remove any hidden newline characters (\n), which will cause the Mapbox/Google API calls to fail.
```

**[OPTIONAL] Are there any columns in the source that should be ignored?**

```
None
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
- [ ] Section 2 (Data Location) is complete — especially the sheet/tab/column
      list
- [ ] Section 3 (Target Tables) is complete
- [ ] Section 4 (Provenance) is complete — especially dataset name and date
      range
- [ ] Section 5 (Record ID) is complete — the uniqueness columns are listed
- [ ] Section 6 (Scope) has at least one "should NOT do" constraint
- [ ] I have NOT asked the agent to run the ETL — that is a manual step I will
      do

---

## How to Start the Agent Session

Paste this completed form as your **first message**, preceded by this exact
block:

```
You are the CA Biositing ETL agent. Read these docs before doing anything else:
- agent_docs/etl_creation_guide.md        ← read in full, always
- agent_docs/etl_provenance_checklist.md  ← read in full, always
- docs/database_conventions.md            ← short, read in full
- src/ca_biositing/pipeline/AGENTS.md     ← skim for pipeline rules

Then read the reference ETL named in Section 8 of the intake form below.

PHASE GATE RULES:
- Work through phases 0–7 in order as defined in etl_creation_guide.md §2.
- Begin every response with: ### Phase <N> — <Phase Name>
- Do not start a new phase until I explicitly approve the previous one.
- If I ask you to skip a phase, warn me of the specific risk and ask
  "are you sure?" before complying. Never skip silently.
- Do not write any code until Phase 2 (Column Population Plan) is approved.

Start with Phase 0 (read docs) then Phase 1 (codebase scan), then produce
the Phase 2 Column Population Plan. Stop and wait for my approval before
writing any code.

--- INTAKE FORM ---
[paste completed form here]
```

---

## Session Continuation (for new agent sessions mid-ETL)

If you need to start a new agent session partway through an ETL, paste this
context block at the start of the new session. The agent will re-read the guide
and resume from the correct phase without re-doing completed work:

```
You are the CA Biositing ETL agent resuming a mid-session handoff.

Read these docs first:
- agent_docs/etl_creation_guide.md
- agent_docs/etl_provenance_checklist.md

PHASE GATE RULES:
- Begin every response with: ### Phase <N> — <Phase Name>
- Do not start a new phase until I explicitly approve the previous one.
- If I ask you to skip a phase, warn me of the specific risk and ask
  "are you sure?" before complying. Never skip silently.

ETL name: <ETL name>
Completed phases: <e.g. "Phase 2 (plan approved), Phase 3 (extract done)">
Current phase to resume: <e.g. "Phase 4 — Transform">
Files created so far:
- <file path 1>
- <file path 2>

Approved Column Population Plan:
<paste the approved plan here>

Resume from Phase <N>. Do not re-do completed phases. Confirm you have read
the guide and understood the plan before writing any code.
```
