"""Outbox pattern: the lead and its "send to CRM" event are written in the same transaction.

If the CRM is down, nothing is lost — the event stays `pending` and is retried with exponential
backoff by `flush()` (called by Cloud Scheduler through /internal/outbox/flush, or by the CLI).
Delivery is at-least-once, so CRM adapters must upsert (see CRMProvider.upsert_lead).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from nexus.crm import CRMError, CRMProvider, LeadPayload
from nexus.db import utcnow
from nexus.models import CrmStatus, Lead, OutboxEvent, OutboxStatus

BASE_DELAY = timedelta(seconds=30)
MAX_DELAY = timedelta(hours=6)


def backoff(attempts: int) -> timedelta:
    """30 s, 1 min, 2 min, 4 min... capped at 6 h."""
    exponent = min(max(attempts - 1, 0), 20)  # bounded: 2**49 seconds overflows timedelta
    return min(BASE_DELAY * (2**exponent), MAX_DELAY)


def enqueue_lead(db: Session, lead: Lead) -> OutboxEvent:
    """Add the outbox event for a new lead. The caller commits both rows together."""
    promoter = lead.promoter
    payload = LeadPayload(
        lead_id=lead.id,
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        phone=lead.phone,
        promoter_public_id=promoter.public_id if promoter else None,
        promoter_name=promoter.name if promoter else None,
    )
    event = OutboxEvent(lead=lead, kind="lead.created", payload=payload.to_dict())
    db.add(event)
    return event


def process_event(
    db: Session, event: OutboxEvent, provider: CRMProvider, max_attempts: int
) -> bool:
    """Try to deliver one event and record the outcome. Returns True on success. Commits."""
    lead = event.lead
    event.attempts += 1
    try:
        crm_id = provider.upsert_lead(LeadPayload.from_dict(event.payload))
    except CRMError as exc:
        event.last_error = str(exc)[:2000]
        if not exc.retryable or event.attempts >= max_attempts:
            event.status = OutboxStatus.DEAD
            event.processed_at = utcnow()
            lead.crm_status = CrmStatus.FAILED
        else:
            event.next_attempt_at = utcnow() + backoff(event.attempts)
        db.commit()
        return False

    event.status = OutboxStatus.DONE
    event.processed_at = utcnow()
    event.last_error = None
    lead.crm_status = CrmStatus.SYNCED
    lead.crm_id = crm_id
    db.commit()
    return True


@dataclass
class FlushResult:
    processed: int = 0
    synced: int = 0
    failed: int = 0
    lead_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"processed": self.processed, "synced": self.synced, "failed": self.failed}


def flush(db: Session, provider: CRMProvider, max_attempts: int, limit: int = 50) -> FlushResult:
    """Deliver due events. On Postgres, `FOR UPDATE SKIP LOCKED` lets two overlapping scheduler
    runs share the work instead of sending the same event twice. SQLite ignores the clause."""
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.status == OutboxStatus.PENDING, OutboxEvent.next_attempt_at <= utcnow())
        .order_by(OutboxEvent.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = FlushResult()
    for event in db.scalars(stmt).all():
        result.processed += 1
        result.lead_ids.append(event.lead_id)
        if process_event(db, event, provider, max_attempts):
            result.synced += 1
        else:
            result.failed += 1
    return result


def requeue_lead(db: Session, lead: Lead) -> OutboxEvent:
    """Give a failed lead a fresh set of attempts (admin action after fixing the cause)."""
    event = db.scalars(
        select(OutboxEvent).where(OutboxEvent.lead_id == lead.id).order_by(OutboxEvent.id.desc())
    ).first()
    if event is None:
        event = enqueue_lead(db, lead)
    event.status = OutboxStatus.PENDING
    event.attempts = 0
    event.next_attempt_at = utcnow()
    event.processed_at = None
    lead.crm_status = CrmStatus.PENDING
    db.commit()
    return event
