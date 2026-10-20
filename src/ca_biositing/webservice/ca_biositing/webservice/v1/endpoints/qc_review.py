"""Portal authentication, 2-role RBAC, and two-stage QC Audit Workbench endpoints (`/v1/qc/*`).

All routes under `/v1/qc` use the isolated `biocirv_portal_token` cookie and have zero
coupling to CalBioScape endpoints or `ca_biositing.pipeline`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ca_biositing.datamodels.database import get_session
from ca_biositing.datamodels.models.qc.qc_review_decision import QcReviewDecision
from ca_biositing.webservice.config import config
from ca_biositing.webservice.services.gsheet_sync_service import (
    sync_pending_decisions_batch_to_gsheet,
    sync_single_decision_to_gsheet,
)
from ca_biositing.webservice.services import portal_auth as _portal_auth_service
from ca_biositing.webservice.services.portal_auth import (
    PortalUser,
    authorize_portal_email,
    clear_portal_auth_cookie,
    create_portal_token,
    require_portal_admin,
    require_portal_analyst,
    set_portal_auth_cookie,
    verify_google_id_token,
)
from ca_biositing.webservice.services.qc_ledger_service import (
    append_or_update_seed_csv,
    export_decisions_to_csv_string,
    record_stage1_decision,
    serialize_decision,
)

_ORIG_VERIFY_GOOGLE_ID_TOKEN = verify_google_id_token

router = APIRouter(prefix="/qc", tags=["qc-review"])

SessionDep = Annotated[Session, Depends(get_session)]
AnalystDep = Annotated[PortalUser, Depends(require_portal_analyst)]
AdminDep = Annotated[PortalUser, Depends(require_portal_admin)]


class GoogleAuthRequest(BaseModel):
    """Request body for Google OIDC login."""

    id_token: str | None = Field(default=None, description="Google OIDC ID token.")
    credential: str | None = Field(
        default=None,
        description="Google Sign-In credential alias for ID token.",
    )


class DevLoginRequest(BaseModel):
    """Request body for localhost-only developer login."""

    email: str = Field(description="Whitelisted analyst or admin email address.")
    name: str | None = Field(default=None, description="Optional display name.")


class Stage1DecisionRequest(BaseModel):
    """Request body for creating or updating a Stage 1 QC review decision."""

    id: int | None = Field(default=None)
    decision_id: int | None = Field(default=None)
    record_table: str = Field(default="proximate_record")
    record_id: str | None = Field(default=None)
    record_ids: list[str] | None = Field(default=None)
    replicate_group_key: str | None = Field(default=None)
    resource_name: str = Field(default="unknown")
    analysis_type: str | None = Field(default=None)
    parameter_name: str | None = Field(default=None)
    flag_type: str = Field(default="analyst_flagged")
    flag_trigger_value: str | None = Field(default=None)
    old_qc_pass: str | None = Field(default=None)
    new_qc_pass: str | None = Field(default=None)
    decision_status: str | None = Field(default=None)
    status: str | None = Field(default=None)
    decision_action: str | None = Field(default=None)
    rationale_chips: list[str] | str | None = Field(default=None)
    review_note: str = Field(default="")
    assigned_to_email: str | None = Field(default=None)


class TrayWorkbenchItem(BaseModel):
    """Single item or replicate group sent from the Selection & Export Tray to the Audit Workbench."""

    record_table: str = Field(default="proximate_record")
    record_id: str | None = Field(default=None)
    record_ids: list[str] | None = Field(default=None)
    replicate_group_key: str | None = Field(default=None)
    resource_name: str = Field(default="unknown")
    analysis_type: str | None = Field(default=None)
    parameter_name: str | None = Field(default=None)
    flag_type: str = Field(default="analyst_flagged")
    flag_trigger_value: str | None = Field(default=None)
    old_qc_pass: str | None = Field(default=None)
    assigned_to_email: str | None = Field(default=None)
    review_note: str = Field(default="")


class TrayToWorkbenchRequest(BaseModel):
    """Request body for `POST /v1/qc/tray-to-workbench`."""

    items: list[TrayWorkbenchItem] | None = Field(default=None)
    record_table: str = Field(default="proximate_record")
    record_id: str | None = Field(default=None)
    record_ids: list[str] | None = Field(default=None)
    replicate_group_key: str | None = Field(default=None)
    resource_name: str = Field(default="unknown")
    analysis_type: str | None = Field(default=None)
    parameter_name: str | None = Field(default=None)
    flag_type: str = Field(default="analyst_flagged")
    flag_trigger_value: str | None = Field(default=None)
    old_qc_pass: str | None = Field(default=None)
    assigned_to_email: str | None = Field(default=None)
    review_note: str = Field(default="")


class AssignDecisionRequest(BaseModel):
    """Request body for `PATCH /v1/qc/decisions/{id}/assign`."""

    assigned_to_email: str | None = Field(
        default=None,
        description="Target analyst email, 'me', or None/empty to unassign.",
    )


class BatchGSheetSyncRequest(BaseModel):
    """Optional request body for `POST /v1/qc/decisions/sync-gsheet-batch`."""

    decision_ids: list[int] | None = Field(default=None)


def _count_assigned_open(session: Session, email: str) -> int:
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return 0
    rows = list(
        session.exec(
            select(QcReviewDecision).where(
                QcReviewDecision.assigned_to_email == clean_email,
                QcReviewDecision.decision_status.in_(
                    ["open", "in_review", "needs_retest"]
                ),
            )
        ).all()
    )
    return len(rows)


@router.get("/auth/config")
def get_portal_auth_public_config() -> dict[str, Any]:
    """Return public OIDC configuration (`google_client_id`, `allowed_domains`) for `login.html`."""
    return {
        "status": "ok",
        "google_client_id": (config.google_client_id or "").strip(),
        "allowed_domains": list(config.dashboard_allowed_domains or []),
        "require_dashboard_auth": bool(config.require_dashboard_auth),
    }


@router.post("/auth/google")
def login_with_google_oidc(
    payload: GoogleAuthRequest,
    response: Response,
    session: SessionDep,
) -> dict[str, Any]:
    """Verify a Google OIDC ID token, enforce domain/email allowlist, and set `biocirv_portal_token`."""
    raw_token = (payload.id_token or payload.credential or "").strip()
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google OIDC id_token.",
        )

    verifier = (
        verify_google_id_token
        if verify_google_id_token is not _ORIG_VERIFY_GOOGLE_ID_TOKEN
        else _portal_auth_service.verify_google_id_token
    )
    claims = verifier(raw_token)
    email = str(claims.get("email") or "").strip().lower()
    name = claims.get("name")
    user = authorize_portal_email(email=email, name=name, auth_mode="google_oidc")
    jwt_token = create_portal_token(user)
    set_portal_auth_cookie(response, jwt_token)
    assigned_open_count = _count_assigned_open(session, user.email)

    return {
        "status": "ok",
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "auth_mode": user.auth_mode,
        "assigned_open_count": assigned_open_count,
        "token": jwt_token,
        "user": {
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "auth_mode": user.auth_mode,
            "assigned_open_count": assigned_open_count,
        },
    }


@router.post("/auth/dev-login")
def login_local_dev(
    payload: DevLoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> dict[str, Any]:
    """Localhost-only developer login that still enforces the portal domain/email allowlist."""
    env_name = os.environ.get("ENV", "development").strip().lower()
    client_host = (request.client.host if request.client else "").strip().lower()
    url_host = (request.url.hostname or "").strip().lower()
    allowed_local_hosts = {"127.0.0.1", "localhost", "::1", "testclient"}

    if env_name == "production" or (
        client_host not in allowed_local_hosts and url_host not in allowed_local_hosts
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer login is restricted to localhost in non-production environments.",
        )

    user = authorize_portal_email(
        email=payload.email,
        name=payload.name,
        auth_mode="dev_login",
    )
    jwt_token = create_portal_token(user)
    set_portal_auth_cookie(response, jwt_token)
    assigned_open_count = _count_assigned_open(session, user.email)

    return {
        "status": "ok",
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "auth_mode": user.auth_mode,
        "assigned_open_count": assigned_open_count,
        "token": jwt_token,
        "user": {
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "auth_mode": user.auth_mode,
            "assigned_open_count": assigned_open_count,
        },
    }


@router.get("/auth/me")
def get_current_portal_user(
    user: AnalystDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Return the authenticated portal user's identity, role, and open assigned review count."""
    assigned_open_count = _count_assigned_open(session, user.email)
    return {
        "status": "ok",
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "auth_mode": user.auth_mode,
        "assigned_open_count": assigned_open_count,
        "user": {
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "auth_mode": user.auth_mode,
            "assigned_open_count": assigned_open_count,
        },
    }


