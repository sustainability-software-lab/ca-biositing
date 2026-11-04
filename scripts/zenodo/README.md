# Zenodo Dataset Release & Live Smartsheet Authorship Workflow

This directory provides the automated authorship ingestion and Zenodo REST API
deposition workflow for the **BioCIRV Public Dataset Release**.

---

## 1. Architectural Overview: Code Release vs. Dataset Release

| Aspect                | Existing Code Release (UW SSEC)                                  | New Public Dataset Release (BioCIRV Public Schema)                                                                    |
| :-------------------- | :--------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| **Artifact Type**     | `software` (GitHub repository snapshot)                          | `dataset` (5 flattened views from `biocirv_public` + data dictionary)                                                 |
| **Concept DOI**       | `10.5281/zenodo.19443582`                                        | Separate Dataset Concept DOI (minted on first release)                                                                |
| **Trigger Mechanism** | Native GitHub Release → Zenodo Webhook                           | Manual `workflow_dispatch` GitHub Action → **Zenodo REST API**                                                        |
| **Author Source**     | Static [`CITATION.cff`](../../CITATION.cff) (7 software authors) | Live **Smartsheet REST API** (`03 Staff and Contacts BioCirV`) + [`CITATION.cff`](../../CITATION.cff) cross-reference |
| **License**           | `BSD-3-Clause` (software license)                                | `CC-BY-4.0` (standard open scientific dataset attribution license)                                                    |

> **Why we use the Zenodo REST API instead of the GitHub-Zenodo Webhook:**
> Zenodo's native GitHub webhook only archives the source code repository
> zipball and links 1-to-1 with a single software Concept DOI
> (`10.5281/zenodo.19443582`). Publishing the exported CSV/Parquet tables from
> the 5 `biocirv_public` views requires hitting `/api/deposit/depositions` with
> `upload_type: "dataset"` and linking back to the software DOI via
> `related_identifiers` (`isCompiledBy`).

---

## 2. Files in `scripts/zenodo/`

- **[`sync_zenodo_authors.py`](./sync_zenodo_authors.py)**:
  - Connects **live to the Smartsheet REST API** (`GET /2.0/sheets/{sheet_id}`)
    using `SMARTSHEET_ACCESS_TOKEN` and `SMARTSHEET_SHEET_ID` (also supports
    `--xlsx` / `--csv` for offline testing).
  - Cross-references [`CITATION.cff`](../../CITATION.cff) to backfill known
    ORCIDs (e.g., Meili Gong, Peter Smith, Tyler Huntington).
  - Separates **`metadata.creators`** (primary byline authors, sorted by tier
    then last name) from **`metadata.contributors`** (supporting roles with
    official DataCite contributor types: `DataCurator`, `DataCollector`,
    `ProjectLeader`, `Researcher`).
  - Supports `--send-orcid-requests` to trigger automated **Smartsheet Update
    Requests** (`POST /2.0/sheets/{sheet_id}/updaterequests`) emailing every
    contributor missing an ORCID ID.
- **[`publish_zenodo_dataset.py`](./publish_zenodo_dataset.py)**:
  - Stages or publishes the exported dataset files + `zenodo_metadata.json` to
    **Zenodo Sandbox** (`sandbox.zenodo.org`, default) or **Zenodo Production**
    (`zenodo.org`, `--production`).
  - Supports `--existing-deposition-id` so subsequent dataset releases mint new
    versions under the same permanent Concept DOI.
  - Defaults to saving a **reviewable Draft** on Zenodo unless `--publish` is
    explicitly passed.
- **[`zenodo-dataset-release.yml.example`](./zenodo-dataset-release.yml.example)**:
  - Ready-to-use `workflow_dispatch` GitHub Action template (copy to
    `.github/workflows/zenodo-dataset-release.yml` once the `biocirv_public`
    schema PR is merged).
- **[`author_audit_report.md`](./author_audit_report.md)** &
  **[`zenodo_metadata.preview.json`](./zenodo_metadata.preview.json)**:
  - Current audit report and preview Zenodo payload generated from
    `03_Staff_and_Contacts_BioCirV.xlsx`.

