#!/usr/bin/env python3
"""Synchronize BioCIRV contributor metadata from Smartsheet to Zenodo JSON.

This script connects directly to the live Smartsheet REST API (or reads a local
Smartsheet `.xlsx`/`.csv` export for offline testing) and generates:
1. A Zenodo REST API deposition metadata payload (`zenodo_metadata.json`)
   separating primary byline authors (`creators`) from supporting roles
   (`contributors` with DataCite contributor types).
2. A Markdown audit report (`author_audit_report.md`) highlighting missing
   ORCIDs, missing affiliations, name/encoding anomalies, and readiness stats.
3. Optional automated Smartsheet Update Requests (`--send-orcid-requests`) to
   email contributors whose ORCIDs are missing in Smartsheet.

Usage (Live Smartsheet API):
    export SMARTSHEET_ACCESS_TOKEN="your_token"
    export SMARTSHEET_SHEET_ID="your_sheet_id"
    python scripts/zenodo/sync_zenodo_authors.py --release "Zenodo Dataset v1"

Usage (Offline / Local XLSX test):
    python scripts/zenodo/sync_zenodo_authors.py \
        --xlsx path/to/03_Staff_and_Contacts_BioCirV.xlsx \
        --citation-cff CITATION.cff
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SMARTSHEET_API_BASE = "https://api.smartsheet.com/2.0"
ORCID_REGEX = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE)

# Valid DataCite / Zenodo contributor types for `metadata.contributors`
VALID_ZENODO_CONTRIBUTOR_TYPES = {
    "ContactPerson",
    "DataCollector",
    "DataCurator",
    "DataManager",
    "Distributor",
    "Editor",
    "HostingInstitution",
    "Producer",
    "ProjectLeader",
    "ProjectManager",
    "ProjectMember",
    "RegistrationAgency",
    "RegistrationAuthority",
    "RelatedPerson",
    "Researcher",
    "ResearchGroup",
    "RightsHolder",
    "Sponsor",
    "Supervisor",
    "WorkPackageLeader",
    "Other",
}

# Known encoding repair map for Smartsheet exports with Windows-1252/UTF-8 mojibake
NAME_CLEANUP_MAP = {
    "Larra\ufffdaga": "Larrañaga",
    "Lempi\ufffdl\ufffd": "Lempiälä",
}


@dataclass
class ContributorRecord:
    """Normalized contributor record from Smartsheet."""

    row_id: str | int
    line_id: str
    full_name: str
    first_name: str
    last_name: str
    organization: str
    email: str
    orcid: str = ""
    orcid_source: str = ""  # "smartsheet", "citation.cff", "orcid_api_suggestion", ""
    active: str = ""
    core_team: bool = False
    ecr: bool = False
    tags: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    roles: str = ""
    contribution_description: str = ""
    # New/Proposed Smartsheet columns for explicit Zenodo authorship governance
    zenodo_role: str = ""  # e.g. "Creator", "Contributor:DataCollector", "Exclude"
    zenodo_order_tier: int = 99
    publication_releases: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)

    @property
    def zenodo_formatted_name(self) -> str:
        """Return 'Family, Given' as required by Zenodo REST API."""
        if self.last_name and self.first_name:
            return f"{self.last_name}, {self.first_name}"
        return self.full_name

    def to_zenodo_person(self, contributor_type: str | None = None) -> dict[str, str]:
        """Serialize to a Zenodo `creators` or `contributors` entry."""
        entry: dict[str, str] = {"name": self.zenodo_formatted_name}
        if self.organization:
            entry["affiliation"] = self.organization
        if self.orcid:
            entry["orcid"] = self.orcid
        if contributor_type:
            entry["type"] = contributor_type
        return entry


def normalize_orcid(raw: str) -> str:
    """Extract and normalize a 16-digit ORCID identifier (XXXX-XXXX-XXXX-XXXX)."""
    if not raw:
        return ""
    match = ORCID_REGEX.search(str(raw).strip())
    return match.group(1).upper() if match else ""


def clean_text(val: Any) -> str:
    """Clean cell text and repair known mojibake characters."""
    if val is None:
        return ""
    text = str(val).strip()
    for bad, good in NAME_CLEANUP_MAP.items():
        text = text.replace(bad, good)
    return text


def split_multiselect(val: Any) -> list[str]:
    """Split Smartsheet multi-select or comma/newline separated values."""
    text = clean_text(val)
    if not text:
        return []
    parts = re.split(r"[\r\n,;]+", text)
    return [p.strip() for p in parts if p.strip()]


def load_citation_cff_orcids(cff_path: Path) -> dict[str, dict[str, str]]:
    """Parse CITATION.cff to extract known ORCIDs and affiliations by full name."""
    lookup: dict[str, dict[str, str]] = {}
    if not cff_path.exists():
        return lookup

    content = cff_path.read_text(encoding="utf-8")
    in_authors = False
    current: dict[str, str] = {}

    for line in content.splitlines():
        if line.startswith("authors:"):
            in_authors = True
            continue
        if in_authors and line and not line.startswith(" "):
            break
        if not in_authors:
            continue

        stripped = line.strip()
        if stripped.startswith("- given-names:"):
            if current.get("given-names") and current.get("family-names"):
                full = f"{current['given-names']} {current['family-names']}".lower()
                lookup[full] = current
            current = {"given-names": stripped.split(":", 1)[1].strip().strip('"')}
        elif stripped.startswith("family-names:"):
            current["family-names"] = stripped.split(":", 1)[1].strip().strip('"')
        elif stripped.startswith("orcid:"):
            raw_orcid = stripped.split(":", 1)[1].strip().strip('"')
            current["orcid"] = normalize_orcid(raw_orcid)
        elif stripped.startswith("affiliation:") and ">" not in stripped:
            current["affiliation"] = stripped.split(":", 1)[1].strip().strip('"')

    if current.get("given-names") and current.get("family-names"):
        full = f"{current['given-names']} {current['family-names']}".lower()
        lookup[full] = current

    return lookup


def fetch_smartsheet_live(sheet_id: str, token: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Fetch rows and column ID mapping directly from the live Smartsheet REST API."""
    url = f"{SMARTSHEET_API_BASE}/sheets/{sheet_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        sheet_data = json.loads(resp.read().decode("utf-8"))

    col_id_to_title: dict[int, str] = {}
    col_title_to_id: dict[str, int] = {}
    for col in sheet_data.get("columns", []):
        cid = int(col["id"])
        title = col["title"].strip()
        col_id_to_title[cid] = title
        col_title_to_id[title] = cid

    rows: list[dict[str, Any]] = []
    for row in sheet_data.get("rows", []):
        row_dict: dict[str, Any] = {"_row_id": row["id"], "_row_number": row.get("rowNumber")}
        for cell in row.get("cells", []):
            col_title = col_id_to_title.get(int(cell["columnId"]), "")
            val = cell.get("displayValue") if "displayValue" in cell else cell.get("value")
            row_dict[col_title] = val
        rows.append(row_dict)

    return rows, col_title_to_id


