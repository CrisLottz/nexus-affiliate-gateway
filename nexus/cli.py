"""Command-line tasks: `flask --app nexus <command>`."""

from __future__ import annotations

import click
from flask import Flask

from nexus.db import get_session
from nexus.migrate import upgrade
from nexus.models import Role, User
from nexus.security import hash_password


def register_cli(app: Flask) -> None:
    @app.cli.command("migrate")
    def migrate_cmd() -> None:
        """Apply every pending Alembic migration."""
        upgrade(app.config["NEXUS"].database_url)
        click.echo("Database is up to date.")

    @app.cli.command("create-user")
    @click.option("--email", required=True)
    @click.option("--name", required=True)
    @click.option("--role", type=click.Choice([r.value for r in Role]), default=Role.ADMIN.value)
    @click.password_option()
    def create_user_cmd(email: str, name: str, role: str, password: str) -> None:
        """Create a user (the first admin is created this way)."""
        if len(password) < 10:
            raise click.BadParameter("Use at least 10 characters", param_hint="password")
        db = get_session()
        if db.query(User).filter_by(email=email.lower()).first():
            raise click.ClickException(f"{email} already exists")
        db.add(
            User(email=email.lower(), name=name, role=role, password_hash=hash_password(password))
        )
        db.commit()
        click.echo(f"Created {role} {email}")

    @app.cli.command("outbox-flush")
    def outbox_flush_cmd() -> None:
        """Retry pending CRM syncs once (what Cloud Scheduler triggers in production)."""
        from nexus.crm import get_provider
        from nexus.outbox import flush

        result = flush(get_session(), get_provider(), app.config["NEXUS"].outbox_max_attempts)
        click.echo(f"processed={result.processed} synced={result.synced} failed={result.failed}")
