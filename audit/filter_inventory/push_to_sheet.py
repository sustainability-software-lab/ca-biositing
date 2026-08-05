"""Push the filter inventory CSV to the shared Google Sheet.

Reads filter-inventory.csv and writes it to the first worksheet (gid=0) of the
BioCirv filter inventory sheet, replacing that tab's contents.

Auth follows the existing repo pattern in audit/skills/anomaly_tracker.py:
a service-account credentials.json at the repository root. The service account
    mg-runner@biocirv-470318.iam.gserviceaccount.com
must be granted Editor access to the spreadsheet, otherwise gspread raises a
403 APIError.

Usage:
    pixi run -e auditor python audit/filter_inventory/push_to_sheet.py --inspect
    pixi run -e auditor python audit/filter_inventory/push_to_sheet.py --push

--inspect is read-only: it reports the tabs present and what is currently on
the target tab. Run it before --push so the overwrite is an informed one.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import gspread
from gspread.utils import rowcol_to_a1

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent

SPREADSHEET_ID = "1dEp-46Jng4K6oKGA41rMyzzHLmwIfJ-6p1KRnwnUpog"
CREDENTIALS_PATH = REPO_ROOT / "credentials.json"
CSV_PATH = HERE / "filter-inventory.csv"

# gid=0 is the first worksheet. Resolved by index rather than by title so the
# script does not depend on whatever that tab happens to be named.
TARGET_WORKSHEET_INDEX = 0


def open_target():
    if not CREDENTIALS_PATH.exists():
        sys.exit(f"No credentials at {CREDENTIALS_PATH}")
    client = gspread.service_account(filename=str(CREDENTIALS_PATH))
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet, spreadsheet.get_worksheet(TARGET_WORKSHEET_INDEX)


def inspect() -> None:
    spreadsheet, worksheet = open_target()
    print(f"Spreadsheet: {spreadsheet.title}")
    print(f"Worksheets:  {[ws.title for ws in spreadsheet.worksheets()]}")
    print()
    print(f"Target tab:  '{worksheet.title}' (index {TARGET_WORKSHEET_INDEX}, "
          f"id={worksheet.id}, {worksheet.row_count}x{worksheet.col_count})")

    values = worksheet.get_all_values()
    non_empty = [r for r in values if any(cell.strip() for cell in r)]
    print(f"Non-empty rows currently on target tab: {len(non_empty)}")
    if non_empty:
        print("\n--- current contents (first 10 rows, first 4 cols) ---")
        for row in non_empty[:10]:
            print("  | " + " | ".join(c[:28] for c in row[:4]))
        if len(non_empty) > 10:
            print(f"  ... and {len(non_empty) - 10} more rows")
        print("\nTHIS CONTENT WILL BE CLEARED BY --push")
    else:
        print("Target tab is empty; --push will not destroy anything.")


def _harvest_user_edits(worksheet, user_columns):
    """Read reviewer-owned column values off the live sheet, keyed by rule ID.

    Matching is on the ID column, never on row position, so rows can be
    reordered, added or removed by the build without scrambling human edits.
    """
    existing = worksheet.get_all_values()
    if not existing or not existing[0]:
        return {}

    header = existing[0]
    if "ID" not in header:
        print("  ! Existing sheet has no 'ID' column - cannot preserve edits")
        return {}

    id_idx = header.index("ID")
    col_idx = {c: header.index(c) for c in user_columns if c in header}
    if not col_idx:
        return {}

    saved = {}
    for row in existing[1:]:
        if len(row) <= id_idx:
            continue
        rule_id = row[id_idx].strip()
        if not rule_id:
            continue
        vals = {c: (row[i].strip() if len(row) > i else "")
                for c, i in col_idx.items()}
        if any(vals.values()):
            saved[rule_id] = vals
    return saved


def _apply_validation(spreadsheet, worksheet, header, n_rows):
    """Attach dropdowns to the Priority and Review status columns."""
    from build_inventory import PRIORITY_OPTIONS, REVIEW_OPTIONS

    requests = []
    for col_name, options in (("Priority", PRIORITY_OPTIONS),
                              ("Review status", REVIEW_OPTIONS)):
        if col_name not in header:
            continue
        c = header.index(col_name)
        requests.append({"setDataValidation": {
            "range": {"sheetId": worksheet.id, "startRowIndex": 1,
                      "endRowIndex": n_rows, "startColumnIndex": c,
                      "endColumnIndex": c + 1},
            "rule": {
                "condition": {"type": "ONE_OF_LIST",
                              "values": [{"userEnteredValue": o} for o in options]},
                "showCustomUi": True,
                "strict": False,
            },
        }})
    if requests:
        spreadsheet.batch_update({"requests": requests})


def push() -> None:
    if not CSV_PATH.exists():
        sys.exit(f"No inventory CSV at {CSV_PATH} - run build_inventory.py first")

    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    if not rows:
        sys.exit("Inventory CSV is empty; refusing to push")

    sys.path.insert(0, str(HERE))
    from build_inventory import USER_COLUMNS

    header = rows[0]
    spreadsheet, worksheet = open_target()
    print(f"Target: '{spreadsheet.title}' / tab '{worksheet.title}'")

    # 1. Harvest reviewer edits BEFORE clearing anything.
    saved = _harvest_user_edits(worksheet, USER_COLUMNS)
    if saved:
        print(f"  Preserving reviewer edits on {len(saved)} rule(s)")

    # 2. Merge them into the freshly built rows, matched by ID.
    id_idx = header.index("ID")
    restored, orphaned = 0, []
    seen_ids = {r[id_idx] for r in rows[1:]}
    for row in rows[1:]:
        vals = saved.get(row[id_idx])
        if not vals:
            continue
        for col, val in vals.items():
            if val and col in header:
                row[header.index(col)] = val
        restored += 1
    orphaned = sorted(set(saved) - seen_ids)

    if restored:
        print(f"  Re-applied edits to {restored} rule(s)")
    if orphaned:
        print(f"  ! {len(orphaned)} edited rule(s) no longer exist and will be "
              f"DROPPED: {', '.join(orphaned)}")

    needed_rows, needed_cols = len(rows) + 10, len(header) + 2
    if worksheet.row_count < needed_rows or worksheet.col_count < needed_cols:
        worksheet.resize(rows=max(worksheet.row_count, needed_rows),
                         cols=max(worksheet.col_count, needed_cols))

    last_col = rowcol_to_a1(1, len(header)).rstrip("1")

    worksheet.clear()
    worksheet.update(values=rows, range_name="A1")

    worksheet.format(f"A1:{last_col}1", {
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "backgroundColor": {"red": 0.12, "green": 0.22, "blue": 0.39},
        "verticalAlignment": "MIDDLE",
        "wrapStrategy": "WRAP",
    })
    worksheet.format(f"A2:{last_col}{len(rows)}", {
        "verticalAlignment": "TOP",
        "wrapStrategy": "WRAP",
    })
    # Freeze the header and the ID + Rule columns so ratings stay anchored.
    worksheet.freeze(rows=1, cols=2)
    _apply_validation(spreadsheet, worksheet, header, len(rows))

    print(f"Pushed {len(rows) - 1} rules ({len(rows)} rows incl. header)")
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={worksheet.id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect", action="store_true",
                       help="read-only: show tabs and current target contents")
    group.add_argument("--push", action="store_true",
                       help="clear the target tab and write the inventory")
    args = parser.parse_args()

    if args.inspect:
        inspect()
    else:
        push()