def read_smartsheet_xlsx(xlsx_path: Path) -> list[dict[str, Any]]:
    """Read a Smartsheet Excel (.xlsx) export using Python's built-in zipfile + XML parser."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(xlsx_path) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("s:si", ns):
                shared_strings.append("".join(t.text or "" for t in si.findall(".//s:t", ns)))

        sheet_root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        raw_rows: list[dict[str, str]] = []
        for row_el in sheet_root.findall(".//s:row", ns):
            cell_map: dict[str, str] = {}
            for cell_el in row_el.findall("s:c", ns):
                ref = cell_el.attrib.get("r", "")
                col_letters = re.match(r"[A-Z]+", ref).group(0) if ref else ""
                cell_type = cell_el.attrib.get("t")
                v_el = cell_el.find("s:v", ns)
                is_el = cell_el.find("s:is", ns)
                if cell_type == "s" and v_el is not None and v_el.text is not None:
                    val = shared_strings[int(v_el.text)]
                elif is_el is not None:
                    val = "".join(x.text or "" for x in is_el.findall(".//s:t", ns))
                elif v_el is not None and v_el.text is not None:
                    val = v_el.text
                else:
                    val = ""
                cell_map[col_letters] = val
            raw_rows.append(cell_map)

    if not raw_rows:
        return []

    header_map = raw_rows[0]
    parsed_rows: list[dict[str, Any]] = []
    for idx, r in enumerate(raw_rows[1:], start=2):
        row_dict: dict[str, Any] = {"_row_id": idx, "_row_number": idx}
        for col_letter, col_title in header_map.items():
            row_dict[col_title.strip()] = r.get(col_letter, "")
        parsed_rows.append(row_dict)
    return parsed_rows


def read_smartsheet_csv(csv_path: Path) -> list[dict[str, Any]]:
    """Read a Smartsheet CSV export."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, Any]] = []
        for idx, row in enumerate(reader, start=2):
            r = dict(row)
            r["_row_id"] = idx
            r["_row_number"] = idx
            rows.append(r)
        return rows


