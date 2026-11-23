"""Unit tests for QC review decision seed CSV round-trip, ETL re-load protection, and Stage 2 GSheet writeback."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel, create_engine, select

from ca_biositing.datamodels.models import (
    CalorimetryRecord,
    ProximateRecord,
    QcReviewDecision,
)
from ca_biositing.pipeline.etl.load.analysis.calorimetry_record import (
    load_calorimetry_record,
)
from ca_biositing.pipeline.etl.load.analysis.proximate_record import (
    load_proximate_record,
)
from ca_biositing.pipeline.utils.gsheet_qc_writeback import (
    AIM1_GSHEET_NAME,
    AIM2_BIOCHEM_GSHEET_NAME,
    resolve_worksheet_target,
    writeback_batch_to_gsheet,
    writeback_qc_decision_to_gsheet,
)
from ca_biositing.pipeline.utils.qc_ledger_seed import (
    apply_qc_decision_to_db,
    export_db_decisions_to_seed_csv,
    format_qc_audit_note,
    load_seed_csv_to_db,
)
from ca_biositing.pipeline.utils.qc_protected_records import (
    build_qc_aware_update_dict,
    get_unsynced_qc_protected_record_ids,
)


class _FakeWorksheet:
    def __init__(self, title: str, rows: List[List[str]]) -> None:
        self.title = title
        self.rows = [list(r) for r in rows]
        self.batch_updates: List[Dict[str, Any]] = []

    def get_all_values(self) -> List[List[str]]:
        return [list(r) for r in self.rows]

    def batch_update(
        self,
        updates: List[Dict[str, Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> None:
        self.batch_updates.extend(updates)
        for item in updates:
            a1 = item["range"]
            col_letters = "".join(ch for ch in a1 if ch.isalpha())
            row_num = int("".join(ch for ch in a1 if ch.isdigit()))
            col_idx = ord(col_letters.upper()) - ord("A")
            while len(self.rows[row_num - 1]) <= col_idx:
                self.rows[row_num - 1].append("")
            self.rows[row_num - 1][col_idx] = item["values"][0][0]


class _FakeSpreadsheet:
    def __init__(self, worksheets: Dict[str, _FakeWorksheet]) -> None:
        self.worksheets = worksheets

    def worksheet(self, name: str) -> _FakeWorksheet:
        return self.worksheets[name]


class _FakeGspreadClient:
    def __init__(self, spreadsheets: Dict[str, _FakeSpreadsheet]) -> None:
        self.spreadsheets = spreadsheets

    def open(self, name: str) -> _FakeSpreadsheet:
        return self.spreadsheets[name]


def _make_in_memory_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(
        engine,
        tables=[
            QcReviewDecision.__table__,
            ProximateRecord.__table__,
            CalorimetryRecord.__table__,
        ],
    )
    return engine


def test_seed_csv_roundtrip_and_apply_qc_decision_to_db(tmp_path: Path) -> None:
    """Verify export_db_decisions_to_seed_csv + load_seed_csv_to_db round-trip and record override."""
    engine = _make_in_memory_engine()
    csv_path = tmp_path / "qc_review_decisions_seed.csv"

    with Session(engine) as session:
        session.add(
            ProximateRecord(
                record_id="PROX-100",
                technical_replicate_no=1,
                qc_pass="pass",
                note="Initial lab note",
            )
        )
        decision = QcReviewDecision(
            record_table="proximate_record",
            record_id="PROX-100",
            replicate_group_key="almond hulls::proximate::ash",
            resource_name="almond hulls",
            analysis_type="proximate",
            parameter_name="ash",
            flag_type="rsd_gt_10",
            flag_trigger_value="RSD=15.2%",
            old_qc_pass="pass",
            new_qc_pass="fail",
            decision_status="resolved",
            decision_action="reject_fail",
            rationale_chips="high_rsd;instrument_drift",
            review_note="Confirmed furnace temperature spike on replicate",
            submitted_by_email="analyst@lbl.gov",
            assigned_to_email="analyst@lbl.gov",
            resolved_by_email="analyst@lbl.gov",
            resolved_at=datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc),
            synced_to_gsheet=False,
        )
        session.add(decision)
        session.commit()
        session.refresh(decision)

        applied = apply_qc_decision_to_db(session, decision)
        session.commit()
        assert applied is True

        rec = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-100")
        ).first()
        assert rec is not None
        assert rec.qc_pass == "fail"
        assert f"[QC_AUDIT id={decision.id} " in (rec.note or "")
        assert "Initial lab note | [QC_AUDIT " in (rec.note or "")

        exported = export_db_decisions_to_seed_csv(session, csv_path=csv_path)
        assert exported == 1

    # Simulate DB reset with a fresh in-memory engine and reload from CSV
    reset_engine = _make_in_memory_engine()
    with Session(reset_engine) as session:
        session.add(
            ProximateRecord(
                record_id="PROX-100",
                technical_replicate_no=1,
                qc_pass="pass",
                note="Initial lab note",
            )
        )
        session.commit()

        loaded_decisions = load_seed_csv_to_db(session, csv_path=csv_path)
        assert len(loaded_decisions) == 1
        assert loaded_decisions[0].record_id == "PROX-100"
        assert loaded_decisions[0].new_qc_pass == "fail"
        assert loaded_decisions[0].synced_to_gsheet is False

        restored_rec = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-100")
        ).first()
        assert restored_rec is not None
        assert restored_rec.qc_pass == "fail"
        assert "Confirmed furnace temperature spike on replicate" in (
            restored_rec.note or ""
        )


def test_etl_reload_protection_preserves_unsynced_stage1_decisions() -> None:
    """Verify routine ETL loads preserve qc_pass and note when synced_to_gsheet is False."""
    engine = _make_in_memory_engine()

    with Session(engine) as session:
        # 1. Row with unsynced Stage 1 decision (synced_to_gsheet = False) -> MUST BE PROTECTED
        session.add(
            ProximateRecord(
                record_id="PROX-UNSYNCED",
                technical_replicate_no=1,
                qc_pass="fail",
                note='Bench note | [QC_AUDIT id=1 action=reject_fail qc_pass=fail by=analyst@lbl.gov at=2026-10-18T12:00:00+00:00 note="Outlier"]',
            )
        )
        session.add(
            QcReviewDecision(
                record_table="proximate_record",
                record_id="PROX-UNSYNCED",
                resource_name="almond hulls",
                analysis_type="proximate",
                parameter_name="moisture",
                flag_type="iqr_outlier",
                old_qc_pass="pass",
                new_qc_pass="fail",
                decision_status="resolved",
                decision_action="reject_fail",
                review_note="Outlier",
                submitted_by_email="analyst@lbl.gov",
                resolved_by_email="analyst@lbl.gov",
                synced_to_gsheet=False,
            )
        )

        # 2. Row with synced Stage 2 decision (synced_to_gsheet = True) -> NOT protected (sheet is updated)
        session.add(
            ProximateRecord(
                record_id="PROX-SYNCED",
                technical_replicate_no=1,
                qc_pass="fail",
                note="Old synced note",
            )
        )
        session.add(
            QcReviewDecision(
                record_table="proximate_record",
                record_id="PROX-SYNCED",
                resource_name="almond hulls",
                analysis_type="proximate",
                parameter_name="ash",
                flag_type="rsd_gt_10",
                old_qc_pass="pass",
                new_qc_pass="fail",
                decision_status="resolved",
                decision_action="reject_fail",
                review_note="Synced outlier",
                submitted_by_email="analyst@lbl.gov",
                resolved_by_email="analyst@lbl.gov",
                synced_to_gsheet=True,
            )
        )

        # 3. Row with no QC decision -> NOT protected
        session.add(
            ProximateRecord(
                record_id="PROX-PLAIN",
                technical_replicate_no=1,
                qc_pass="pass",
                note="Plain note",
            )
        )
        session.commit()

        protected = get_unsynced_qc_protected_record_ids(
            session,
            "proximate_record",
            ["PROX-UNSYNCED", "PROX-SYNCED", "PROX-PLAIN"],
        )
        assert protected == {"PROX-UNSYNCED"}

        # Check build_qc_aware_update_dict omits qc_pass and note for protected row
        dummy_stmt = insert(ProximateRecord).values({"record_id": "PROX-UNSYNCED"})
        protected_dict = build_qc_aware_update_dict(
            ProximateRecord,
            dummy_stmt,
            protected,
            record_id="PROX-UNSYNCED",
        )
        assert "qc_pass" not in protected_dict
        assert "note" not in protected_dict
        assert "technical_replicate_no" in protected_dict

        unprotected_dict = build_qc_aware_update_dict(
            ProximateRecord,
            dummy_stmt,
            protected,
            record_id="PROX-SYNCED",
        )
        assert "qc_pass" in unprotected_dict
        assert "note" in unprotected_dict

    # Now run the actual ETL load task (load_proximate_record.fn) simulating a GSheet re-load
    etl_df = pd.DataFrame(
        [
            {
                "record_id": "PROX-UNSYNCED",
                "technical_replicate_no": 2,
                "qc_pass": "pass",  # Stale GSheet value trying to overwrite Stage 1 'fail'
                "note": "Stale GSheet note",
            },
            {
                "record_id": "PROX-SYNCED",
                "technical_replicate_no": 3,
                "qc_pass": "pass",
                "note": "Updated GSheet note after sync",
            },
            {
                "record_id": "PROX-PLAIN",
                "technical_replicate_no": 4,
                "qc_pass": "fail",
                "note": "Updated plain GSheet note",
            },
        ]
    )

    with (
        patch(
            "ca_biositing.pipeline.etl.load.analysis.proximate_record.get_engine",
            return_value=engine,
        ),
        patch("ca_biositing.pipeline.etl.load.analysis.proximate_record.get_run_logger"),
    ):
        load_proximate_record.fn(etl_df)

    with Session(engine) as session:
        unsynced_row = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-UNSYNCED")
        ).first()
        assert unsynced_row is not None
        assert unsynced_row.technical_replicate_no == 2  # non-QC column updated!
        assert unsynced_row.qc_pass == "fail"  # Stage 1 qc_pass preserved!
        assert "[QC_AUDIT id=1" in (unsynced_row.note or "")  # Stage 1 audit note preserved!

        synced_row = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-SYNCED")
        ).first()
        assert synced_row is not None
        assert synced_row.technical_replicate_no == 3
        assert synced_row.qc_pass == "pass"
        assert synced_row.note == "Updated GSheet note after sync"

        plain_row = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-PLAIN")
        ).first()
        assert plain_row is not None
        assert plain_row.technical_replicate_no == 4
        assert plain_row.qc_pass == "fail"
        assert plain_row.note == "Updated plain GSheet note"


def test_bulk_etl_reload_protection_preserves_unsynced_decisions() -> None:
    """Verify bulk-upsert ETL load tasks (e.g. CalorimetryRecord) preserve unsynced QC decisions via SQL CASE."""
    engine = _make_in_memory_engine()

    with Session(engine) as session:
        session.add(
            CalorimetryRecord(
                record_id="CAL-UNSYNCED",
                technical_replicate_no=1,
                qc_pass="fail",
                note='Cal note | [QC_AUDIT id=7 action=reject_fail qc_pass=fail by=analyst@lbl.gov at=2026-10-18T12:00:00+00:00 note="Bomb misfire"]',
            )
        )
        session.add(
            CalorimetryRecord(
                record_id="CAL-PLAIN",
                technical_replicate_no=1,
                qc_pass="pass",
                note="Initial cal note",
            )
        )
        session.add(
            QcReviewDecision(
                record_table="calorimetry_record",
                record_id="CAL-UNSYNCED",
                resource_name="walnut shells",
                analysis_type="calorimetry",
                parameter_name="hhv",
                flag_type="analyst_flagged",
                old_qc_pass="pass",
                new_qc_pass="fail",
                decision_status="resolved",
                decision_action="reject_fail",
                review_note="Bomb misfire",
                submitted_by_email="analyst@lbl.gov",
                resolved_by_email="analyst@lbl.gov",
                synced_to_gsheet=False,
            )
        )
        session.commit()

    etl_df = pd.DataFrame(
        [
            {
                "record_id": "CAL-UNSYNCED",
                "technical_replicate_no": 2,
                "qc_pass": "pass",
                "note": "Stale sheet note",
            },
            {
                "record_id": "CAL-PLAIN",
                "technical_replicate_no": 3,
                "qc_pass": "fail",
                "note": "Updated sheet note",
            },
        ]
    )

    with (
        patch(
            "ca_biositing.pipeline.etl.load.analysis.calorimetry_record.engine",
            engine,
        ),
        patch(
            "ca_biositing.pipeline.etl.load.analysis.calorimetry_record.get_run_logger"
        ),
    ):
        load_calorimetry_record.fn(etl_df)

    with Session(engine) as session:
        unsynced_cal = session.exec(
            select(CalorimetryRecord).where(
                CalorimetryRecord.record_id == "CAL-UNSYNCED"
            )
        ).first()
        assert unsynced_cal is not None
        assert unsynced_cal.technical_replicate_no == 2
        assert unsynced_cal.qc_pass == "fail"
        assert "[QC_AUDIT id=7" in (unsynced_cal.note or "")

        plain_cal = session.exec(
            select(CalorimetryRecord).where(CalorimetryRecord.record_id == "CAL-PLAIN")
        ).first()
        assert plain_cal is not None
        assert plain_cal.technical_replicate_no == 3
        assert plain_cal.qc_pass == "fail"
        assert plain_cal.note == "Updated sheet note"


def test_idempotent_qc_audit_note_and_stage2_gsheet_writeback() -> None:
    """Verify format_qc_audit_note and writeback_qc_decision_to_gsheet are idempotent on repeated calls."""
    assert resolve_worksheet_target("proximate_record") == (
        AIM1_GSHEET_NAME,
        "03.1-Proximate",
    )
    assert resolve_worksheet_target("fermentation_record") == (
        AIM2_BIOCHEM_GSHEET_NAME,
        "02.2-BioConversionData",
    )

    note_v1 = format_qc_audit_note(
        existing_note="Bench observation",
        decision_id=42,
        action="reject_fail",
        new_qc_pass="fail",
        reviewer_email="petersmith@lbl.gov",
        review_note="Initial fail note",
        resolved_at_iso="2026-10-18T14:00:00+00:00",
    )
    assert note_v1.count("[QC_AUDIT id=42 ") == 1
    assert "Bench observation | [QC_AUDIT id=42 " in note_v1

    # Calling again with updated note for the same decision_id replaces in-place without duplicating
    note_v2 = format_qc_audit_note(
        existing_note=note_v1,
        decision_id=42,
        action="approve_pass",
        new_qc_pass="pass",
        reviewer_email="petersmith@lbl.gov",
        review_note="Updated after re-check",
        resolved_at_iso="2026-10-18T15:00:00+00:00",
    )
    assert note_v2.count("[QC_AUDIT id=42 ") == 1
    assert "qc_pass=pass" in note_v2
    assert 'note="Updated after re-check"' in note_v2
    assert "Initial fail note" not in note_v2

    engine = _make_in_memory_engine()
    ws = _FakeWorksheet(
        "03.1-Proximate",
        [
            ["record_id", "resource", "parameter", "value", "qc_result", "note", "updated_at"],
            ["PROX-201", "almond hulls", "ash", "6.2", "pass", "Baseline note", ""],
            ["PROX-202", "almond hulls", "ash", "6.4", "pass", "", ""],
        ],
    )
    spreadsheet = _FakeSpreadsheet({"03.1-Proximate": ws})
    client = _FakeGspreadClient({AIM1_GSHEET_NAME: spreadsheet})

    with Session(engine) as session:
        d1 = QcReviewDecision(
            record_table="proximate_record",
            record_id="prox-201",
            replicate_group_key="almond hulls::proximate::ash",
            resource_name="almond hulls",
            analysis_type="Proximate Analysis",
            parameter_name="ash",
            flag_type="rsd_gt_10",
            old_qc_pass="pass",
            new_qc_pass="fail",
            decision_status="resolved",
            decision_action="reject_fail",
            review_note="Crucible crack observed",
            submitted_by_email="analyst@lbl.gov",
            resolved_by_email="petersmith@lbl.gov",
            resolved_at=datetime(2026, 10, 18, 16, 0, tzinfo=timezone.utc),
            synced_to_gsheet=False,
        )
        session.add(d1)
        session.commit()
        session.refresh(d1)
        assert d1.id is not None

        # First Stage 2 sync call (also tests case-insensitive record_id match & updated_at writeback)
        res1 = writeback_qc_decision_to_gsheet(
            session,
            decision_id=d1.id,
            worksheet_client=client,
        )
        assert res1["already_synced"] is False
        assert res1["synced_to_gsheet"] is True
        assert ws.rows[1][4] == "fail"
        assert ws.rows[1][5].count(f"[QC_AUDIT id={d1.id} ") == 1
        assert "Baseline note | [QC_AUDIT " in ws.rows[1][5]
        assert ws.rows[1][6].endswith("Z")
        assert res1["updated_at"] == ws.rows[1][6]

        # Second Stage 2 sync call on the same decision is idempotent
        res2 = writeback_qc_decision_to_gsheet(
            session,
            decision_id=d1.id,
            worksheet_client=client,
        )
        assert res2["already_synced"] is True
        assert res2["synced_to_gsheet"] is True
        assert ws.rows[1][5].count(f"[QC_AUDIT id={d1.id} ") == 1

        # Add a second unsynced decision and test writeback_batch_to_gsheet
        d2 = QcReviewDecision(
            record_table="proximate_record",
            record_id="PROX-202",
            replicate_group_key="almond hulls::proximate::ash",
            resource_name="almond hulls",
            analysis_type="proximate",
            parameter_name="ash",
            flag_type="rsd_gt_10",
            old_qc_pass="pass",
            new_qc_pass="fail",
            decision_status="resolved",
            decision_action="reject_fail",
            review_note="Batch replicate also affected",
            submitted_by_email="analyst@lbl.gov",
            resolved_by_email="petersmith@lbl.gov",
            resolved_at=datetime(2026, 10, 18, 16, 5, tzinfo=timezone.utc),
            synced_to_gsheet=False,
        )
        session.add(d2)
        session.commit()

        batch_res = writeback_batch_to_gsheet(session, worksheet_client=client)
        assert batch_res["synced_count"] == 1
        assert ws.rows[2][4] == "fail"
        assert f"[QC_AUDIT id={d2.id} " in ws.rows[2][5]

        # Test dry_run=True does NOT mutate worksheet or mark synced_to_gsheet=True
        ws.rows.append(["PROX-203", "almond hulls", "ash", "6.8", "pass", "Orig note", ""])
        d3 = QcReviewDecision(
            record_table="proximate_record",
            record_id="PROX-203",
            replicate_group_key="almond hulls::proximate::ash",
            resource_name="almond hulls",
            analysis_type="proximate",
            parameter_name="ash",
            flag_type="rsd_gt_10",
            old_qc_pass="pass",
            new_qc_pass="fail",
            decision_status="resolved",
            decision_action="reject_fail",
            review_note="Dry run check",
            submitted_by_email="analyst@lbl.gov",
            resolved_by_email="petersmith@lbl.gov",
            resolved_at=datetime(2026, 10, 18, 16, 10, tzinfo=timezone.utc),
            synced_to_gsheet=False,
        )
        session.add(d3)
        session.commit()
        session.refresh(d3)
        assert d3.id is not None

        dry_res = writeback_qc_decision_to_gsheet(
            session,
            decision_id=d3.id,
            worksheet_client=client,
            dry_run=True,
        )
        assert dry_res["dry_run"] is True
        assert dry_res["synced_to_gsheet"] is False
        assert ws.rows[3][4] == "pass"  # Unchanged in dry-run
        assert ws.rows[3][5] == "Orig note"  # Unchanged in dry-run

        dry_batch = writeback_batch_to_gsheet(
            session,
            worksheet_client=client,
            dry_run=True,
        )
        assert dry_batch["dry_run"] is True
        assert dry_batch["synced_count"] == 0
        assert len(dry_batch["results"]) == 1
        assert ws.rows[3][4] == "pass"

        # Test missing/blank record_id guard raises ValueError and increments failed_count in batch
        d_blank = QcReviewDecision(
            record_table="proximate_record",
            record_id="   ",
            replicate_group_key="almond hulls::proximate::ash",
            resource_name="almond hulls",
            analysis_type="proximate",
            parameter_name="ash",
            flag_type="rsd_gt_10",
            old_qc_pass="pass",
            new_qc_pass="fail",
            decision_status="resolved",
            decision_action="reject_fail",
            review_note="Missing record_id check",
            submitted_by_email="analyst@lbl.gov",
            resolved_by_email="petersmith@lbl.gov",
            resolved_at=datetime(2026, 10, 18, 16, 15, tzinfo=timezone.utc),
            synced_to_gsheet=False,
        )
        session.add(d_blank)
        session.commit()
        session.refresh(d_blank)
        assert d_blank.id is not None

        with pytest.raises(ValueError, match="missing record_id"):
            writeback_qc_decision_to_gsheet(
                session,
                decision_id=d_blank.id,
                worksheet_client=client,
            )

        batch_with_blank = writeback_batch_to_gsheet(session, worksheet_client=client)
        assert batch_with_blank["synced_count"] == 1  # d3 synced
        assert batch_with_blank["failed_count"] == 1  # d_blank failed cleanly
