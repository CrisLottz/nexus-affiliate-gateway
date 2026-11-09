"""Endpoints for machines (Cloud Scheduler), protected by a shared bearer token.

Cloud Run scales to zero, so there is no background worker: the scheduler calls
POST /internal/outbox/flush every few minutes to retry pending CRM syncs.
"""

from __future__ import annotations

import hmac

from flask import Blueprint, current_app, jsonify, request

from nexus.crm import get_provider
from nexus.db import get_session
from nexus.extensions import csrf
from nexus.outbox import flush

bp = Blueprint("internal", __name__, url_prefix="/internal")
csrf.exempt(bp)  # no browser involved; the bearer token is the protection


@bp.before_request
def _require_token():
    expected = current_app.config["NEXUS"].internal_token
    if not expected:
        return jsonify(error="not_configured", message="INTERNAL_TOKEN is not set"), 503
    supplied = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied.encode(), expected.encode()):  # constant-time compare
        return jsonify(error="unauthorized"), 401
    return None


@bp.post("/outbox/flush")
def outbox_flush():
    settings = current_app.config["NEXUS"]
    result = flush(get_session(), get_provider(), settings.outbox_max_attempts)
    return jsonify(result.to_dict())
