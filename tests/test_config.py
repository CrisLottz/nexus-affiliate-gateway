import pytest
from pydantic import ValidationError

from nexus.config import Settings

KEY = "test-secret-key-0123456789"


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_hubspot_requires_token():
    with pytest.raises(ValidationError, match="HUBSPOT_TOKEN"):
        Settings(_env_file=None, secret_key=KEY, crm_provider="hubspot")


def test_production_rejects_missing_internal_token():
    with pytest.raises(ValidationError, match="INTERNAL_TOKEN"):
        Settings(
            _env_file=None,
            secret_key=KEY,
            nexus_env="production",
            database_url="postgresql://u:p@h/db",
        )


def test_production_rejects_sqlite():
    with pytest.raises(ValidationError, match="SQLite"):
        Settings(_env_file=None, secret_key=KEY, nexus_env="production", internal_token="x")


def test_postgres_url_gets_psycopg_driver():
    s = Settings(_env_file=None, secret_key=KEY, database_url="postgres://u:p@h/db")
    assert s.database_url == "postgresql+psycopg://u:p@h/db"


def test_brand_color_is_validated():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_key=KEY, brand_primary_color="red")
