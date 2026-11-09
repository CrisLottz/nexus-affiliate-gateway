"""User management (admins only)."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError

from nexus.db import get_session
from nexus.models import Role, User
from nexus.security import current_user, hash_password, login_required
from nexus.validation import parse_body

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.before_request
def _read_only_in_demo():
    # The public demo shares one admin account: nobody may lock the others out.
    if current_app.config["NEXUS"].demo_mode and request.method != "GET":
        return jsonify(error="demo_mode", message="User management is read-only in the demo"), 403
    return None


class UserIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=200)
    role: Role = Role.COLLABORATOR


class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=200)


@bp.get("")
@login_required(Role.ADMIN)
def list_users():
    users = get_session().query(User).order_by(User.created_at).all()
    return jsonify(users=[u.to_dict() for u in users])


@bp.post("")
@login_required(Role.ADMIN)
def create_user():
    body = parse_body(UserIn)
    db = get_session()
    user = User(
        email=body.email.lower(),
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return jsonify(error="conflict", message="A user with that e-mail already exists"), 409
    return jsonify(user=user.to_dict()), 201


@bp.patch("/<int:user_id>")
@login_required(Role.ADMIN)
def update_user(user_id: int):
    body = parse_body(UserPatch)
    db = get_session()
    user = db.get(User, user_id) or abort(404)
    me = current_user()
    if user.id == me.id and (body.role == Role.COLLABORATOR or body.is_active is False):
        return jsonify(error="forbidden", message="You cannot demote or deactivate yourself"), 403

    if body.name is not None:
        user.name = body.name.strip()
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        if not body.is_active:
            user.session_version += 1
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
        user.session_version += 1  # log out every device
    db.commit()
    return jsonify(user=user.to_dict())
