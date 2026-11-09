"""Public referral flow: the visitor lands on /join?ref=<public_id> and submits the form.

Order matters: (1) save lead + outbox event in one transaction, (2) only then try the CRM.
A CRM outage can delay a lead but never lose it.
"""

from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from nexus.crm import get_provider
from nexus.db import get_session
from nexus.extensions import limiter
from nexus.models import Lead, Promoter
from nexus.outbox import enqueue_lead, process_event
from nexus.validation import parse_body

log = logging.getLogger(__name__)
bp = Blueprint("public", __name__, url_prefix="/api/public")


class LeadIn(BaseModel):
    ref: str | None = Field(default=None, max_length=16)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32, pattern=r"^[0-9+()\-\s]*$")
    # Honeypot: hidden in the form. Humans leave it empty; naive bots fill every field.
    website: str | None = None


def _active_promoter(ref: str | None) -> Promoter | None:
    if not ref:
        return None
    return get_session().scalar(
        select(Promoter).where(Promoter.public_id == ref, Promoter.archived_at.is_(None))
    )


@bp.get("/promoters/<ref>")
def promoter_card(ref: str):
    """Lets the form show "Referred by <name>". Only the display name is exposed."""
    promoter = _active_promoter(ref)
    if promoter is None:
        return jsonify(error="not_found", message="Unknown or inactive referral link"), 404
    return jsonify(promoter={"public_id": promoter.public_id, "name": promoter.name})


@bp.post("/leads")
@limiter.limit("10 per minute")
def submit_lead():
    body = parse_body(LeadIn)
    if body.website:
        return jsonify(status="received"), 201  # pretend success, store nothing

    db = get_session()
    email = body.email.lower()
    if db.scalar(select(Lead.id).where(Lead.email == email)) is not None:
        # Already registered: keep the original attribution; same answer as a new lead so the
        # form does not reveal who is already in the database.
        return jsonify(status="received"), 201

    # Unknown or archived ref -> the lead is still stored, just without attribution.
    lead = Lead(
        promoter=_active_promoter(body.ref),
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        email=email,
        phone=(body.phone or "").strip() or None,
    )
    db.add(lead)
    try:
        db.flush()  # assigns lead.id for the payload
        event = enqueue_lead(db, lead)
        db.commit()
    except IntegrityError:  # two submissions of the same e-mail at the same instant
        db.rollback()
        return jsonify(status="received"), 201

    settings = current_app.config["NEXUS"]
    try:
        process_event(db, event, get_provider(), settings.outbox_max_attempts)
    except Exception:  # never fail the visitor because of the CRM; the outbox will retry
        log.exception("Immediate CRM sync failed for lead %s", lead.id)
        db.rollback()
    return jsonify(status="received"), 201
