"""Unit tests for the credentialed Google Sheets county writeback helper."""

from __future__ import annotations

import copy
import logging
import re
from typing import Any

import gspread

from ca_biositing.pipeline.utils.backfill_gsheet_counties import (
    backfill_gsheet_counties,
    backfill_worksheet_counties,
    main,
)

_A1_RE = re.compile(r"^([A-Z]+)(\d+)$")


def _a1_to_rowcol_0based(a1: str) -> tuple[int, int]:
    """Convert a single-cell A1 reference (e.g. ``'G2'``) to 0-based ``(row, col)``."""
    match = _A1_RE.fullmatch(a1.strip().upper())
    if not match:
        raise ValueError(f"Unsupported A1 range in fake worksheet: {a1!r}")
    col_letters, row_str = match.groups()
    col_1based = 0
    for ch in col_letters:
        col_1based = col_1based * 26 + (ord(ch) - ord("A") + 1)
    return int(row_str) - 1, col_1based - 1


class FakeWorksheet:
    """In-memory test double for ``gspread.Worksheet``."""

    def __init__(self, rows: list[list[str]], *, col_count: int | None = None) -> None:
        self._rows: list[list[str]] = [list(r) for r in rows]
        self.col_count: int = (
            col_count
            if col_count is not None
            else (max((len(r) for r in rows), default=0))
        )
        self.batch_update_calls: list[tuple[list[dict[str, Any]], str | None]] = []
        self.update_cell_calls: list[tuple[int, int, str]] = []
        self.add_cols_calls: list[int] = []

    def get_all_values(self, *args: Any, **kwargs: Any) -> list[list[str]]:
        return copy.deepcopy(self._rows)

    def add_cols(self, cols: int) -> None:
        self.add_cols_calls.append(cols)
        self.col_count += cols

    def batch_update(
        self,
        data: list[dict[str, Any]],
        value_input_option: str | None = None,
    ) -> None:
        self.batch_update_calls.append((copy.deepcopy(data), value_input_option))
        for item in data:
            r_idx, c_idx = _a1_to_rowcol_0based(item["range"])
            val = str(item["values"][0][0])
            while len(self._rows) <= r_idx:
                self._rows.append([])
            while len(self._rows[r_idx]) <= c_idx:
                self._rows[r_idx].append("")
            self._rows[r_idx][c_idx] = val

    def update_cell(self, row: int, col: int, value: str) -> None:
        self.update_cell_calls.append((row, col, value))
        r_idx, c_idx = row - 1, col - 1
        while len(self._rows) <= r_idx:
            self._rows.append([])
        while len(self._rows[r_idx]) <= c_idx:
            self._rows[r_idx].append("")
        self._rows[r_idx][c_idx] = value


class FakeSpreadsheet:
    """In-memory test double for ``gspread.Spreadsheet``."""

    def __init__(self, worksheets: dict[str, FakeWorksheet]) -> None:
        self._worksheets = worksheets

    def worksheet(self, tab_name: str) -> FakeWorksheet:
        return self._worksheets[tab_name]


class FakeClient:
    """In-memory test double for ``gspread.Client``."""

    def __init__(self, spreadsheet: FakeSpreadsheet) -> None:
        self._spreadsheet = spreadsheet
        self.opened_names: list[str] = []

    def open(self, name: str) -> FakeSpreadsheet:
        self.opened_names.append(name)
        return self._spreadsheet