@router.post("/auth/logout")
def logout_portal_user(response: Response) -> dict[str, Any]:
    """Clear the `biocirv_portal_token` cookie."""
    clear_portal_auth_cookie(response)
    return {
        "status": "ok",
        "authenticated": False,
    }


def _query_filtered_decisions(
    session: Session,
    user: PortalUser,
    assigned_to: str | None = None,
    decision_status: str | None = None,
    flag_type: str | None = None,
    resource_name: str | None = None,
    analysis_type: str | None = None,
    parameter_name: str | None = None,
    synced_to_gsheet: bool | None = None,
) -> list[QcReviewDecision]:
    stmt = select(QcReviewDecision)
    rows = list(session.exec(stmt).all())

    if assigned_to is not None and assigned_to.strip():
        target = assigned_to.strip().lower()
        if target == "me":
            rows = [
                r
                for r in rows
                if (r.assigned_to_email or "").strip().lower() == user.email.lower()
            ]
        elif target in {"unassigned", "none"}:
            rows = [r for r in rows if not (r.assigned_to_email or "").strip()]
        else:
            rows = [
                r
                for r in rows
                if (r.assigned_to_email or "").strip().lower() == target
            ]

    if decision_status is not None and decision_status.strip():
        allowed_statuses = {
            s.strip().lower() for s in decision_status.split(",") if s.strip()
        }
        rows = [
            r
            for r in rows
            if (r.decision_status or "").strip().lower() in allowed_statuses
        ]

    if flag_type is not None and flag_type.strip():
        allowed_flags = {
            f.strip().lower() for f in flag_type.split(",") if f.strip()
        }
        rows = [
            r for r in rows if (r.flag_type or "").strip().lower() in allowed_flags
        ]

    if resource_name is not None and resource_name.strip():
        res_norm = resource_name.strip().lower()
        rows = [
            r for r in rows if (r.resource_name or "").strip().lower() == res_norm
        ]

    if analysis_type is not None and analysis_type.strip():
        at_norm = analysis_type.strip().lower()
        rows = [
            r for r in rows if (r.analysis_type or "").strip().lower() == at_norm
        ]

    if parameter_name is not None and parameter_name.strip():
        param_norm = parameter_name.strip().lower()
        rows = [
            r for r in rows if (r.parameter_name or "").strip().lower() == param_norm
        ]

    if synced_to_gsheet is not None:
        rows = [r for r in rows if bool(r.synced_to_gsheet) is bool(synced_to_gsheet)]

    rows.sort(
        key=lambda d: (
            d.updated_at or datetime.min.replace(tzinfo=timezone.utc),
            d.id or 0,
        ),
        reverse=True,
    )
    return rows


