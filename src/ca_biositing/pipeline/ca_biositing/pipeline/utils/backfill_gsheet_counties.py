"""Credentialed Google Sheets county writeback helper for FieldSample metadata.

This module resolves ``Sampling_County`` (in worksheet ``02_Sample_Desc``) and
``Prod_County`` (in worksheet ``04_Producers``) from raw sub-county columns in
``SampleMetadata_v03-BioCirV`` using the offline-first California county
resolver (`resolve_county_geoid`) and writes **only** canonical California
county names back to the Google Sheet.

Privacy invariant:
- Never logs or prints ``Sample_name``, street addresses, cities, ZIP codes,
  coordinates, or location descriptions.
- Never writes any local file.
"""

from __future__ import annotations

import argparse
from collections import Counter
import logging
import os
import re
from typing import Any, Mapping, Optional, Sequence

import gspread
from gspread.exceptions import SpreadsheetNotFound
from gspread.utils import rowcol_to_a1

from ca_biositing.pipeline.utils.geo_utils import (
    get_canonical_ca_county_name,
    resolve_county_geoid,
)

logger = logging.getLogger(__name__)

DEFAULT_GSHEET_NAME = "SampleMetadata_v03-BioCirV"
DEFAULT_TABS: tuple[str, str] = ("02_Sample_Desc", "04_Producers")

WORKSHEET_COUNTY_SPECS: dict[str, dict[str, Any]] = {
    "02_Sample_Desc": {
        "county_header": "Sampling_County",
        "county_aliases": ("sampling_county",),
        "latlong": ("sampling_latlong", "sampling_lat_long", "latlong"),
        "zip_code": ("sampling_zip", "sampling_zipcode", "sampling_zip_code"),
        "city": ("sampling_city",),
        "street": ("sampling_street",),
        "location_desc": ("sampling_location",),
    },
    "04_Producers": {
        "county_header": "Prod_County",
        "county_aliases": ("prod_county", "producer_county"),
        "latlong": ("prod_latlong", "prod_lat_long"),
        "zip_code": ("prod_zip", "prod_zipcode", "prod_zip_code"),
        "city": ("prod_city",),
        "street": ("prod_street",),
        "location_desc": ("prod_location",),
    },
}

_EMPTY_SENTINELS = {"", "nan", "none", "null", "n/a", "na", "-"}


def _normalize_header(header: object) -> str:
    """Normalize a worksheet column header for case-insensitive matching."""
    return re.sub(r"[\s\-]+", "_", str(header or "").strip().lower())


def _is_nonempty_cell(val: object) -> bool:
    """Return True when a worksheet cell contains a meaningful non-empty string."""
    if val is None:
        return False
    cleaned = str(val).strip()
    return cleaned.lower() not in _EMPTY_SENTINELS


def _cell_at(row: Sequence[Any], col_idx: int | None) -> str | None:
    """Safely extract a stripped cell value at ``col_idx`` or return ``None``."""
    if col_idx is None or col_idx < 0 or col_idx >= len(row):
        return None
    val = row[col_idx]
    if not _is_nonempty_cell(val):
        return None
    return str(val).strip()


def _first_cell(row: Sequence[Any], col_indices: Sequence[int]) -> str | None:
    """Return the first non-empty cell value among candidate column indices."""
    for idx in col_indices:
        val = _cell_at(row, idx)
        if val is not None:
            return val
    return None


def _find_matching_col_indices(
    normalized_headers: Sequence[str],
    candidate_names: Sequence[str],
) -> list[int]:
    """Return all 0-based column indices matching ``candidate_names`` in priority order."""
    indices: list[int] = []
    for candidate in candidate_names:
        norm_cand = _normalize_header(candidate)
        for idx, header in enumerate(normalized_headers):
            if header == norm_cand and idx not in indices:
                indices.append(idx)
    return indices