def parse_contributor_rows(
    raw_rows: list[dict[str, Any]],
    cff_lookup: dict[str, dict[str, str]],
) -> list[ContributorRecord]:
    """Convert raw Smartsheet rows into validated ContributorRecord instances."""
    records: list[ContributorRecord] = []
    seen_names: set[str] = set()

    for r in raw_rows:
        full_name = clean_text(r.get("Name"))
        if not full_name:
            continue

        # Skip obvious duplicate Slack-only rows (e.g., "Fraser Murison Smith - Slack")
        if full_name.endswith("- Slack"):
            continue

        first_name = clean_text(r.get("First name as used"))
        last_name = clean_text(r.get("Last name"))
        anomalies: list[str] = []

        if "\ufffd" in str(r.get("Name", "")) or "\ufffd" in str(r.get("Last name", "")):
            anomalies.append("Character encoding issue repaired in name")

        # Check if first_name and last_name appear swapped relative to Name
        if first_name and last_name and full_name:
            name_parts = full_name.split()
            if (
                len(name_parts) >= 2
                and first_name.lower() != name_parts[0].lower()
                and last_name.lower() == name_parts[0].lower()
            ):
                anomalies.append(
                    f"First/Last name columns appear swapped or misspelled "
                    f"(Name='{full_name}', First='{first_name}', Last='{last_name}')"
                )
                first_name, last_name = name_parts[0], " ".join(name_parts[1:])

        if not first_name or not last_name:
            parts = full_name.split()
            first_name = first_name or (parts[0] if parts else "")
            last_name = last_name or (" ".join(parts[1:]) if len(parts) > 1 else "")

        # Use formal academic given name for Edward S. Spang (esspang@ucdavis.edu)
        if clean_text(r.get("Email address")).startswith("esspang@"):
            first_name = "Edward S."
            full_name = "Edward S. Spang"

        orcid = normalize_orcid(clean_text(r.get("orcid.org/") or r.get("ORCID")))
        orcid_source = "smartsheet" if orcid else ""

        # Enrich from CITATION.cff if missing in Smartsheet
        cff_key = f"{first_name} {last_name}".lower()
        cff_match = cff_lookup.get(cff_key) or cff_lookup.get(full_name.lower())
        if not orcid and cff_match and cff_match.get("orcid"):
            orcid = cff_match["orcid"]
            orcid_source = "citation.cff"
            anomalies.append(f"ORCID backfilled from CITATION.cff ({orcid}); missing in Smartsheet")

        org = clean_text(r.get("Organization"))
        if not org:
            anomalies.append("Missing Organization/Affiliation")

        raw_email = clean_text(r.get("Email address"))
        # If multiple emails in one cell, take the first one
        email = re.split(r"[,;\s]+", raw_email)[0].strip() if raw_email else ""

        tags = split_multiselect(r.get("Tags"))
        groups = split_multiselect(r.get("Group(s)"))
        roles = clean_text(r.get("Role(s)"))
        active = clean_text(r.get("Active?"))
        if not active:
            anomalies.append("Blank 'Active?' status in Smartsheet")

        # Read proposed explicit Zenodo governance columns if present
        zenodo_role = clean_text(r.get("Zenodo Release Role") or r.get("Zenodo Role"))
        raw_order = clean_text(r.get("Zenodo Author Order") or r.get("Author Order"))
        try:
            zenodo_order_tier = int(float(raw_order)) if raw_order else 99
        except ValueError:
            zenodo_order_tier = 99

        pub_releases = split_multiselect(
            r.get("Publication Releases") or r.get("Releases")
        )

        norm_name = full_name.lower()
        if norm_name in seen_names:
            anomalies.append("Duplicate name entry in Smartsheet")
        seen_names.add(norm_name)

        records.append(
            ContributorRecord(
                row_id=r.get("_row_id", ""),
                line_id=clean_text(r.get("line ID")),
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                organization=org,
                email=email,
                orcid=orcid,
                orcid_source=orcid_source,
                active=active,
                core_team=bool(clean_text(r.get("Core team"))),
                ecr=bool(clean_text(r.get("ECR?"))),
                tags=tags,
                groups=groups,
                roles=roles,
                contribution_description=clean_text(
                    r.get("Project contribution description")
                ),
                zenodo_role=zenodo_role,
                zenodo_order_tier=zenodo_order_tier,
                publication_releases=pub_releases,
                anomalies=anomalies,
            )
        )

    return records


