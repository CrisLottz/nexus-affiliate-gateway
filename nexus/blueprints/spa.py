"""Serve the compiled React app and its runtime config from the same origin as the API.

Vite builds into nexus/static/app. Any path that is not an API route and not a real file gets
index.html, so client-side routes like /join or /leads work on reload.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, send_from_directory

bp = Blueprint("spa", __name__)

DIST = Path(__file__).resolve().parent.parent / "static" / "app"


@bp.get("/api/config")
def config():
    """White-label settings for the SPA. Only public values: never return a secret here."""
    s = current_app.config["NEXUS"]
    demo: dict = {"enabled": s.demo_mode}
    if s.demo_mode:
        from nexus.demo import DEMO_ADMIN_EMAIL, DEMO_PASSWORD

        demo.update(email=DEMO_ADMIN_EMAIL, password=DEMO_PASSWORD)
    return jsonify(
        brand_name=s.brand_name,
        brand_primary_color=s.brand_primary_color,
        brand_logo_url=s.brand_logo_url,
        crm_provider=s.crm_provider,
        demo=demo,
    )


@bp.get("/", defaults={"path": ""})
@bp.get("/<path:path>")
def index(path: str):
    if path.startswith(("api/", "internal/")):
        abort(404)
    if not (DIST / "index.html").exists():
        return (
            "Frontend not built. Run: cd frontend && npm ci && npm run build "
            "(or use the Vite dev server on :5173).",
            503,
        )
    if path and (DIST / path).is_file():
        response = send_from_directory(DIST, path)
        if path.startswith("assets/"):  # Vite fingerprints these files: cache them forever
            response.cache_control.max_age = 31536000
            response.cache_control.immutable = True
            response.cache_control.public = True
        return response
    response = send_from_directory(DIST, "index.html")
    response.cache_control.no_cache = True  # always pick up a new deploy
    return response