def backfill_worksheet_counties(
    worksheet: Any,
    tab_name: str,
    *,
    dry_run: bool = True,
    allow_live_geocoding: bool = False,
) -> dict[str, Any]:
    """Resolve and optionally write back canonical California county names for one worksheet.

    Args:
        worksheet: A ``gspread.Worksheet`` (or compatible in-memory double) supporting
            ``get_all_values()`` and ``batch_update()``.
        tab_name: Worksheet tab name (must be a key in ``WORKSHEET_COUNTY_SPECS``).
        dry_run: When ``True`` (default), compute summary counts without mutating
            the worksheet.
        allow_live_geocoding: When ``True``, allow ``resolve_county_geoid`` to use
            the external geocoder fallback if ``GOOGLE_MAPS_API_KEY`` is set.

    Returns:
        Aggregate summary dictionary containing only county-level counts and safe metadata.
    """
    if tab_name not in WORKSHEET_COUNTY_SPECS:
        raise ValueError(
            f"Unsupported worksheet tab '{tab_name}'. "
            f"Expected one of {sorted(WORKSHEET_COUNTY_SPECS)}."
        )

    spec = WORKSHEET_COUNTY_SPECS[tab_name]
    county_header: str = spec["county_header"]

    all_values = worksheet.get_all_values()
    if not all_values:
        return {
            "tab_name": tab_name,
            "county_header": county_header,
            "dry_run": dry_run,
            "created_header": False,
            "total_rows": 0,
            "already_populated_rows": 0,
            "resolved_rows": 0,
            "unresolved_rows": 0,
            "updated_cells": 0,
            "county_counts": {},
        }

    headers = list(all_values[0])
    normalized_headers = [_normalize_header(h) for h in headers]

    county_col_matches = _find_matching_col_indices(
        normalized_headers,
        (county_header, *spec.get("county_aliases", ())),
    )
    if county_col_matches:
        county_col_idx_0based = county_col_matches[0]
        created_header = False
    else:
        county_col_idx_0based = len(headers)
        created_header = True

    col_map: dict[str, list[int]] = {
        field: _find_matching_col_indices(normalized_headers, spec.get(field, ()))
        for field in ("latlong", "zip_code", "city", "street", "location_desc")
    }

    total_rows = 0
    already_populated_rows = 0
    resolved_rows = 0
    unresolved_rows = 0
    county_counts: Counter[str] = Counter()
    pending_updates: list[tuple[int, int, str]] = []

    for row_idx_1based, row in enumerate(all_values[1:], start=2):
        if not any(_is_nonempty_cell(cell) for cell in row):
            continue

        total_rows += 1

        existing_county = (
            _cell_at(row, county_col_idx_0based) if not created_header else None
        )
        if existing_county is not None:
            already_populated_rows += 1
            continue

        geoid = resolve_county_geoid(
            county=None,
            latlong=_first_cell(row, col_map["latlong"]),
            zip_code=_first_cell(row, col_map["zip_code"]),
            city=_first_cell(row, col_map["city"]),
            street=_first_cell(row, col_map["street"]),
            location_desc=_first_cell(row, col_map["location_desc"]),
            allow_external_geocode=allow_live_geocoding,
        )

        county_name = (
            get_canonical_ca_county_name(geoid)
            if geoid and geoid != "06000"
            else None
        )
        if county_name and county_name not in {"California", "State of California"}:
            pending_updates.append((row_idx_1based, county_col_idx_0based, county_name))
            resolved_rows += 1
            county_counts[county_name] += 1
        else:
            unresolved_rows += 1

    updated_cells = 0
    if not dry_run and (pending_updates or created_header):
        if created_header and hasattr(worksheet, "add_cols"):
            current_col_count = getattr(worksheet, "col_count", len(headers))
            if isinstance(current_col_count, int) and county_col_idx_0based >= current_col_count:
                worksheet.add_cols(county_col_idx_0based - current_col_count + 1)

        batch_payload: list[dict[str, Any]] = []
        if created_header:
            batch_payload.append(
                {
                    "range": rowcol_to_a1(1, county_col_idx_0based + 1),
                    "values": [[county_header]],
                }
            )
        for r_1based, c_0based, val in pending_updates:
            batch_payload.append(
                {
                    "range": rowcol_to_a1(r_1based, c_0based + 1),
                    "values": [[val]],
                }
            )

        if batch_payload:
            if hasattr(worksheet, "batch_update"):
                worksheet.batch_update(batch_payload, value_input_option="USER_ENTERED")
            elif hasattr(worksheet, "update_cell"):
                if created_header:
                    worksheet.update_cell(1, county_col_idx_0based + 1, county_header)
                for r_1based, c_0based, val in pending_updates:
                    worksheet.update_cell(r_1based, c_0based + 1, val)
            updated_cells = len(batch_payload)

    summary: dict[str, Any] = {
        "tab_name": tab_name,
        "county_header": county_header,
        "dry_run": dry_run,
        "created_header": created_header,
        "total_rows": total_rows,
        "already_populated_rows": already_populated_rows,
        "resolved_rows": resolved_rows,
        "unresolved_rows": unresolved_rows,
        "updated_cells": updated_cells,
        "county_counts": dict(sorted(county_counts.items())),
    }

    mode_label = "DRY-RUN" if dry_run else "APPLIED"
    logger.info(
        "[%s] Worksheet %s (%s): total_rows=%d, already_populated=%d, "
        "resolved=%d, unresolved=%d, updated_cells=%d, county_counts=%s",
        mode_label,
        tab_name,
        county_header,
        total_rows,
        already_populated_rows,
        resolved_rows,
        unresolved_rows,
        updated_cells,
        summary["county_counts"],
    )
    return summary


def _open_spreadsheet(
    gsheet_name: str,
    credentials_path: str,
    worksheet_client: Any = None,
) -> Any:
    """Open a Google Sheet via ``worksheet_client`` or ``gspread.service_account``."""
    if worksheet_client is not None:
        if hasattr(worksheet_client, "open"):
            return worksheet_client.open(gsheet_name)
        return worksheet_client

    gc = gspread.service_account(filename=credentials_path)
    try:
        return gc.open(gsheet_name)
    except SpreadsheetNotFound:
        if re.fullmatch(r"[A-Za-z0-9_-]{20,}", gsheet_name):
            return gc.open_by_key(gsheet_name)
        raise


