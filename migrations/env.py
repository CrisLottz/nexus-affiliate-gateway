"""Alembic environment.

The URL comes from (1) `config.attributes["database_url"]` when migrations run from code (tests,
`nexus.migrate.upgrade`) or (2) the app settings (DATABASE_URL) when run from the alembic CLI.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import nexus.models  # noqa: F401  (registers the tables on Base.metadata)
from nexus.db import Base

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    url = config.attributes.get("database_url")
    if url:
        return url
    from nexus.config import Settings

    return Settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _url()
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),  # SQLite needs batch mode for ALTERs
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