def classify_for_zenodo(
    records: list[ContributorRecord],
    release_tag: str | None = None,
) -> tuple[list[ContributorRecord], list[tuple[ContributorRecord, str]], list[ContributorRecord]]:
    """Classify records into Zenodo `creators`, `contributors` (with role), and `excluded`.

    Supports two modes automatically:
    1. Explicit Mode (once the `Zenodo Release Role` column is populated in Smartsheet).
    2. Heuristic Preview Mode (when `Zenodo Release Role` is not yet added to Smartsheet),
       using `Tags` ('Data contributor', 'PI / Co-PI', 'Core team') and research `Group(s)`.
    """
    has_explicit_roles = any(r.zenodo_role for r in records)
    creators: list[ContributorRecord] = []
    contributors: list[tuple[ContributorRecord, str]] = []
    excluded: list[ContributorRecord] = []

    for r in records:
        if release_tag and r.publication_releases and release_tag not in r.publication_releases:
            excluded.append(r)
            continue

        if has_explicit_roles:
            role_val = r.zenodo_role.strip()
            if not role_val or role_val.lower() in {"exclude", "none", "no", "na"}:
                excluded.append(r)
            elif role_val.lower().startswith("creator"):
                creators.append(r)
                # Optional secondary DataCite contributor role (e.g. "Creator | DataCurator")
                if ":" in role_val or "|" in role_val:
                    sub_role = re.split(r"[:|]", role_val, maxsplit=1)[1].strip()
                    if sub_role in VALID_ZENODO_CONTRIBUTOR_TYPES:
                        contributors.append((r, sub_role))
            elif role_val.lower().startswith("contributor"):
                sub_role = (
                    re.split(r"[:|-]", role_val, maxsplit=1)[1].strip()
                    if any(sep in role_val for sep in (":", "|", "-"))
                    else "ProjectMember"
                )
                if sub_role not in VALID_ZENODO_CONTRIBUTOR_TYPES:
                    sub_role = "ProjectMember"
                contributors.append((r, sub_role))
            elif role_val in VALID_ZENODO_CONTRIBUTOR_TYPES:
                contributors.append((r, role_val))
            else:
                creators.append(r)
        else:
            # Heuristic mode based on current Smartsheet columns
            is_admin_or_comms_only = bool(r.groups) and all(
                g in {"Administrative", "Communications", "pending"} for g in r.groups
            )
            is_research_aim = any(
                g.startswith("Aim ") or "Portal" in g for g in r.groups
            )

            if r.active == "No" and "Data contributor" not in r.tags:
                excluded.append(r)
                continue
            if is_admin_or_comms_only and "Data contributor" not in r.tags:
                excluded.append(r)
                continue

            # Determine heuristic tier & role for preview
            if "Data contributor" in r.tags:
                r.zenodo_order_tier = min(r.zenodo_order_tier, 1)
                creators.append(r)
                contributors.append((r, "DataCurator"))
            elif "PI / Co-PI" in r.tags or "Lead" in r.roles or "PI" in r.roles:
                r.zenodo_order_tier = min(r.zenodo_order_tier, 3)
                creators.append(r)
                contributors.append((r, "ProjectLeader"))
            elif r.core_team and is_research_aim:
                r.zenodo_order_tier = min(r.zenodo_order_tier, 2)
                creators.append(r)
                contributors.append((r, "Researcher"))
            elif is_research_aim:
                contributors.append((r, "DataCollector"))
            else:
                excluded.append(r)

    # Sort creators deterministically by (zenodo_order_tier, last_name, first_name)
    creators.sort(key=lambda x: (x.zenodo_order_tier, x.last_name.lower(), x.first_name.lower()))
    contributors.sort(key=lambda x: (x[0].last_name.lower(), x[0].first_name.lower()))
    return creators, contributors, excluded


