from datetime import timedelta

from nexus.crm.base import CRMError
from nexus.crm.mock import MockProvider
from nexus.db import utcnow
from nexus.models import CrmStatus, Lead, OutboxEvent, OutboxStatus, Promoter
from nexus.outbox import backoff, enqueue_lead, flush, process_event


class FlakyProvider:
    """Fails `failures` times, then works."""

    name = "flaky"

    def __init__(self, failures: int, retryable: bool = True):
        self.failures = failures
        self.retryable = retryable
        self.calls = 0

    def upsert_lead(self, payload):
        self.calls += 1
        if self.calls <= self.failures:
            raise CRMError("boom", retryable=self.retryable)
        return "crm-1"


def _make_lead(db, email="a@example.com"):
    promoter = Promoter(name="Ana")
    lead = Lead(promoter=promoter, first_name="A", last_name="B", email=email)
    db.add(lead)
    db.flush()
    event = enqueue_lead(db, lead)
    db.commit()
    return lead, event


def test_backoff_grows_and_is_capped():
    assert backoff(1) == timedelta(seconds=30)
    assert backoff(2) == timedelta(minutes=1)
    assert backoff(3) == timedelta(minutes=2)
    assert backoff(50) == timedelta(hours=6)


def test_payload_snapshot_survives_promoter_rename(db):
    lead, event = _make_lead(db)
    lead.promoter.name = "Renamed"
    db.commit()
    assert event.payload["promoter_name"] == "Ana"
    assert event.payload["promoter_public_id"] == lead.promoter.public_id


def test_retry_until_success(db):
    lead, event = _make_lead(db)
    provider = FlakyProvider(failures=2)

    assert process_event(db, event, provider, max_attempts=5) is False
    assert event.status == OutboxStatus.PENDING
    assert event.next_attempt_at > utcnow()

    # Not due yet: flush skips it.
    assert flush(db, provider, 5).processed == 0

    event.next_attempt_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert flush(db, provider, 5).failed == 1

    event.next_attempt_at = utcnow() - timedelta(seconds=1)
    db.commit()
    result = flush(db, provider, 5)
    assert result.synced == 1
    assert event.status == OutboxStatus.DONE
    assert lead.crm_status == CrmStatus.SYNCED
    assert lead.crm_id == "crm-1"
    assert event.attempts == 3


def test_gives_up_after_max_attempts(db):
    lead, event = _make_lead(db)
    provider = FlakyProvider(failures=99)
    for _ in range(3):
        event.next_attempt_at = utcnow() - timedelta(seconds=1)
        db.commit()
        flush(db, provider, max_attempts=3)
    assert event.status == OutboxStatus.DEAD
    assert lead.crm_status == CrmStatus.FAILED
    assert flush(db, provider, max_attempts=3).processed == 0


def test_non_retryable_error_is_dead_at_once(db):
    lead, event = _make_lead(db)
    process_event(db, event, FlakyProvider(failures=1, retryable=False), max_attempts=8)
    assert event.status == OutboxStatus.DEAD
    assert lead.crm_status == CrmStatus.FAILED


def test_mock_provider_is_idempotent(db):
    lead, event = _make_lead(db)
    mock = MockProvider()
    process_event(db, event, mock, 3)
    first = lead.crm_id
    process_event(db, event, mock, 3)  # redelivery
    assert lead.crm_id == first
    assert len(mock.contacts) == 1
    assert db.query(OutboxEvent).count() == 1