def test_backfill_02_sample_desc_creates_header_and_populates_counties_on_apply():
    """Verify 02_Sample_Desc creates Sampling_County header when absent and writes resolved counties."""
    ws = FakeWorksheet(
        [
            [
                "Sample_name",
                "Sampling_Location",
                "Sampling_Street",
                "Sampling_City",
                "Sampling_Zip",
                "Sampling_LatLong",
            ],
            # Row 2: Resolves via lat/lon PIP -> Yolo (06113)
            [
                "SAMPLE_001",
                "Orchard Block A",
                "100 County Rd",
                "",
                "",
                "38.5382, -121.7617",
            ],
            # Row 3: Resolves via ZIP -> San Joaquin (06077)
            [
                "SAMPLE_002",
                "Processor Yard",
                "200 Port Way",
                "",
                "95202",
                "",
            ],
            # Row 4: Resolves via City -> Stanislaus (06099)
            [
                "SAMPLE_003",
                "North Silo",
                "",
                "Modesto",
                "",
                "",
            ],
            # Row 5: Unresolvable -> 06000 (skipped, cell left blank)
            [
                "SAMPLE_004",
                "Unknown Experimental Plot",
                "",
                "",
                "",
                "",
            ],
            # Row 6: Blank row -> ignored completely
            ["", "", "", "", "", ""],
        ]
    )

    summary = backfill_worksheet_counties(ws, "02_Sample_Desc", dry_run=False)

    assert summary["tab_name"] == "02_Sample_Desc"
    assert summary["county_header"] == "Sampling_County"
    assert summary["dry_run"] is False
    assert summary["created_header"] is True
    assert summary["total_rows"] == 4
    assert summary["already_populated_rows"] == 0
    assert summary["resolved_rows"] == 3
    assert summary["unresolved_rows"] == 1
    assert summary["updated_cells"] == 4  # G1 header + G2, G3, G4
    assert summary["county_counts"] == {
        "San Joaquin": 1,
        "Stanislaus": 1,
        "Yolo": 1,
    }

    assert ws.add_cols_calls == [1]
    assert len(ws.batch_update_calls) == 1
    payload, value_input_option = ws.batch_update_calls[0]
    assert value_input_option == "USER_ENTERED"
    assert payload == [
        {"range": "G1", "values": [["Sampling_County"]]},
        {"range": "G2", "values": [["Yolo"]]},
        {"range": "G3", "values": [["San Joaquin"]]},
        {"range": "G4", "values": [["Stanislaus"]]},
    ]

    # Verify in-memory sheet contents after apply
    updated_rows = ws.get_all_values()
    assert updated_rows[0][6] == "Sampling_County"
    assert updated_rows[1][6] == "Yolo"
    assert updated_rows[2][6] == "San Joaquin"
    assert updated_rows[3][6] == "Stanislaus"
    assert len(updated_rows[4]) < 7 or updated_rows[4][6] == ""

    # Running a second time is idempotent and makes zero additional updates
    second_summary = backfill_worksheet_counties(ws, "02_Sample_Desc", dry_run=False)
    assert second_summary["created_header"] is False
    assert second_summary["already_populated_rows"] == 3
    assert second_summary["resolved_rows"] == 0
    assert second_summary["unresolved_rows"] == 1
    assert second_summary["updated_cells"] == 0
    assert len(ws.batch_update_calls) == 1


def test_backfill_04_producers_preserves_existing_county_and_fills_blank_rows():
    """Verify 04_Producers preserves existing Prod_County values and fills only empty cells."""
    ws = FakeWorksheet(
        [
            [
                "Provider_Code",
                "Prod_Location",
                "Prod_Street",
                "Prod_City",
                "Prod_County",
                "Prod_Zip",
                "Prod_LatLong",
            ],
            # Row 2: Already populated -> preserved even if other fields differ
            [
                "PROV_01",
                "Main Huller",
                "500 Almond Way",
                "Stockton",
                "Fresno",
                "95202",
                "",
            ],
            # Row 3: Blank Prod_County -> resolves via ZIP 95695 -> Yolo
            [
                "PROV_02",
                "Valley Facility",
                "800 East Main",
                "",
                "",
                "95695",
                "",
            ],
            # Row 4: Blank Prod_County -> resolves via LatLong -> Fresno
            [
                "PROV_03",
                "South Gin",
                "",
                "",
                "",
                "",
                "36.7378, -119.7871",
            ],
        ]
    )

    summary = backfill_worksheet_counties(ws, "04_Producers", dry_run=False)

    assert summary["tab_name"] == "04_Producers"
    assert summary["county_header"] == "Prod_County"
    assert summary["created_header"] is False
    assert summary["total_rows"] == 3
    assert summary["already_populated_rows"] == 1
    assert summary["resolved_rows"] == 2
    assert summary["unresolved_rows"] == 0
    assert summary["updated_cells"] == 2
    assert summary["county_counts"] == {"Fresno": 1, "Yolo": 1}

    assert ws.add_cols_calls == []
    assert len(ws.batch_update_calls) == 1
    payload, _ = ws.batch_update_calls[0]
    assert payload == [
        {"range": "E3", "values": [["Yolo"]]},
        {"range": "E4", "values": [["Fresno"]]},
    ]

    updated_rows = ws.get_all_values()
    assert updated_rows[1][4] == "Fresno"
    assert updated_rows[2][4] == "Yolo"
    assert updated_rows[3][4] == "Fresno"


