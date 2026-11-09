"""Application settings, read from environment variables (and an optional .env file).

Validated with pydantic-settings so a misconfigured deployment fails at start-up with a clear
message instead of misbehaving later. No secret has a default value.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nexus_env: Literal["development", "test", "production"] = "development"
    secret_key: str = Field(min_length=16)
    database_url: str = "sqlite:///nexus.db"

    crm_provider: Literal["mock", "hubspot"] = "mock"
    hubspot_token: str | None = None
    hubspot_promoter_property: str = "nexus_promoter_id"
    crm_timeout_seconds: float = 10.0
    outbox_max_attempts: int = Field(default=8, ge=1)

    internal_token: str | None = None

    brand_name: str = "Nexus"
    brand_primary_color: str = "#4f46e5"
    brand_logo_url: str | None = None

    demo_mode: bool = False
    login_rate_limit: str = "5 per minute"

    @field_validator("brand_primary_color")
    @classmethod
    def _color(cls, v: str) -> str:
        if not HEX_COLOR.match(v):
            raise ValueError("BRAND_PRIMARY_COLOR must look like #4f46e5")
        return v

    @field_validator("database_url")
    @classmethod
    def _db_url(cls, v: str) -> str:
        # Neon / Heroku style URLs start with postgres:// — SQLAlchemy needs an explicit driver.
        if v.startswith("postgres://"):
            v = "postgresql://" + v.removeprefix("postgres://")
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v.removeprefix("postgresql://")
        return v

    @model_validator(mode="after")
    def _cross_checks(self) -> Settings:
        if self.crm_provider == "hubspot" and not self.hubspot_token:
            raise ValueError("CRM_PROVIDER=hubspot requires HUBSPOT_TOKEN")
        if self.nexus_env == "production":
            if not self.internal_token:
                raise ValueError("INTERNAL_TOKEN is required in production")
            if self.database_url.startswith("sqlite"):
                raise ValueError(
                    "SQLite is not allowed in production (Cloud Run disk is ephemeral)"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.nexus_env == "production"
