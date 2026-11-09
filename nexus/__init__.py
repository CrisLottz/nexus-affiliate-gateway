"""Nexus Affiliate Gateway — Flask application factory."""

from __future__ import annotations

from typing import Any

from flask import Flask

from nexus.config import Settings


def create_app(overrides: dict[str, Any] | None = None) -> Flask:
    """Build a Flask app.

    `overrides` lets tests and scripts inject settings without touching the environment.
    """
    settings = Settings(**(overrides or {}))

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.secret_key,
        NEXUS=settings,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.is_production,
        TESTING=settings.nexus_env == "test",
    )

    from nexus.blueprints import health

    app.register_blueprint(health.bp)
    return app
