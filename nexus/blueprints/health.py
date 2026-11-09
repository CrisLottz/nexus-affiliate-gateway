from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():
    """Liveness probe for Cloud Run and docker compose. Does not touch the database."""
    return jsonify(status="ok")
