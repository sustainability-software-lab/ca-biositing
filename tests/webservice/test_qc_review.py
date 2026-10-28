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
from ca_biositing.webservice.v1.endpoints.qc_review import (
    canonical_domain_slug,
    matches_replicate_group_key,
    normalize_replicate_group_key,
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


def test_github_issue_endpoint_fallback_and_api(
    client: TestClient,
    sqlite_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify POST /v1/qc/github-issue persists to PostgreSQL and supports both fallback URL and GitHub API."""
    import io
    import json
    import urllib.request

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    resp = client.post(
        "/v1/qc/github-issue",
        json={
            "title": "Ash outlier whisker clipping",
            "category": "UI / Chart Rendering Bug",
            "description": "Box whisker is clipped on Page 1",
            "expected_behavior": "Full whisker visible",
            "page": "Page 1 — Characterization & AI Brief",
            "resource": "Almond hulls",
            "domain_tab": "proximate",
            "qc_filter": "pass",
            "query_string": "?resource=Almond+hulls",
            "create_via_api": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["persisted"] is True
    assert isinstance(data["decision_id"], int)
    assert str(data["bug_record_id"]).startswith("BUG-")
    assert data["created_via_api"] is False
    assert "https://github.com/uw-ssec/ca-biositing/issues/new?" in data["issue_url"]
    assert "Ash+outlier+whisker+clipping" in data["issue_url"]

    # Verify the bug report was persisted in qc_review_decision
    with Session(sqlite_engine) as session:
        persisted_bug = session.get(QcReviewDecision, data["decision_id"])
        assert persisted_bug is not None
        assert persisted_bug.record_table == "portal_bug_report"
        assert persisted_bug.flag_type == "bug_report"
        assert persisted_bug.decision_status == "open"
        assert "Ash outlier whisker clipping" in persisted_bug.review_note

    # Verify mocked GitHub API path also persists with GH-<issue_number>
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_123")

    class _DummyResp:
        def __enter__(self) -> "_DummyResp":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self) -> bytes:
            return json.dumps(
                {
                    "number": 42,
                    "html_url": "https://github.com/uw-ssec/ca-biositing/issues/42",
                }
            ).encode("utf-8")

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=10: _DummyResp())

    api_resp = client.post(
        "/v1/qc/github-issue",
        json={
            "title": "Pretreatment yield axis label",
            "category": "Unit / Basis Normalization Issue",
            "description": "Y-axis unit label missing",
            "expected_behavior": "Show g/L",
            "page": "Page 3 — Multi-Resource Comparison",
            "resource": "Corn stover",
            "domain_tab": "pretreatment",
            "qc_filter": "all",
            "query_string": "?tab=pretreatment",
            "create_via_api": True,
        },
    )
    assert api_resp.status_code == 200
    api_data = api_resp.json()
    assert api_data["status"] == "ok"
    assert api_data["persisted"] is True
    assert api_data["created_via_api"] is True
    assert api_data["issue_number"] == 42
    assert api_data["bug_record_id"] == "GH-42"
    assert api_data["issue_url"] == "https://github.com/uw-ssec/ca-biositing/issues/42"

    # Verify GET /v1/qc/bug-issues returns both persisted bug reports
    bug_list_resp = client.get("/v1/qc/bug-issues")
    assert bug_list_resp.status_code == 200
    bug_list_body = bug_list_resp.json()
    assert bug_list_body["status"] == "ok"
    assert bug_list_body["count"] == 2
    assert [b["record_id"] for b in bug_list_body["bug_issues"]] == [
        "GH-42",
        data["bug_record_id"],
    ]

    # Verify GET /v1/qc/summary does not count portal_bug_report rows as analytical outliers
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst@lbl.gov"},
    )
    summary_resp = client.get("/v1/qc/summary")
    assert summary_resp.status_code == 200
    summary_body = summary_resp.json()
    assert summary_body["total_decisions"] == 0
    assert "bug_report" not in summary_body["by_flag_type"]


def test_replicate_group_key_normalization_in_decisions_and_tray_endpoints(
    client: TestClient,
    sqlite_engine,
) -> None:
    """Verify 6-part and 4-part replicate_group_key normalization in /v1/qc/decisions and /v1/qc/tray-to-workbench."""
    _seed_proximate_records(sqlite_engine)

    assert canonical_domain_slug("Proximate Analysis") == "proximate"
    assert canonical_domain_slug("ICP-OES / ICP-MS") == "icp"
    assert canonical_domain_slug("Ash") == "xrf"
    assert canonical_domain_slug("Pretreatment & Hydrolysis") == "pretreatment"
    assert canonical_domain_slug("Fermentation (Bioconversion)") == "fermentation"
    assert canonical_domain_slug(None) == "unknown"
    assert canonical_domain_slug("") == "unknown"

    assert (
        normalize_replicate_group_key(
            {
                "resource_name": "Corn Stover",
                "prepared_sample": "CS-PREP-01",
                "analysis_type": "Pretreatment & Hydrolysis",
                "parameter_name": "Glucose Yield",
                "prep_method": "Wiley Milled",
                "pt_method": "Dilute Acid",
                "eh_method": "CTec3",
                "experiment": "EXP-PT-01",
            }
        )
        == "corn stover::cs-prep-01::pretreatment::glucose yield::dilute acid · ctec3::exp-pt-01"
    )
    assert (
        normalize_replicate_group_key(
            {
                "resource_name": "Corn Stover",
                "prepared_sample": "CS-PREP-01",
                "analysis_type": "Fermentation (Bioconversion)",
                "parameter_name": "Ethanol",
                "prep_method": "Wiley Milled",
                "pt_method": "SHF",
                "strain": "S. cerevisiae",
                "time_h": 48,
                "experiment": "EXP-FERM-01",
            }
        )
        == "corn stover::cs-prep-01::fermentation::ethanol::shf · s. cerevisiae @ 48h::exp-ferm-01"
    )

    k6 = normalize_replicate_group_key(
        "Almond Hulls",
        "AH-01_prep",
        "Proximate Analysis",
        "Ash",
        "Mill-1mm",
        "EXP-2025-A",
    )
    assert k6 == "almond hulls::ah-01_prep::proximate::ash::mill-1mm::exp-2025-a"

    k4 = normalize_replicate_group_key(
        "grp::Almond Hulls::AH-01_prep::Proximate Analysis::Ash"
    )
    assert k4 == "almond hulls::ah-01_prep::proximate::ash"
    assert matches_replicate_group_key(k6, k4) is True

    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst1@lbl.gov"},
    )

    # 1. POST /v1/qc/decisions normalizes incoming 6-part replicate_group_key with grp:: prefix & mixed case
    dec_resp = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "replicate_group_key": "grp::Almond Shells::AS-PS-01::Proximate Analysis::Moisture::Oven-105C::EXP-01",
            "resource_name": "Almond Shells",
            "analysis_type": "Proximate Analysis",
            "parameter_name": "Moisture",
            "flag_type": "rsd_gt_10",
            "decision_action": "reject_fail",
            "new_qc_pass": "fail",
            "review_note": "Normalized 6-part key check",
        },
    )
    assert dec_resp.status_code == 200
    assert (
        dec_resp.json()["decision"]["replicate_group_key"]
        == "almond shells::as-ps-01::proximate::moisture::oven-105c::exp-01"
    )

    # 2. POST /v1/qc/tray-to-workbench normalizes incoming 4-part or 6-part replicate_group_key
    tray_resp = client.post(
        "/v1/qc/tray-to-workbench",
        json={
            "record_table": "proximate_record",
            "record_ids": ["PROX-AS-02"],
            "replicate_group_key": "grp::Almond Shells::AS-PS-01::Proximate Analysis::Ash",
            "resource_name": "Almond Shells",
            "analysis_type": "Proximate Analysis",
            "parameter_name": "Ash",
            "flag_type": "iqr_outlier",
            "review_note": "Normalized 4-part tray key check",
        },
    )
    assert tray_resp.status_code == 200
    tray_decisions = tray_resp.json()["decisions"]
    assert len(tray_decisions) == 1
    assert (
        tray_decisions[0]["replicate_group_key"]
        == "almond shells::as-ps-01::proximate::ash"
    )


def test_card5a_decision_actions_and_legacy_payload_mapping(
    client: TestClient,
    sqlite_engine,
) -> None:
    """Verify provisional/in_review/keep_note/accept_with_note/re_assay/keep/exclude_qc_fail and legacy client fields map cleanly."""
    _seed_proximate_records(sqlite_engine)
    client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst1@lbl.gov"},
    )

    # 1. Default in_review / provisional submission does NOT flip qc_pass to 'fail'
    resp_prov = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "target_record_ids": ["PROX-AS-01", "PROX-AS-02"],
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "previous_qc_status": "pass",
            "new_qc_status": "provisional",
            "decision": "accept_with_note",
            "status": "pending",
            "rationale_tags": ["Method Note", "Check Notebook"],
            "audit_note": "Flagged for PI review without failing replicate",
            "assigned_to_email": "Analyst2@BeamCircular.org",
        },
    )
    assert resp_prov.status_code == 200
    dec_prov = resp_prov.json()["decision"]
    assert dec_prov["decision_status"] == "in_review"
    assert dec_prov["new_qc_pass"] is None
    assert dec_prov["old_qc_pass"] == "pass"
    assert dec_prov["assigned_to_email"] == "analyst2@beamcircular.org"
    assert dec_prov["review_note"] == "Flagged for PI review without failing replicate"
    assert dec_prov["rationale_chips"] == "Method Note, Check Notebook"

    with Session(sqlite_engine) as session:
        rec1 = session.exec(
            select(ProximateRecord).where(ProximateRecord.record_id == "PROX-AS-01")
        ).first()
        assert rec1 is not None
        assert rec1.qc_pass == "pass"

    # 2. keep_note action maps to decision_status='in_review', new_qc_pass=None
    resp_keep_note = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-02",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "decision_action": "keep_note",
            "review_note": "Keep with note from Explorer popover",
            "assigned_to_email": "analyst1@lbl.gov",
        },
    )
    assert resp_keep_note.status_code == 200
    dec_kn = resp_keep_note.json()["decision"]
    assert dec_kn["decision_status"] == "in_review"
    assert dec_kn["new_qc_pass"] is None
    assert dec_kn["assigned_to_email"] == "analyst1@lbl.gov"

    # 3. re_assay action maps to decision_status='needs_retest', new_qc_pass=None
    resp_reassay = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-03",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "ash",
            "decision": "re_assay",
            "new_qc_status": "re_assay",
            "audit_note": "Needs bench re-assay",
        },
    )
    assert resp_reassay.status_code == 200
    dec_ra = resp_reassay.json()["decision"]
    assert dec_ra["decision_status"] == "needs_retest"
    assert dec_ra["new_qc_pass"] is None

    # 4. keep action maps to decision_status='resolved', new_qc_pass='pass'
    resp_keep = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-03",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "ash",
            "decision": "keep",
            "new_qc_status": "pass",
            "audit_note": "Verified valid replicate",
        },
    )
    assert resp_keep.status_code == 200
    dec_keep = resp_keep.json()["decision"]
    assert dec_keep["decision_status"] == "resolved"
    assert dec_keep["new_qc_pass"] == "pass"

    # 5. exclude_qc_fail action maps to decision_status='resolved', new_qc_pass='fail'
    resp_fail = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-03",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "ash",
            "decision": "exclude_qc_fail",
            "new_qc_status": "fail",
            "audit_note": "Confirmed ash outlier",
        },
    )
    assert resp_fail.status_code == 200
    dec_fail = resp_fail.json()["decision"]
    assert dec_fail["decision_status"] == "resolved"
    assert dec_fail["new_qc_pass"] == "fail"


def test_assign_qc_decisions_batch_updates_existing_and_upserts_static_candidates(
    client: TestClient,
    sqlite_engine,
    tmp_path: Path,
) -> None:
    """Verify POST /v1/qc/decisions/assign-batch atomically assigns existing DB decisions and upserts unpersisted static queue candidates."""
    _seed_proximate_records(sqlite_engine)

    login_resp = client.post(
        "/v1/qc/auth/dev-login",
        json={"email": "analyst1@lbl.gov", "name": "Analyst One"},
    )
    assert login_resp.status_code == 200

    # 1. Create an existing DB decision row for PROX-AS-01
    existing_resp = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "replicate_group_key": "almond shells::as-ps-01::proximate::moisture::milled 2mm::exp-01",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "flag_type": "rsd_gt_10",
            "flag_trigger_value": "RSD=18.4%",
            "decision_action": "in_review",
            "review_note": "Existing open finding",
        },
    )
    assert existing_resp.status_code == 200
    existing_id = existing_resp.json()["decision"]["id"]

    # 2. Call POST /v1/qc/decisions/assign-batch with 1 existing DB decision + 1 unpersisted static candidate
    batch_resp = client.post(
        "/v1/qc/decisions/assign-batch",
        json={
            "assigned_to_email": "Reviewer.Lead@lbl.gov",
            "review_note": "Bulk assigned for weekly review",
            "items": [
                {
                    "id": existing_id,
                    "decision_id": f"QC-{existing_id:04d}",
                    "record_table": "proximate_record",
                    "record_id": "PROX-AS-01",
                },
                {
                    "decision_id": "QC-0002",
                    "record_table": "proximate_record",
                    "record_id": "PROX-AS-02",
                    "record_ids": ["PROX-AS-02", "PROX-AS-03"],
                    "replicate_group_key": "almond shells::as-ps-02::proximate::ash::milled 2mm::exp-01",
                    "resource_name": "almond shells",
                    "analysis_type": "Proximate Analysis",
                    "parameter_name": "Ash",
                    "flag_type": "rsd_gt_20",
                    "flag_trigger_value": "RSD=24.1%",
                },
            ],
        },
    )
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["status"] == "ok"
    assert batch_data["assigned_count"] == 2
    assert batch_data["assigned_to_email"] == "reviewer.lead@lbl.gov"
    assert batch_data["assigned_by_email"] == "analyst1@lbl.gov"
    assert isinstance(batch_data.get("audit_history"), list)
    assert batch_data["audit_history"][0]["action"] == "bulk_assign"
    assert len(batch_data["decisions"]) == 2

    by_rec = {d["record_id"]: d for d in batch_data["decisions"]}
    assert by_rec["PROX-AS-01"]["id"] == existing_id
    assert by_rec["PROX-AS-01"]["assigned_to_email"] == "reviewer.lead@lbl.gov"
    assert by_rec["PROX-AS-01"]["assigned_by_email"] == "analyst1@lbl.gov"
    assert by_rec["PROX-AS-01"]["decision_status"] == "in_review"
    assert by_rec["PROX-AS-01"]["review_note"] == "Bulk assigned for weekly review"
    assert by_rec["PROX-AS-01"]["audit_history"][0]["action"] == "bulk_assign"

    assert by_rec["PROX-AS-02"]["id"] != existing_id
    assert by_rec["PROX-AS-02"]["assigned_to_email"] == "reviewer.lead@lbl.gov"
    assert by_rec["PROX-AS-02"]["assigned_by_email"] == "analyst1@lbl.gov"
    assert by_rec["PROX-AS-02"]["decision_status"] == "in_review"
    assert by_rec["PROX-AS-02"]["decision_action"] == "flag_for_review"
    assert by_rec["PROX-AS-02"]["old_qc_pass"] == "pass"

    # 2b. Verify >500 items per batch is rejected with HTTP 400
    too_large_resp = client.post(
        "/v1/qc/decisions/assign-batch",
        json={
            "assigned_to_email": "Reviewer.Lead@lbl.gov",
            "items": [
                {
                    "decision_id": f"QC-{i:04d}",
                    "record_table": "proximate_record",
                    "record_id": f"PROX-AS-{i:04d}",
                }
                for i in range(501)
            ],
        },
    )
    assert too_large_resp.status_code == 400
    assert "cannot exceed 500 items" in too_large_resp.json()["detail"]

    # 3. Resolve existing_id and verify reassigning a resolved decision preserves decision_status == "resolved"
    resolve_resp = client.post(
        "/v1/qc/decisions",
        json={
            "record_table": "proximate_record",
            "record_id": "PROX-AS-01",
            "replicate_group_key": "almond shells::as-ps-01::proximate::moisture::milled 2mm::exp-01",
            "resource_name": "almond shells",
            "analysis_type": "proximate",
            "parameter_name": "moisture",
            "flag_type": "rsd_gt_10",
            "decision_action": "pass",
            "new_qc_pass": "pass",
            "review_note": "Resolved as pass",
        },
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["decision"]["decision_status"] == "resolved"

    reassign_resolved_resp = client.post(
        "/v1/qc/decisions/assign-batch",
        json={
            "assigned_to_email": "Senior.Auditor@lbl.gov",
            "items": [
                {
                    "id": existing_id,
                    "record_table": "proximate_record",
                    "record_id": "PROX-AS-01",
                }
            ],
        },
    )
    assert reassign_resolved_resp.status_code == 200
    reassigned_dec = reassign_resolved_resp.json()["decisions"][0]
    assert reassigned_dec["id"] == existing_id
    assert reassigned_dec["assigned_to_email"] == "senior.auditor@lbl.gov"
    assert reassigned_dec["decision_status"] == "resolved"

    # 4. Verify seed CSV was synced with both assigned rows
    seed_csv_path = tmp_path / "qc_review_decisions_seed.csv"
    csv_rows = read_seed_csv(seed_csv_path)
    assert len(csv_rows) == 2
