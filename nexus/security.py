"""Authentication helpers: password hashing, the current user and role checks.

Sessions are Flask's signed, HttpOnly, SameSite=Lax cookies holding only the user id and a
`session_version`. Bumping `User.session_version` (password change, deactivation) invalidates
every cookie issued before, which gives server-side revocation without a session table.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import abort, g, session
from werkzeug.security import check_password_hash, generate_password_hash

from nexus.db import get_session
from nexus.models import Role, User

# Hash checked when the e-mail does not exist, so a failed login takes the same time either way
# (no user enumeration through response timing).
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def hash_password(password: str) -> str:
    return generate_password_hash(password)  # scrypt by default in Werkzeug 3


def verify_login(email: str, password: str) -> User | None:
    user = get_session().query(User).filter_by(email=email.strip().lower()).one_or_none()
    if user is None:
        check_password_hash(_DUMMY_HASH, password)
        return None
    if not check_password_hash(user.password_hash, password) or not user.is_active:
        return None
    return user


def login_user(user: User) -> None:
    session.clear()  # new session on login: prevents session fixation
    session["uid"] = user.id
    session["sv"] = user.session_version
    session.permanent = True


def logout_user() -> None:
    session.clear()


def current_user() -> User | None:
    if "user" in g:
        return g.user
    user = None
    uid = session.get("uid")
    if uid is not None:
        user = get_session().get(User, uid)
        if user is None or not user.is_active or user.session_version != session.get("sv"):
            session.clear()
            user = None
    g.user = user
    return user


def login_required(role: Role | None = None) -> Callable:
    """Require a logged-in user; with `role=Role.ADMIN`, require an admin."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = current_user()
            if user is None:
                abort(401)
            if role is not None and user.role != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