---

## 3. Recommended Smartsheet Schema Additions (3 Columns)

The existing `03 Staff and Contacts BioCirV` Smartsheet already has `Name`,
`First name as used`, `Last name`, `Organization`, `orcid.org/`, `Active?`,
`Core team`, `Tags`, `Group(s)`, and `Role(s)`.

To support deterministic automation for both the **Zenodo Dataset Release** and
**future manuscripts** without manual list editing, add **3 columns** to
Smartsheet:

| New Column Name            | Smartsheet Type        | Allowed Values / Format                                                                                                                                           | Purpose                                                                                                                              |
| :------------------------- | :--------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| **`Zenodo Release Role`**  | Single-Select Dropdown | `Creator`, `Contributor:DataCurator`, `Contributor:DataCollector`, `Contributor:ProjectLeader`, `Contributor:Researcher`, `Contributor:ProjectManager`, `Exclude` | Distinguishes primary DOI byline authors (`creators`) from supporting `contributors` (DataCite roles) and excluded admin/comms rows. |
| **`Zenodo Author Order`**  | Text/Number            | Integer Tier (`1`, `2`, `3`, ...) or explicit rank                                                                                                                | Controls byline sort order. Within the same number/tier, `sync_zenodo_authors.py` sorts alphabetically by `Last name, First name`.   |
| **`Publication Releases`** | Multi-Select Dropdown  | `Zenodo Dataset v1`, `Aim 1 Paper`, `Aim 3 Paper`, `Portal Paper`                                                                                                 | Allows filtering the exact subset of contributors for a specific dataset release or paper (`--release "Zenodo Dataset v1"`).         |

_(Note: Before these 3 columns are added, `sync_zenodo_authors.py` automatically
falls back to **Heuristic Preview Mode** using existing `Tags`
(`Data contributor`, `PI / Co-PI`, `Core team`) and `Group(s)`.)_

---

## 4. Audit Findings from Current Smartsheet (`03_Staff_and_Contacts_BioCirV.xlsx`)

Running `sync_zenodo_authors.py` against the current Smartsheet surfaced the
following items to clean up:

1. **ORCID Coverage (`1 / 75` in Smartsheet):**
   - Only **James Gardner** (`0000-0002-8106-3817`) currently has `orcid.org/`
     populated in Smartsheet.
   - **Meili Gong**, **Peter Smith**, and **Tyler Huntington** have ORCIDs in
     [`CITATION.cff`](../../CITATION.cff) (automatically backfilled by the
     script, but should be copied into Smartsheet).
   - **Non-blocking for Zenodo release:** Zenodo allows updating
     `creators`/`contributors` metadata (including adding ORCIDs) _after_ a DOI
     is published without minting a new DOI version.
2. **Incomplete `Data contributor` Tagging (`5 / 75`):**
   - Currently only 5 people are tagged `Data contributor` in column `H`
     (_Anagha Krishnamoorthy, Andrea Bailey, James Gardner, Jenny Duong, Peter
     Smith_). Several Aim 1/2/3 researchers and data collectors are not yet
     tagged.
3. **Specific Row Anomalies to Fix in Smartsheet:**
   - **Row `con079` (Giya Kuriakose):** `First name as used` (`Kariakose`) and
     `Last name` (`Giya`) are swapped and misspelled, and `Active?` is blank.
   - **Row `con054` (Tai-Yuan Huang):** `Active?` is blank.
   - **Row `con050` (`Fraser Murison Smith - Slack`):** Duplicate Slack-specific
     entry of `con026` (automatically filtered out by `sync_zenodo_authors.py`).
   - **Character Encoding (`con069` Mariana Larrañaga Tapia, `con022` Tea
     Lempiälä):** Non-ASCII characters exported as `\ufffd` in some exports
     (automatically repaired by `sync_zenodo_authors.py`).

---

## 5. Ready-to-Paste Slide Content (for Tuesday Review & Thursday Stakeholder Deck)

