"""Database wiring: one engine per app, one SQLAlchemy session per request.

No Flask-SQLAlchemy on purpose: the engine and session factory are built by hand so every piece is
visible. The session lives in `flask.g` and is closed when the app context ends.
"""

from __future__ import annotations

from datetime import UTC, datetime

from flask import Flask, current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """All timestamps are stored as naive UTC, so SQLite and Postgres behave the same."""
    return datetime.now(UTC).replace(tzinfo=None)


def init_db(app: Flask) -> None:
    url = app.config["NEXUS"].database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    app.extensions["nexus_engine"] = engine
    app.extensions["nexus_sessionmaker"] = sessionmaker(bind=engine, expire_on_commit=False)

    @app.teardown_appcontext
    def _close_session(_exc: BaseException | None) -> None:
        session = g.pop("db", None)
        if session is not None:
            session.close()


def get_session() -> Session:
    if "db" not in g:
        g.db = current_app.extensions["nexus_sessionmaker"]()
    return g.db