def send_smartsheet_orcid_update_requests(
    sheet_id: str,
    token: str,
    col_title_to_id: dict[str, int],
    missing_orcid_records: list[ContributorRecord],
    dry_run: bool = True,
) -> list[dict[str, Any]]:
    """Trigger Smartsheet Update Requests to contributors missing an ORCID ID."""
    orcid_col_id = col_title_to_id.get("orcid.org/") or col_title_to_id.get("ORCID")
    org_col_id = col_title_to_id.get("Organization")
    name_col_id = col_title_to_id.get("Name")

    if not orcid_col_id:
        raise ValueError("Could not find 'orcid.org/' column ID in Smartsheet.")

    column_ids = [cid for cid in (name_col_id, org_col_id, orcid_col_id) if cid]
    results: list[dict[str, Any]] = []

    for rec in missing_orcid_records:
        if not rec.email:
            continue
        payload = {
            "sendTo": [{"email": rec.email}],
            "subject": "Action Required: Add your ORCID ID for the BioCIRV Zenodo Dataset Release",
            "message": (
                f"Hi {rec.first_name},\n\n"
                "We are preparing the first public BioCIRV dataset release on Zenodo (which mints a citable DOI). "
                "Please enter your 16-digit ORCID iD (e.g., 0000-0002-1825-0097) and verify your institutional "
                "affiliation in this form so you are accurately credited on the release."
            ),
            "ccMe": False,
            "rowIds": [int(rec.row_id)],
            "columnIds": column_ids,
            "includeAttachments": False,
            "includeDiscussions": False,
        }
        if dry_run:
            results.append({"email": rec.email, "row_id": rec.row_id, "status": "dry_run", "payload": payload})
        else:
            url = f"{SMARTSHEET_API_BASE}/sheets/{sheet_id}/updaterequests"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
            results.append({"email": rec.email, "row_id": rec.row_id, "status": "sent", "response": resp_data})

    return results


def build_zenodo_metadata(
    creators: list[ContributorRecord],
    contributors: list[tuple[ContributorRecord, str]],
    version: str = "0.1.0",
    license_id: str = "cc-by-4.0",
) -> dict[str, Any]:
    """Build the Zenodo REST API deposition metadata JSON object."""
    return {
        "metadata": {
            "title": "BioCIRV Public Biomass Characterization Dataset",
            "upload_type": "dataset",
            "description": (
                "Public analytical characterization dataset (proximate, ultimate, compositional, "
                "calorimetry, XRF, XRD, ICP, and fermentation/pretreatment records) from the "
                "BioCircular Valley (BioCIRV / Cal BioScape) initiative in California's "
                "Northern San Joaquin Valley."
            ),
            "version": version,
            "access_right": "open",
            "license": license_id,
            "creators": [c.to_zenodo_person() for c in creators],
            "contributors": [
                rec.to_zenodo_person(contributor_type=ctype)
                for rec, ctype in contributors
            ],
            "keywords": [
                "bioeconomy",
                "biomass characterization",
                "feedstocks",
                "California",
                "Northern San Joaquin Valley",
                "proximate analysis",
                "compositional analysis",
                "Cal BioScape",
            ],
            "related_identifiers": [
                {
                    "identifier": "10.5281/zenodo.19443582",
                    "relation": "isCompiledBy",
                    "resource_type": "software",
                },
                {
                    "identifier": "https://github.com/sustainability-software-lab/ca-biositing",
                    "relation": "isSupplementTo",
                    "resource_type": "software",
                },
            ],
        }
    }


