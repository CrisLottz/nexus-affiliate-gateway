"""Login, logout, current user and CSRF token for the SPA."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from flask_wtf.csrf import generate_csrf
from pydantic import BaseModel, Field

from nexus.extensions import limiter
from nexus.security import current_user, login_user, logout_user, verify_login
from nexus.validation import parse_body

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


def _login_limit() -> str:
    return current_app.config["NEXUS"].login_rate_limit


@bp.get("/csrf")
def csrf_token():
    """The SPA calls this once and sends the token back in the X-CSRFToken header."""
    return jsonify(csrf_token=generate_csrf())


@bp.post("/login")
@limiter.limit(_login_limit, methods=["POST"])
def login():
    body = parse_body(LoginIn)
    user = verify_login(body.email, body.password)
    if user is None:
        return jsonify(error="invalid_credentials", message="Wrong e-mail or password"), 401
    login_user(user)
    return jsonify(user=user.to_dict(), csrf_token=generate_csrf())


@bp.post("/logout")
def logout():
    logout_user()
    return jsonify(ok=True)


@bp.get("/me")
def me():
    user = current_user()
    if user is None:
        return jsonify(error="unauthorized"), 401
    return jsonify(user=user.to_dict())
