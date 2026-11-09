"""Promoters: everyone logged in can read; only admins create, edit and archive.

There is no DELETE: archiving keeps the historical attribution of the promoter's leads.
"""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from pydantic import BaseModel, EmailStr, Field

from nexus.db import get_session, utcnow
from nexus.models import Promoter, Role
from nexus.security import login_required
from nexus.validation import parse_body

bp = Blueprint("promoters", __name__, url_prefix="/api/promoters")


class PromoterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None


class PromoterPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None


@bp.get("")
@login_required()
def list_promoters():
    query = get_session().query(Promoter)
    if request.args.get("include_archived") != "1":
        query = query.filter(Promoter.archived_at.is_(None))
    promoters = query.order_by(Promoter.name).all()
    return jsonify(promoters=[p.to_dict() for p in promoters])


@bp.post("")
@login_required(Role.ADMIN)
def create_promoter():
    body = parse_body(PromoterIn)
    db = get_session()
    promoter = Promoter(name=body.name.strip(), email=body.email.lower() if body.email else None)
    db.add(promoter)
    db.commit()
    return jsonify(promoter=promoter.to_dict()), 201


@bp.get("/<int:promoter_id>")
@login_required()
def get_promoter(promoter_id: int):
    promoter = get_session().get(Promoter, promoter_id) or abort(404)
    return jsonify(promoter=promoter.to_dict())


@bp.patch("/<int:promoter_id>")
@login_required(Role.ADMIN)
def update_promoter(promoter_id: int):
    body = parse_body(PromoterPatch)
    db = get_session()
    promoter = db.get(Promoter, promoter_id) or abort(404)
    if body.name is not None:
        promoter.name = body.name.strip()
    if "email" in body.model_fields_set:
        promoter.email = body.email.lower() if body.email else None
    db.commit()
    return jsonify(promoter=promoter.to_dict())


@bp.post("/<int:promoter_id>/archive")
@login_required(Role.ADMIN)
def archive_promoter(promoter_id: int):
    db = get_session()
    promoter = db.get(Promoter, promoter_id) or abort(404)
    if promoter.archived_at is None:
        promoter.archived_at = utcnow()
        db.commit()
    return jsonify(promoter=promoter.to_dict())


@bp.post("/<int:promoter_id>/unarchive")
@login_required(Role.ADMIN)
def unarchive_promoter(promoter_id: int):
    db = get_session()
    promoter = db.get(Promoter, promoter_id) or abort(404)
    promoter.archived_at = None
    db.commit()
    return jsonify(promoter=promoter.to_dict())