def generate_audit_report(
    all_records: list[ContributorRecord],
    creators: list[ContributorRecord],
    contributors: list[tuple[ContributorRecord, str]],
    excluded: list[ContributorRecord],
) -> str:
    """Generate a Markdown audit report of Smartsheet contributor readiness."""
    active_records = [r for r in all_records if r.active == "Yes"]
    with_orcid_smartsheet = [r for r in all_records if r.orcid_source == "smartsheet"]
    with_orcid_cff = [r for r in all_records if r.orcid_source == "citation.cff"]
    creators_missing_orcid = [c for c in creators if not c.orcid]

    lines = [
        "# BioCIRV Zenodo Authorship & Smartsheet Audit Report",
        "",
        "## 1. Executive Summary Statistics",
        "",
        f"- **Total Named Rows in Smartsheet:** {len(all_records)}",
        f"- **Active Contributors (`Active? = Yes`):** {len(active_records)}",
        f"- **Tagged `Data contributor` in Smartsheet:** {sum(1 for r in all_records if 'Data contributor' in r.tags)}",
        f"- **ORCIDs Populated in Smartsheet (`orcid.org/`):** {len(with_orcid_smartsheet)} / {len(all_records)} "
        f"({', '.join(r.full_name for r in with_orcid_smartsheet) or 'None'})",
        f"- **Additional ORCIDs Backfilled from `CITATION.cff`:** {len(with_orcid_cff)} "
        f"({', '.join(r.full_name for r in with_orcid_cff) or 'None'})",
        f"- **Candidate Zenodo `creators` (Byline Authors):** {len(creators)} "
        f"({len(creators) - len(creators_missing_orcid)} with ORCID, {len(creators_missing_orcid)} missing ORCID)",
        f"- **Candidate Zenodo `contributors` (DataCite Roles):** {len(contributors)}",
        f"- **Excluded Rows (Inactive / Admin / Comms only):** {len(excluded)}",
        "",
        "---",
        "",
        "## 2. Data Quality & Anomaly Flags in Current Smartsheet",
        "",
    ]

    anomalous = [r for r in all_records if r.anomalies]
    if not anomalous:
        lines.append("No data quality anomalies detected.")
    else:
        lines.append("| Line ID | Name | Email | Detected Issue |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for r in anomalous:
            for issue in r.anomalies:
                lines.append(f"| `{r.line_id}` | {r.full_name} | `{r.email}` | {issue} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Candidate Zenodo `creators` (Primary Byline Preview)",
            "",
            "> **Note:** Currently sorted by Heuristic Tier (`Tier 1` = tagged `Data contributor`, "
            "`Tier 2` = Core Team Aim 1/2/3 Researchers, `Tier 3` = PIs / Co-PIs / Leads), then alphabetically by last name. "
            "Once the `Zenodo Release Role` and `Zenodo Author Order` columns are added to Smartsheet, "
            "this table will reflect explicit ordering.",
            "",
            "| Tier | Zenodo Formatted Name | Organization | ORCID | Group(s) | Current Smartsheet Tags |",
            "| :---: | :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for c in creators:
        orcid_badge = f"`{c.orcid}` ({c.orcid_source})" if c.orcid else "**MISSING**"
        groups_str = ", ".join(c.groups)
        tags_str = ", ".join(c.tags)
        lines.append(
            f"| {c.zenodo_order_tier} | **{c.zenodo_formatted_name}** | {c.organization} | "
            f"{orcid_badge} | {groups_str} | {tags_str} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Additional Aim 1–3 Contributors (`Active? = Yes` or Research Group, Not in Core Team)",
            "",
            "| Zenodo Formatted Name | Suggested DataCite Role | Active? | Organization | Group(s) | Role(s) |",
            "| :--- | :--- | :---: | :--- | :--- | :--- |",
        ]
    )

    creator_ids = {c.line_id for c in creators}
    for rec, ctype in contributors:
        if rec.line_id in creator_ids:
            continue
        lines.append(
            f"| {rec.zenodo_formatted_name} | `{ctype}` | {rec.active or 'Blank'} | "
            f"{rec.organization} | {', '.join(rec.groups)} | {rec.roles} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync BioCIRV contributor metadata from Smartsheet to Zenodo JSON."
    )
    parser.add_argument(
        "--smartsheet-id",
        default=os.environ.get("SMARTSHEET_SHEET_ID", ""),
        help="Smartsheet Sheet ID (or set SMARTSHEET_SHEET_ID env var).",
    )
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=None,
        help="Fallback path to a local Smartsheet .xlsx export for offline testing.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Fallback path to a local Smartsheet .csv export for offline testing.",
    )
    parser.add_argument(
        "--citation-cff",
        type=Path,
        default=Path("CITATION.cff"),
        help="Path to CITATION.cff for ORCID cross-referencing (default: CITATION.cff).",
    )
    parser.add_argument(
        "--release",
        default=None,
        help="Filter by tag in 'Publication Releases' column (e.g., 'Zenodo Dataset v1').",
    )
    parser.add_argument(
        "--version",
        default="0.1.0",
        help="Dataset semantic version for Zenodo metadata (default: 0.1.0).",
    )
    parser.add_argument(
        "--license",
        default="cc-by-4.0",
        help="Zenodo license identifier (default: cc-by-4.0).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("scripts/zenodo/zenodo_metadata.preview.json"),
        help="Output path for Zenodo metadata JSON.",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=Path("scripts/zenodo/author_audit_report.md"),
        help="Output path for Markdown audit report.",
    )
    parser.add_argument(
        "--send-orcid-requests",
        action="store_true",
        help="Trigger Smartsheet Update Requests to contributors missing ORCIDs.",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually send Smartsheet Update Requests when --send-orcid-requests is set.",
    )
    args = parser.parse_args()

    token = os.environ.get("SMARTSHEET_ACCESS_TOKEN", "")
    col_title_to_id: dict[str, int] = {}

    if args.smartsheet_id and token:
        print(f"Fetching live Smartsheet {args.smartsheet_id} via Smartsheet REST API...")
        raw_rows, col_title_to_id = fetch_smartsheet_live(args.smartsheet_id, token)
    elif args.xlsx and args.xlsx.exists():
        print(f"Reading local Smartsheet XLSX export: {args.xlsx}...")
        raw_rows = read_smartsheet_xlsx(args.xlsx)
    elif args.csv and args.csv.exists():
        print(f"Reading local Smartsheet CSV export: {args.csv}...")
        raw_rows = read_smartsheet_csv(args.csv)
    else:
        raise SystemExit(
            "Error: Provide either SMARTSHEET_ACCESS_TOKEN + SMARTSHEET_SHEET_ID (for live API sync) "
            "or --xlsx / --csv (for local offline testing)."
        )

    cff_lookup = load_citation_cff_orcids(args.citation_cff)
    records = parse_contributor_rows(raw_rows, cff_lookup)
    creators, contributors, excluded = classify_for_zenodo(records, release_tag=args.release)

    metadata = build_zenodo_metadata(
        creators=creators,
        contributors=contributors,
        version=args.version,
        license_id=args.license,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote Zenodo metadata payload ({len(creators)} creators, {len(contributors)} contributors) to {args.output_json}")

    report_md = generate_audit_report(records, creators, contributors, excluded)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(report_md, encoding="utf-8")
    print(f"Wrote Smartsheet authorship audit report to {args.output_report}")

    if args.send_orcid_requests:
        if not (args.smartsheet_id and token):
            raise SystemExit("Error: --send-orcid-requests requires live SMARTSHEET_ACCESS_TOKEN and --smartsheet-id.")
        missing_orcids = [c for c in creators if not c.orcid]
        reqs = send_smartsheet_orcid_update_requests(
            sheet_id=args.smartsheet_id,
            token=token,
            col_title_to_id=col_title_to_id,
            missing_orcid_records=missing_orcids,
            dry_run=not args.no_dry_run,
        )
        mode_str = "Sent" if args.no_dry_run else "Prepared (dry-run)"
        print(f"{mode_str} {len(reqs)} Smartsheet ORCID update requests.")


if __name__ == "__main__":
    main()
