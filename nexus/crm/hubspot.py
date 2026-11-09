"""HubSpot adapter: each lead becomes a Contact, upserted by e-mail.

Auth uses a private-app token (Settings → Integrations → Private apps) with the scopes
`crm.objects.contacts.read` and `crm.objects.contacts.write`. The promoter id goes into one
custom contact property (default `nexus_promoter_id`) that must exist in the HubSpot account —
see docs/hubspot.md.
"""

from __future__ import annotations

import re

import requests

from nexus.crm.base import CRMError, LeadPayload

API = "https://api.hubapi.com"
_EXISTING_ID = re.compile(r"Existing ID:\s*(\d+)")


class HubSpotProvider:
    name = "hubspot"

    def __init__(self, token: str, promoter_property: str, timeout: float = 10.0) -> None:
        self.promoter_property = promoter_property
        self.timeout = timeout
        self.http = requests.Session()
        self.http.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def _properties(self, p: LeadPayload) -> dict:
        props = {"email": p.email, "firstname": p.first_name, "lastname": p.last_name}
        if p.phone:
            props["phone"] = p.phone
        if p.promoter_public_id:
            props[self.promoter_property] = p.promoter_public_id
        return props

    def _request(self, method: str, path: str, body: dict) -> requests.Response:
        try:
            return self.http.request(method, API + path, json=body, timeout=self.timeout)
        except requests.RequestException as exc:  # network error, timeout: try again later
            raise CRMError(f"HubSpot unreachable: {exc}") from exc

    def upsert_lead(self, payload: LeadPayload) -> str:
        body = {"properties": self._properties(payload)}
        res = self._request("POST", "/crm/v3/objects/contacts", body)
        if res.status_code == 201:
            return str(res.json()["id"])
        if res.status_code == 409:
            # The contact already exists (an earlier attempt succeeded, or the person was
            # already in the CRM): update it instead. This makes redelivery idempotent.
            match = _EXISTING_ID.search(res.text)
            if not match:
                raise CRMError(f"HubSpot 409 without an existing id: {res.text[:300]}")
            contact_id = match.group(1)
            upd = self._request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", body)
            if upd.ok:
                return contact_id
            res = upd
        raise _error_for(res)


def _error_for(res: requests.Response) -> CRMError:
    detail = f"HubSpot {res.status_code}: {res.text[:300]}"
    # 429 (rate limit) and 5xx are transient. 401/403 are a configuration problem that a
    # fixed token will solve, so they are retried too. Any other 4xx is a bad request:
    # sending the same data again will never work.
    retryable = res.status_code in (401, 403, 429) or res.status_code >= 500
    return CRMError(detail, retryable=retryable)
