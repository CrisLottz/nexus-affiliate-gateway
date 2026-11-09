"""Pick the CRM adapter from the settings. One instance per app."""

from __future__ import annotations

from flask import Flask, current_app

from nexus.config import Settings
from nexus.crm.base import CRMError, CRMProvider, LeadPayload

__all__ = ["CRMError", "CRMProvider", "LeadPayload", "build_provider", "get_provider"]


def build_provider(settings: Settings) -> CRMProvider:
    if settings.crm_provider == "hubspot":
        from nexus.crm.hubspot import HubSpotProvider

        assert settings.hubspot_token  # guaranteed by Settings validation  # noqa: S101
        return HubSpotProvider(
            settings.hubspot_token,
            settings.hubspot_promoter_property,
            settings.crm_timeout_seconds,
        )
    from nexus.crm.mock import MockProvider

    return MockProvider()


def init_crm(app: Flask) -> None:
    app.extensions["nexus_crm"] = build_provider(app.config["NEXUS"])


def get_provider() -> CRMProvider:
    return current_app.extensions["nexus_crm"]