def _get_worksheet(spreadsheet_or_mapping: Any, tab_name: str) -> Any:
    """Retrieve a worksheet by ``tab_name`` from a Spreadsheet, dict, or Worksheet."""
    if isinstance(spreadsheet_or_mapping, Mapping):
        return spreadsheet_or_mapping[tab_name]
    if hasattr(spreadsheet_or_mapping, "worksheet"):
        return spreadsheet_or_mapping.worksheet(tab_name)
    if hasattr(spreadsheet_or_mapping, "get_all_values"):
        return spreadsheet_or_mapping
    raise TypeError(
        f"Cannot resolve worksheet '{tab_name}' from object of type "
        f"{type(spreadsheet_or_mapping).__name__}."
    )


def backfill_gsheet_counties(
    *,
    gsheet_name: str = DEFAULT_GSHEET_NAME,
    tabs: Sequence[str] = DEFAULT_TABS,
    dry_run: bool = True,
    allow_live_geocoding: bool = False,
    credentials_path: Optional[str] = None,
    worksheet_client: Optional[Any] = None,
) -> dict[str, Any]:
    """Backfill canonical California county names across target Google Sheet tabs.

    Never logs or prints sub-county addresses, coordinates, ZIP codes, cities,
    or sample names, and never writes any local file.
    """
    resolved_credentials_path = (
        credentials_path
        or os.getenv("CREDENTIALS_PATH")
        or "credentials.json"
    )
    spreadsheet = _open_spreadsheet(
        gsheet_name=gsheet_name,
        credentials_path=resolved_credentials_path,
        worksheet_client=worksheet_client,
    )

    tab_summaries: dict[str, dict[str, Any]] = {}
    for tab_name in tabs:
        worksheet = _get_worksheet(spreadsheet, tab_name)
        tab_summaries[tab_name] = backfill_worksheet_counties(
            worksheet,
            tab_name,
            dry_run=dry_run,
            allow_live_geocoding=allow_live_geocoding,
        )

    aggregate_summary: dict[str, Any] = {
        "gsheet_name": gsheet_name,
        "dry_run": dry_run,
        "tabs": tab_summaries,
        "total_resolved_rows": sum(s["resolved_rows"] for s in tab_summaries.values()),
        "total_unresolved_rows": sum(s["unresolved_rows"] for s in tab_summaries.values()),
        "total_already_populated_rows": sum(
            s["already_populated_rows"] for s in tab_summaries.values()
        ),
        "total_updated_cells": sum(s["updated_cells"] for s in tab_summaries.values()),
    }

    mode_label = "DRY-RUN" if dry_run else "APPLIED"
    logger.info(
        "[%s] Google Sheet county backfill complete for '%s': "
        "resolved=%d, already_populated=%d, unresolved=%d, updated_cells=%d",
        mode_label,
        gsheet_name,
        aggregate_summary["total_resolved_rows"],
        aggregate_summary["total_already_populated_rows"],
        aggregate_summary["total_unresolved_rows"],
        aggregate_summary["total_updated_cells"],
    )
    return aggregate_summary


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    worksheet_client: Optional[Any] = None,
) -> int:
    """CLI entrypoint for backfilling county columns in SampleMetadata_v03-BioCirV."""
    parser = argparse.ArgumentParser(
        description=(
            "Resolve Sampling_County (02_Sample_Desc) and Prod_County (04_Producers) "
            "from sub-county fields in Google Sheets and write back only canonical "
            "California county names."
        )
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report aggregate county counts without modifying Google Sheets (default).",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Batch-update resolved canonical county names in Google Sheets.",
    )
    parser.add_argument(
        "--gsheet-name",
        default=DEFAULT_GSHEET_NAME,
        help=f"Google Sheet name or key (default: {DEFAULT_GSHEET_NAME}).",
    )
    parser.add_argument(
        "--tab",
        dest="tabs",
        action="append",
        choices=sorted(WORKSHEET_COUNTY_SPECS),
        help="Worksheet tab(s) to process (repeatable; defaults to both 02_Sample_Desc and 04_Producers).",
    )
    parser.add_argument(
        "--credentials-path",
        default=None,
        help="Path to service account JSON credentials (defaults to $CREDENTIALS_PATH or credentials.json).",
    )
    parser.add_argument(
        "--allow-live-geocoding",
        action="store_true",
        default=False,
        help="Allow external Google Maps geocoding fallback when offline lookup returns 06000.",
    )

    args = parser.parse_args(argv)
    dry_run = not args.apply
    tabs = tuple(args.tabs) if args.tabs else DEFAULT_TABS

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    backfill_gsheet_counties(
        gsheet_name=args.gsheet_name,
        tabs=tabs,
        dry_run=dry_run,
        allow_live_geocoding=args.allow_live_geocoding,
        credentials_path=args.credentials_path,
        worksheet_client=worksheet_client,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
