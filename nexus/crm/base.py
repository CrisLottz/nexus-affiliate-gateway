"""The CRM boundary. The rest of the app only knows this interface, never a vendor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LeadPayload:
    """What Nexus sends to a CRM. Built from the lead when the outbox event is created, so a
    later rename of the promoter does not change what was sent."""

    lead_id: int
    email: str
    first_name: str
    last_name: str
    phone: str | None
    promoter_public_id: str | None
    promoter_name: str | None

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> LeadPayload:
        return cls(**data)


class CRMError(Exception):
    """A failed sync. `retryable=False` means retrying will never help (e.g. a 400 response)."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class CRMProvider(Protocol):
    name: str

    def upsert_lead(self, payload: LeadPayload) -> str:
        """Create or update the contact and return its id in the CRM. Must be idempotent:
        the outbox may deliver the same lead more than once (at-least-once delivery)."""
        ...