@router.get("/decisions")
def list_qc_decisions(
    user: AnalystDep,
    session: SessionDep,
    assigned_to: str | None = Query(
        default=None,
        description="Filter by 'me', 'unassigned', or a specific analyst email.",
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by decision_status (e.g. 'open', 'in_review', 'needs_retest', 'resolved').",
    ),
    decision_status: str | None = Query(default=None),
    flag_type: str | None = Query(default=None),
    resource_name: str | None = Query(default=None),
    analysis_type: str | None = Query(default=None),
    parameter_name: str | None = Query(default=None),
    synced_to_gsheet: bool | None = Query(default=None),
) -> dict[str, Any]:
    """List QC review decisions with optional queue and facet filters."""
    effective_status = decision_status or status_filter
    rows = _query_filtered_decisions(
        session=session,
        user=user,
        assigned_to=assigned_to,
        decision_status=effective_status,
        flag_type=flag_type,
        resource_name=resource_name,
        analysis_type=analysis_type,
        parameter_name=parameter_name,
        synced_to_gsheet=synced_to_gsheet,
    )
    serialized = [serialize_decision(r) for r in rows]
    return {
        "status": "ok",
        "count": len(serialized),
        "decisions": serialized,
        "items": serialized,
    }


@router.post("/decisions")
def create_or_update_stage1_decision(
    payload: Stage1DecisionRequest,
    user: AnalystDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Record a Stage 1 QC review decision (`analyst` or `admin`).

    Immediately updates `qc_review_decision`, the analytical record table in PostgreSQL,
    and the seed CSV, while setting `synced_to_gsheet = False`.
    """
    all_record_ids: list[str] = []
    if payload.record_ids:
        for rid in payload.record_ids:
            if rid and str(rid).strip():
                all_record_ids.append(str(rid).strip())
    primary_record_id = (payload.record_id or "").strip()
    if not primary_record_id and all_record_ids:
        primary_record_id = all_record_ids[0]
    if not primary_record_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either record_id or record_ids must be provided.",
        )

    assigned = payload.assigned_to_email
    if assigned and assigned.strip().lower() == "me":
        assigned = user.email

    decision, updated_record_ids = record_stage1_decision(
        session=session,
        actor_email=user.email,
        decision_id=payload.decision_id or payload.id,
        record_table=payload.record_table,
        record_id=primary_record_id,
        record_ids=all_record_ids or [primary_record_id],
        replicate_group_key=payload.replicate_group_key,
        resource_name=payload.resource_name,
        analysis_type=payload.analysis_type,
        parameter_name=payload.parameter_name,
        flag_type=payload.flag_type,
        flag_trigger_value=payload.flag_trigger_value,
        old_qc_pass=payload.old_qc_pass,
        new_qc_pass=payload.new_qc_pass,
        decision_action=payload.decision_action,
        decision_status=payload.decision_status or payload.status,
        rationale_chips=payload.rationale_chips,
        review_note=payload.review_note,
        assigned_to_email=assigned,
    )
    serialized = serialize_decision(decision)
    return {
        "status": "ok",
        "decision": serialized,
        "updated_record_ids": updated_record_ids,
        "synced_to_gsheet": False,
    }


@router.post("/tray-to-workbench")
def send_selection_tray_to_workbench(
    payload: TrayToWorkbenchRequest,
    user: AnalystDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Create or update open `QcReviewDecision` rows from the Products 2 & 3 Selection & Export Tray."""
    items_to_process: list[TrayWorkbenchItem] = []
    if payload.items:
        items_to_process.extend(payload.items)
    else:
        items_to_process.append(
            TrayWorkbenchItem(
                record_table=payload.record_table,
                record_id=payload.record_id,
                record_ids=payload.record_ids,
                replicate_group_key=payload.replicate_group_key,
                resource_name=payload.resource_name,
                analysis_type=payload.analysis_type,
                parameter_name=payload.parameter_name,
                flag_type=payload.flag_type,
                flag_trigger_value=payload.flag_trigger_value,
                old_qc_pass=payload.old_qc_pass,
                assigned_to_email=payload.assigned_to_email,
                review_note=payload.review_note,
            )
        )

    created_decisions: list[QcReviewDecision] = []
    for item in items_to_process:
        rids = [str(r).strip() for r in (item.record_ids or []) if str(r).strip()]
        if item.record_id and item.record_id.strip() not in rids:
            rids.insert(0, item.record_id.strip())
        if not rids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each tray item must include record_id or record_ids.",
            )

        assigned = item.assigned_to_email or payload.assigned_to_email
        if assigned and assigned.strip().lower() == "me":
            assigned = user.email

        for rid in rids:
            decision, _ = record_stage1_decision(
                session=session,
                actor_email=user.email,
                record_table=item.record_table or payload.record_table,
                record_id=rid,
                record_ids=[rid],
                replicate_group_key=item.replicate_group_key
                or payload.replicate_group_key,
                resource_name=item.resource_name or payload.resource_name,
                analysis_type=item.analysis_type or payload.analysis_type,
                parameter_name=item.parameter_name or payload.parameter_name,
                flag_type=item.flag_type or payload.flag_type or "analyst_flagged",
                flag_trigger_value=item.flag_trigger_value
                or payload.flag_trigger_value,
                old_qc_pass=item.old_qc_pass or payload.old_qc_pass,
                new_qc_pass=None,
                decision_action="flag_for_review",
                decision_status="open",
                review_note=item.review_note
                or payload.review_note
                or "Flagged from Selection & Export Tray",
                assigned_to_email=assigned,
            )
            created_decisions.append(decision)

    serialized_list = [serialize_decision(d) for d in created_decisions]
    first_id = created_decisions[0].id if created_decisions else None
    workbench_url = (
        f"/v1/dashboards/metadata/resource_audit_workbench.html?decision_id={first_id}"
        if first_id is not None
        else "/v1/dashboards/metadata/resource_audit_workbench.html"
    )
    return {
        "status": "ok",
        "created_count": len(serialized_list),
        "decision_id": first_id,
        "decision_ids": [d.id for d in created_decisions if d.id is not None],
        "workbench_url": workbench_url,
        "decisions": serialized_list,
    }


