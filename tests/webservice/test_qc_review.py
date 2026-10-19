"""Tests for the two-stage `/v1/qc/*` Audit Workbench API, Stage 1 DB persistence, and Stage 2 Admin GSheet sync."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from ca_biositing.datamodels.database import get_session
from ca_biositing.datamodels.models.aim1_records.proximate_record import (
    ProximateRecord,
)
from ca_biositing.datamodels.models.qc.qc_review_decision import QcReviewDecision
from ca_biositing.webservice.config import config
from ca_biositing.webservice.main import app
from ca_biositing.webservice.services.gsheet_sync_service import (
    clear_worksheet_row_state,
)
from ca_biositing.webservice.services.qc_ledger_service import (
    read_seed_csv,
    sync_seed_csv_to_db,
)


@pytest.fixture
def sqlite_engine():
    """Create an in-memory SQLite engine with `QcReviewDecision` and `ProximateRecord` tables."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[
            QcReviewDecision.__table__,
            ProximateRecord.__table__,
        ],
    )
    return engine


@pytest.fixture
def client(
    sqlite_engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient wired to the in-memory SQLite engine and temp seed CSV."""
    seed_csv = tmp_path / "qc_review_decisions_seed.csv"
    monkeypatch.setenv("BIOSITING_QC_SEED_CSV_PATH", str(seed_csv))
    monkeypatch.setattr(config, "require_dashboard_auth", True)
    monkeypatch.setattr(
        config,
        "dashboard_allowed_domains",
        ["lbl.gov", "ucdavis.edu", "beamcircular.org"],
    )
    monkeypatch.setattr(config, "dashboard_allowed_emails", [])
    monkeypatch.setattr(
        config,
        "dashboard_admin_emails",
        ["qa.admin@lbl.gov"],
    )
    clear_worksheet_row_state()

    def _override_session() -> Generator[Session, None, None]:
        with Session(sqlite_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    clear_worksheet_row_state()


def _seed_proximate_records(engine) -> None:
    with Session(engine) as session:
        for rid, note in [
            ("PROX-AS-01", "Initial lab run"),
            ("PROX-AS-02", "Rep 2"),
            ("PROX-AS-03", "Rep 3"),
        ]:
            session.add(
                ProximateRecord(
                    record_id=rid,
                    qc_pass="pass",
                    note=note,
                )
            )
        session.commit()


def test_stage1_analyst_decision_updates_db_and_seed_csv_with_unsynced_flag(
    client: TestClient,
    sqlite_engine,
    tmp_path: Path,
) -> None:
    """Verify Stage 1 decision immediately updates analytical DB and seed CSV while keeping synced_to_gsheet=False."""
    _seed_proximate_records(sqlite_engine)

    # Log in as analyst
    login_resp = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst1@lbl.gov", "name": "Analyst One"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["role"] == "analyst"

    # Submit a Stage 1 decision rejecting PROX-AS-01 as fail
    post_resp = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "replicate_group_key": "almond_shells|proximate|moisture|AS-PS-01",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "flag_type": "rsd_gt_10",
            "flag_trigger_value": "RSD=18.4%",
            "decision_action": "reject_fail",
            "new_qc_pass": "fail",
            "rationale_chips": ["Crucible Crack", "High RSD"],
            "review_note": "Crucible cracked during drying cycle",
        },
    )
    assert post_resp.status_code == 200
    data = post_resp.json()
    decision = data["decision"]
    assert decision["record_id"] == "PROX-AS-01"
    assert decision["old_qc_pass"] == "pass"
    assert decision["new_qc_pass"] == "fail"
    assert decision["decision_status"] == "resolved"
    assert decision["resolved_by_email"] == "analyst1@lbl.gov"
    assert decision["resolved_at"] is not None
    assert decision["synced_to_gsheet"] is False
    assert decision["gsheet_synced_at"] is None

    # Verify analytical ProximateRecord in DB was immediately flipped to fail with [QC_AUDIT ...] note
    with Session(sqlite_engine) as session:
        rec = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-AS-01")
        ).first()
        assert rec is not None
        assert rec.qc_pass == "fail"
        assert "[QC_AUDIT id=" in (rec.note or "")
        assert "Crucible cracked during drying cycle" in (rec.note or "")

    # Verify seed CSV was written and can re-seed after a simulated DB reset
    seed_csv_path = tmp_path / "qc_review_decisions_seed.csv"
    csv_rows = read_seed_csv(seed_csv_path)
    assert len(csv_rows) == 1
    assert csv_rows[0]["record_id"] == "PROX-AS-01"
    assert csv_rows[0]["new_qc_pass"] == "fail"
    assert csv_rows[0]["synced_to_gsheet"] == "false"

    with Session(sqlite_engine) as session:
        for d in session.exec(select(QcReviewDecision)).all():
            session.delete(d)
        rec = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-AS-01")
        ).first()
        assert rec is not None
        rec.qc_pass = "pass"
        session.add(rec)
        session.commit()

        reseed_result = sync_seed_csv_to_db(session, csv_path=seed_csv_path)
        assert reseed_result["decisions_seeded"] == 1
        assert reseed_result["records_updated"] == 1

        rec_after = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-AS-01")
        ).first()
        assert rec_after is not None
        assert rec_after.qc_pass == "fail"


def test_tray_to_workbench_assignment_queues_and_csv_export(
    client: TestClient,
    sqlite_engine,
) -> None:
    """Verify Selection Tray -> Workbench flow, assignment, /auth/me open count, queue filters, and CSV export."""
    _seed_proximate_records(sqlite_engine)

    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst1@ucdavis.edu"},
    )

    tray_resp = client.post(
        "/v1/qc/tray-to-workbench",
        json={
            "record_table": "proximate_record",
            "record_ids": ["PROX-AS-02", "PROX-AS-03"],
            "replicate_group_key": "almond_shells|proximate|ash|AS-PS-01",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "ash",
            "flag_type": "iqr_outlier",
            "assigned_to_email": "me",
            "review_note": "Investigate duplicate ash replicates",
        },
    )
    assert tray_resp.status_code == 200
    tray_body = tray_resp.json()
    assert tray_body["created_count"] == 2
    assert tray_body["workbench_url"].startswith(
        "/v1/dashboards/metadata/resource_audit_workbench.html?decision_id="
    )

    # /v1/qc/auth/me reflects assigned_open_count == 2
    me_resp = client.get("/v1/qc/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["assigned_open_count"] == 2

    # Filter GET /v1/qc/decisions?assigned_to=me&status=open
    mine_resp = client.get(
        "/v1/qc/decisions",
        params={"assigned_to": "me", "status": "open"},
    )
    assert mine_resp.status_code == 200
    assert mine_resp.json()["count"] == 2

    # Unassign one decision via PATCH /v1/qc/decisions/{id}/assign
    first_id = tray_body["decision_ids"][0]
    assign_resp = client.patch(
        f"/v1/qc/decisions/{first_id}/assign",
        json={"assigned_to_email": None},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["decision"]["assigned_to_email"] is None

    unassigned_resp = client.get(
        "/v1/qc/decisions",
        params={"assigned_to": "unassigned"},
    )
    assert unassigned_resp.status_code == 200
    assert unassigned_resp.json()["count"] == 1

    # Summary endpoint
    summary_resp = client.get("/v1/qc/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_decisions"] == 2
    assert summary["assigned_open_count"] == 1
    assert summary["unassigned_open_count"] == 1

    # CSV export endpoint
    csv_resp = client.get("/v1/qc/export.csv")
    assert csv_resp.status_code == 200
    assert "PROX-AS-02" in csv_resp.text
    assert "PROX-AS-03" in csv_resp.text


def test_stage2_gsheet_sync_rbac_idempotency_and_re_edit_reset(
    client: TestClient,
    sqlite_engine,
) -> None:
    """Verify analyst is blocked (403) from Stage 2 sync, admin succeeds idempotently, and Stage 1 re-edit resets sync status."""
    _seed_proximate_records(sqlite_engine)

    # 1. Analyst creates a resolved Stage 1 decision
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst1@lbl.gov"},
    )
    create_resp = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "replicate_group_key": "almond_shells|proximate|moisture|AS-PS-01",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "flag_type": "rsd_gt_10",
            "decision_action": "reject_fail",
            "new_qc_pass": "fail",
            "review_note": "Confirmed moisture outlier",
        },
    )
    assert create_resp.status_code == 200
    decision_id = create_resp.json()["decision"]["id"]

    # 2. Analyst is blocked (403) from both single and batch Stage 2 Google Sheets writeback
    analyst_single_sync = client.post(
        f"/v1/qc/decisions/{decision_id}/sync-gsheet"
    )
    assert analyst_single_sync.status_code == 403

    analyst_batch_sync = client.post("/v1/qc/decisions/sync-gsheet-batch")
    assert analyst_batch_sync.status_code == 403

    # 3. Log in as Admin and trigger Stage 2 Google Sheets writeback
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "qa.admin@lbl.gov"},
    )
    admin_sync_1 = client.post(f"/v1/qc/decisions/{decision_id}/sync-gsheet")
    assert admin_sync_1.status_code == 200
    sync1_body = admin_sync_1.json()
    assert sync1_body["decision_id"] == decision_id
    assert sync1_body["already_synced"] is False
    assert sync1_body["synced_to_gsheet"] is True
    assert sync1_body["gsheet_synced_at"] is not None
    note_after_first_sync = sync1_body["sheet_note"]
    assert note_after_first_sync.count(f"[QC_AUDIT id={decision_id}") == 1

    # 4. Calling sync-gsheet a second time is idempotent and does NOT duplicate [QC_AUDIT ...] tags
    admin_sync_2 = client.post(f"/v1/qc/decisions/{decision_id}/sync-gsheet")
    assert admin_sync_2.status_code == 200
    sync2_body = admin_sync_2.json()
    assert sync2_body["decision_id"] == decision_id
    assert sync2_body["already_synced"] is True
    assert sync2_body["synced_to_gsheet"] is True
    assert sync2_body["gsheet_synced_at"] is not None
    note_after_second_sync = sync2_body["sheet_note"]
    assert note_after_second_sync.count(f"[QC_AUDIT id={decision_id}") == 1

    # 5. If an analyst records a new Stage 1 decision on the synced row, synced_to_gsheet resets to False
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst2@beamcircular.org"},
    )
    re_edit_resp = client.post(
        "/v1/qc/decisions",
        json={
            "decision_id": decision_id,
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "decision_action": "approve_pass",
            "new_qc_pass": "pass",
            "review_note": "Re-verified calibration curve; sample is within spec",
        },
    )
    assert re_edit_resp.status_code == 200
    re_edited = re_edit_resp.json()["decision"]
    assert re_edited["new_qc_pass"] == "pass"
    assert re_edited["old_qc_pass"] == "fail"
    assert re_edited["synced_to_gsheet"] is False
    assert re_edited["gsheet_synced_at"] is None

    # 6. Admin batch sync picks up the re-edited pending decision and syncs it in-place
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "qa.admin@lbl.gov"},
    )
    batch_resp = client.post("/v1/qc/decisions/sync-gsheet-batch")
    assert batch_resp.status_code == 200
    batch_body = batch_resp.json()
    assert batch_body["synced_count"] == 1
    assert batch_body["synced_decision_ids"] == [decision_id]
    final_sheet_note = batch_body["results"][0]["sheet_note"]
    assert final_sheet_note.count(f"[QC_AUDIT id={decision_id}") == 1
    assert "Re-verified calibration curve" in final_sheet_note

    # 7. Updating an existing decision with backslash-digit sequences (\1, \2) in review_note
    # preserves literal text without regex backreference errors in both Stage 1 DB and Stage 2 GSheet sync
    backslash_note = r"Rechecked: still shows drift \1 percent off (see section \2)"
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst2@beamcircular.org"},
    )
    backslash_edit_resp = client.post(
        "/v1/qc/decisions",
        json={
            "decision_id": decision_id,
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "decision_action": "reject_fail",
            "new_qc_pass": "fail",
            "review_note": backslash_note,
        },
    )
    assert backslash_edit_resp.status_code == 200
    with Session(sqlite_engine) as session:
        rec = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-AS-01")
        ).first()
        assert rec is not None
        assert (rec.note or "").count(f"[QC_AUDIT id={decision_id}") == 1
        assert backslash_note in (rec.note or "")

    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "qa.admin@lbl.gov"},
    )
    backslash_sync_resp = client.post(
        f"/v1/qc/decisions/{decision_id}/sync-gsheet"
    )
    assert backslash_sync_resp.status_code == 200
    backslash_sync_body = backslash_sync_resp.json()
    assert backslash_sync_body["synced_to_gsheet"] is True
    assert backslash_sync_body["sheet_note"].count(f"[QC_AUDIT id={decision_id}") == 1
    assert backslash_note in backslash_sync_body["sheet_note"]
