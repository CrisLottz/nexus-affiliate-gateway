"""In-memory CRM for the demo and the tests. No account needed."""

from __future__ import annotations

import hashlib

from nexus.crm.base import CRMError, LeadPayload

# Any lead whose e-mail ends with one of these domains simulates a CRM failure, so the retry
# flow can be seen in the demo without breaking anything real.
FAIL_RETRYABLE = "@crm-down.example.com"
FAIL_PERMANENT = "@crm-reject.example.com"


class MockProvider:
    name = "mock"

    def __init__(self) -> None:
        self.contacts: dict[str, dict] = {}

    def upsert_lead(self, payload: LeadPayload) -> str:
        if payload.email.endswith(FAIL_RETRYABLE):
            raise CRMError("Mock CRM is down (simulated)", retryable=True)
        if payload.email.endswith(FAIL_PERMANENT):
            raise CRMError("Mock CRM rejected the contact (simulated)", retryable=False)
        crm_id = "mock-" + hashlib.sha256(payload.email.encode()).hexdigest()[:12]
        self.contacts[crm_id] = payload.to_dict()  # same e-mail -> same id: idempotent
        return crm_id
