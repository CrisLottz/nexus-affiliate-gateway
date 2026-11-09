"""Nexus Affiliate Gateway — Flask application factory."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from nexus.config import Settings


def create_app(overrides: dict[str, Any] | None = None) -> Flask:
    """Build a Flask app.

    `overrides` lets tests and scripts inject settings without touching the environment.
    `_ratelimit=True` re-enables rate limiting in tests (it is off by default there).
    """
    overrides = dict(overrides or {})
    force_ratelimit = bool(overrides.pop("_ratelimit", False))
    settings = Settings(**overrides)

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.secret_key,
        NEXUS=settings,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.is_production,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        WTF_CSRF_TIME_LIMIT=None,  # the token lives as long as the session
        TESTING=settings.nexus_env == "test",
        RATELIMIT_ENABLED=settings.nexus_env != "test" or force_ratelimit,
    )
    if settings.is_production:
        # Cloud Run sits behind one proxy: trust its X-Forwarded-For / -Proto.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    from nexus.cli import register_cli
    from nexus.db import init_db
    from nexus.extensions import csrf, limiter

    init_db(app)
    csrf.init_app(app)
    limiter.init_app(app)
    register_cli(app)

    from nexus.blueprints import auth, health, promoters, users

    for module in (health, auth, users, promoters):
        app.register_blueprint(module.bp)

    _register_error_handlers(app)
    return app


def _register_error_handlers(app: Flask) -> None:
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def _csrf(exc: CSRFError):
        return jsonify(error="csrf_failed", message=exc.description), 400

    @app.errorhandler(HTTPException)
    def _http(exc: HTTPException):
        # JSON errors for the API; other paths keep Flask's default rendering.
        if not request.path.startswith(("/api/", "/internal/")):
            return exc
        if exc.response is not None:  # aborted with a ready response (validation errors)
            return exc.response
        code = exc.code or 500
        return jsonify(
            error=(exc.name or "error").lower().replace(" ", "_"), message=exc.description
        ), code