def test_backfill_dry_run_makes_zero_sheet_mutations():
    """Verify dry_run=True (and CLI default) computes identical counts without mutating sheets."""
    ws_samples = FakeWorksheet(
        [
            ["Sample_name", "Sampling_City", "Sampling_Zip"],
            ["S1", "Davis", "95616"],
            ["S2", "Stockton", "95202"],
        ]
    )
    ws_producers = FakeWorksheet(
        [
            ["Provider_Code", "Prod_County", "Prod_City"],
            ["P1", "Stanislaus", "Modesto"],
            ["P2", "", "Salinas"],
        ]
    )
    client = FakeClient(
        FakeSpreadsheet(
            {
                "02_Sample_Desc": ws_samples,
                "04_Producers": ws_producers,
            }
        )
    )

    dry_summary = backfill_gsheet_counties(worksheet_client=client, dry_run=True)

    assert dry_summary["dry_run"] is True
    assert dry_summary["total_resolved_rows"] == 3
    assert dry_summary["total_already_populated_rows"] == 1
    assert dry_summary["total_unresolved_rows"] == 0
    assert dry_summary["total_updated_cells"] == 0
    assert dry_summary["tabs"]["02_Sample_Desc"]["county_counts"] == {
        "San Joaquin": 1,
        "Yolo": 1,
    }
    assert dry_summary["tabs"]["04_Producers"]["county_counts"] == {
        "Monterey": 1,
    }

    # Zero mutations on either worksheet in dry_run mode
    assert ws_samples.batch_update_calls == []
    assert ws_samples.update_cell_calls == []
    assert ws_samples.add_cols_calls == []
    assert ws_producers.batch_update_calls == []
    assert ws_producers.update_cell_calls == []
    assert ws_producers.add_cols_calls == []

    # CLI default mode is also dry-run
    exit_code = main([], worksheet_client=client)
    assert exit_code == 0
    assert ws_samples.batch_update_calls == []
    assert ws_producers.batch_update_calls == []


def test_backfill_never_logs_or_prints_subcounty_addresses_or_sample_names(
    caplog, capsys, monkeypatch
):
    """Assert sensitive sample names, addresses, cities, ZIPs, and coordinates never leak."""
    sensitive_values = [
        "SAMPLE_SECRET_001",
        "1234 Secret Orchard Ln",
        "36.7468,-119.7726",
        "95202",
        "Modesto",
        "Confidential Provider Barn",
    ]

    ws_samples = FakeWorksheet(
        [
            [
                "Sample_name",
                "Sampling_Location",
                "Sampling_Street",
                "Sampling_City",
                "Sampling_Zip",
                "Sampling_LatLong",
            ],
            [
                "SAMPLE_SECRET_001",
                "Confidential Provider Barn",
                "1234 Secret Orchard Ln",
                "Modesto",
                "95202",
                "36.7468,-119.7726",
            ],
        ]
    )
    ws_producers = FakeWorksheet(
        [
            [
                "Provider_Code",
                "Prod_Location",
                "Prod_Street",
                "Prod_City",
                "Prod_Zip",
                "Prod_LatLong",
            ],
            [
                "SAMPLE_SECRET_001",
                "Confidential Provider Barn",
                "1234 Secret Orchard Ln",
                "Modesto",
                "95202",
                "36.7468,-119.7726",
            ],
        ]
    )
    fake_client = FakeClient(
        FakeSpreadsheet(
            {
                "02_Sample_Desc": ws_samples,
                "04_Producers": ws_producers,
            }
        )
    )
    monkeypatch.setattr(gspread, "service_account", lambda filename=None: fake_client)

    with caplog.at_level(logging.DEBUG):
        exit_code = main(["--dry-run"])
        assert exit_code == 0
        backfill_gsheet_counties(worksheet_client=fake_client, dry_run=False)

    captured = capsys.readouterr()
    combined_output = "\n".join([caplog.text, captured.out, captured.err])

    for secret in sensitive_values:
        assert secret not in combined_output