Below is the structured text for the slide Deck
([Slide Link](https://docs.google.com/presentation/d/1NZ92QFGZpyng5kXL6s3SbkasDZJdIqejqPkCsMqGuYQ/edit?slide=id.he8402c422401a42_0_19)):

### Slide Title: Zenodo Dataset Release — Authorship Workflow & Open Decisions

**What’s Built (`scripts/zenodo/`):**

- **Live Smartsheet → Zenodo Sync (`sync_zenodo_authors.py`):** Pulls live
  contributor rows via Smartsheet API, validates ORCIDs/affiliations, and builds
  the Zenodo REST API payload (`creators` vs. DataCite `contributors`).
- **Automated Deposition Pipeline (`publish_zenodo_dataset.py` + GitHub
  Action):** Stages the 5 `biocirv_public` views + metadata to Zenodo
  Sandbox/Production as a reviewable Draft before minting the Dataset DOI.

**3 Smartsheet Columns Needed (5-min setup with James):**

1. **`Zenodo Release Role`** _(Dropdown)_: `Creator` (byline author) vs.
   `Contributor:<DataCiteRole>` (`DataCollector`, `DataCurator`,
   `ProjectLeader`, `Researcher`) vs. `Exclude`.
2. **`Zenodo Author Order`** _(Tier 1 / 2 / 3)_: Tier 1 = Lead Data Curators;
   Tier 2 = Aim 1–3 Contributors (auto-sorted A–Z); Tier 3 = PIs / Leads.
3. **`Publication Releases`** _(Multi-select)_: e.g., `Zenodo Dataset v1`,
   `Aim 1 Paper`, `Aim 3 Paper` (decouples dataset-wide release credit from
   paper-specific author lists).

**Decisions & Action Items for Aim 3 / Leadership (Thursday Meeting):**

- [ ] **Byline Policy (`Creators` vs. `Contributors`):** Who goes on the main
      dataset citation byline (`creators`, currently ~30 Core/Data/PI members)
      vs. the Zenodo `contributors` section (e.g., UCCE farm advisors / sample
      providers)?
- [ ] **ORCID Collection (Currently 4/75 known):** Trigger automated Smartsheet
      Update Request email (`--send-orcid-requests`) with a Friday deadline.
      _(Confirmed: missing ORCIDs are **not** a release blocker—Zenodo allows
      post-publication metadata updates without changing the DOI)._
- [ ] **Smartsheet Data Cleanup:** Fix 2 incomplete rows (`Giya Kuriakose`
      swapped first/last name; `Tai-Yuan Huang` blank active status) and confirm
      whether UW SSEC software engineers from `CITATION.cff` should be listed as
      `Contributor:Software` on the dataset release.
- [ ] **Dataset License & LBNL Review:** Confirm **CC-BY-4.0** for the dataset
      release (standard open data attribution license, distinct from
      `BSD-3-Clause` code license) and verify whether LBNL IPO/STI requires
      sign-off for public dataset deposition.

---

## 6. Required GitHub Actions Secrets & Variables

To enable live execution in GitHub Actions:

- **Secrets (`Settings -> Secrets and variables -> Actions -> Secrets`):**
  - `SMARTSHEET_ACCESS_TOKEN`: Smartsheet API Personal Access Token (read access
    to `03 Staff and Contacts BioCirV`).
  - `ZENODO_TOKEN`: Zenodo Personal Access Token (`deposit:write` and
    `deposit:actions` scopes; use a Sandbox token for `zenodo-sandbox`
    environment and Production token for `zenodo-production`).
- **Variables (`Settings -> Secrets and variables -> Actions -> Variables`):**
  - `SMARTSHEET_SHEET_ID`: Numeric Sheet ID of `03 Staff and Contacts BioCirV`
    (found in Smartsheet via _File → Properties_).
  - `ZENODO_DEPOSITION_ID`: _(Optional, after v1 release)_ The
    Concept/Deposition ID of the first published dataset so future runs
    automatically create Version 2, 3, etc.
