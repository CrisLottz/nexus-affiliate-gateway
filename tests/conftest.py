from __future__ import annotations

import os

import pytest
from alembic import command

from nexus import create_app
from nexus.config import Settings
from nexus.db import get_session
from nexus.migrate import alembic_config, upgrade
from nexus.models import Role, User
from nexus.security import hash_password

PASSWORD = "correct-horse-battery"


SECRET = "test-secret-key-0123456789"


@pytest.fixture
def make_app(tmp_path):
    """Build an app on a fresh database migrated with Alembic (the real migrations).

    SQLite file per test by default. With TEST_DATABASE_URL (CI sets a Postgres service), the
    schema is dropped and re-migrated before each test instead.
    """
    external = os.environ.get("TEST_DATABASE_URL")
    state = {"reset": False}

    def _make(**overrides):
        if external:
            url = Settings(_env_file=None, secret_key=SECRET, database_url=external).database_url
            if not state["reset"]:
                command.downgrade(alembic_config(url), "base")
                state["reset"] = True
        else:
            url = f"sqlite:///{tmp_path / 'test.db'}"
        upgrade(url)
        settings = {
            "nexus_env": "test",
            "secret_key": SECRET,
            "database_url": url,
        }
        settings.update(overrides)
        return create_app(settings)

    return _make


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def db(app):
    with app.app_context():
        yield get_session()


class ApiClient:
    """Test client that fetches the CSRF token once and sends it on every write."""

    def __init__(self, app):
        self.client = app.test_client()
        self._token = None

    def token(self) -> str:
        if self._token is None:
            self._token = self.client.get("/api/auth/csrf").get_json()["csrf_token"]
        return self._token

    def get(self, url, **kw):
        return self.client.get(url, **kw)

    def _write(self, method, url, json=None, **kw):
        headers = {"X-CSRFToken": self.token(), **kw.pop("headers", {})}
        return getattr(self.client, method)(url, json=json, headers=headers, **kw)

    def post(self, url, json=None, **kw):
        return self._write("post", url, json, **kw)

    def patch(self, url, json=None, **kw):
        return self._write("patch", url, json, **kw)

    def login(self, email: str, password: str = PASSWORD):
        res = self.post("/api/auth/login", {"email": email, "password": password})
        if res.status_code == 200:
            self._token = res.get_json()["csrf_token"]
        return res


@pytest.fixture
def client(app):
    return ApiClient(app)


def add_user(app, email: str, role: Role) -> None:
    with app.app_context():
        db = get_session()
        db.add(
            User(
                email=email,
                name=email.split("@")[0],
                role=role,
                password_hash=hash_password(PASSWORD),
            )
        )
        db.commit()


@pytest.fixture
def admin_client(app):
    add_user(app, "admin@example.com", Role.ADMIN)
    c = ApiClient(app)
    assert c.login("admin@example.com").status_code == 200
    return c


@pytest.fixture
def collab_client(app):
    add_user(app, "collab@example.com", Role.COLLABORATOR)
    c = ApiClient(app)
    assert c.login("collab@example.com").status_code == 200
    return c