@router.patch("/decisions/{decision_id}/assign")
def assign_qc_decision(
    decision_id: int,
    payload: AssignDecisionRequest,
    user: AnalystDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Assign or unassign a `QcReviewDecision` to an analyst email."""
    decision = session.get(QcReviewDecision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QC decision {decision_id} not found.",
        )

    raw_target = (payload.assigned_to_email or "").strip().lower()
    if raw_target == "me":
        decision.assigned_to_email = user.email.lower()
    elif not raw_target or raw_target in {"unassigned", "none", "null"}:
        decision.assigned_to_email = None
    else:
        decision.assigned_to_email = raw_target

    decision.updated_at = datetime.now(timezone.utc)
    session.add(decision)
    session.commit()
    session.refresh(decision)
    append_or_update_seed_csv(decision)

    return {
        "status": "ok",
        "decision": serialize_decision(decision),
    }


@router.get("/summary")
def get_qc_review_summary(
    user: AnalystDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Return aggregate queue counts for the QC Audit Workbench."""
    rows = list(session.exec(select(QcReviewDecision)).all())
    by_status: dict[str, int] = {}
    by_flag_type: dict[str, int] = {}
    by_resource: dict[str, int] = {}
    assigned_to_me_open = 0
    unassigned_open = 0
    pending_gsheet_sync = 0
    synced_to_gsheet = 0

    for r in rows:
        st = (r.decision_status or "open").strip().lower()
        by_status[st] = by_status.get(st, 0) + 1

        ft = (r.flag_type or "analyst_flagged").strip().lower()
        by_flag_type[ft] = by_flag_type.get(ft, 0) + 1

        res = (r.resource_name or "unknown").strip().lower()
        by_resource[res] = by_resource.get(res, 0) + 1

        is_open_like = st in {"open", "in_review", "needs_retest"}
        assignee = (r.assigned_to_email or "").strip().lower()
        if is_open_like:
            if assignee == user.email.lower():
                assigned_to_me_open += 1
            elif not assignee:
                unassigned_open += 1

        if r.synced_to_gsheet:
            synced_to_gsheet += 1
        elif st == "resolved":
            pending_gsheet_sync += 1

    return {
        "status": "ok",
        "total_decisions": len(rows),
        "assigned_open_count": assigned_to_me_open,
        "unassigned_open_count": unassigned_open,
        "pending_gsheet_sync_count": pending_gsheet_sync,
        "synced_to_gsheet_count": synced_to_gsheet,
        "by_status": by_status,
        "by_flag_type": by_flag_type,
        "by_resource": by_resource,
    }


@router.get("/export.csv")
def export_qc_decisions_csv(
    user: AnalystDep,
    session: SessionDep,
    assigned_to: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    decision_status: str | None = Query(default=None),
    flag_type: str | None = Query(default=None),
    resource_name: str | None = Query(default=None),
    analysis_type: str | None = Query(default=None),
    synced_to_gsheet: bool | None = Query(default=None),
) -> PlainTextResponse:
    """Export filtered `QcReviewDecision` rows as a CSV attachment."""
    rows = _query_filtered_decisions(
        session=session,
        user=user,
        assigned_to=assigned_to,
        decision_status=decision_status or status_filter,
        flag_type=flag_type,
        resource_name=resource_name,
        analysis_type=analysis_type,
        synced_to_gsheet=synced_to_gsheet,
    )
    csv_text = export_decisions_to_csv_string(rows)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="qc_review_decisions.csv"'
        },
    )


@router.post("/decisions/{decision_id}/sync-gsheet")
def sync_decision_to_gsheet_endpoint(
    decision_id: int,
    admin: AdminDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Admin-only Stage 2 endpoint: sync a single resolved QC decision to Google Sheets."""
    return sync_single_decision_to_gsheet(
        session=session,
        decision_id=decision_id,
        admin_email=admin.email,
    )


@router.post("/decisions/sync-gsheet-batch")
def sync_pending_decisions_batch_endpoint(
    admin: AdminDep,
    session: SessionDep,
    payload: BatchGSheetSyncRequest | None = Body(default=None),
) -> dict[str, Any]:
    """Admin-only Stage 2 endpoint: batch-sync pending resolved QC decisions to Google Sheets."""
    decision_ids = payload.decision_ids if payload is not None else None
    return sync_pending_decisions_batch_to_gsheet(
        session=session,
        admin_email=admin.email,
        decision_ids=decision_ids,
    )
