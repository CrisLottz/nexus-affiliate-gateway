"""Leads list for logged-in users; manual retry for admins."""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from nexus.db import get_session
from nexus.models import CrmStatus, Lead, Role
from nexus.outbox import requeue_lead
from nexus.security import login_required

bp = Blueprint("leads", __name__, url_prefix="/api/leads")

PAGE_SIZE = 25


@bp.get("")
@login_required()
def list_leads():
    db = get_session()
    stmt = select(Lead)
    if promoter_id := request.args.get("promoter_id", type=int):
        stmt = stmt.where(Lead.promoter_id == promoter_id)
    if (status := request.args.get("crm_status")) in {s.value for s in CrmStatus}:
        stmt = stmt.where(Lead.crm_status == status)
    if q := (request.args.get("q") or "").strip().lower():
        like = f"%{q}%"
        stmt = stmt.where(
            func.lower(Lead.email).like(like)
            | func.lower(Lead.first_name).like(like)
            | func.lower(Lead.last_name).like(like)
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    page = max(request.args.get("page", 1, type=int), 1)
    leads = db.scalars(
        stmt.options(joinedload(Lead.promoter))
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return jsonify(
        leads=[lead.to_dict() for lead in leads], page=page, page_size=PAGE_SIZE, total=total
    )


@bp.post("/<int:lead_id>/retry")
@login_required(Role.ADMIN)
def retry_lead(lead_id: int):
    db = get_session()
    lead = db.get(Lead, lead_id) or abort(404)
    if lead.crm_status == CrmStatus.SYNCED:
        return jsonify(error="conflict", message="Lead is already synced"), 409
    requeue_lead(db, lead)
    return jsonify(lead=lead.to_dict())
