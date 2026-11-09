"""Demo mode: fictional sample data so anyone can try Nexus without accounts.

Every name and e-mail here is invented (example.com domains). Seeding is idempotent: it does
nothing if the demo admin already exists.
"""

from __future__ import annotations

import random
import unicodedata
from datetime import timedelta

from sqlalchemy.orm import Session

from nexus.crm.mock import FAIL_PERMANENT, FAIL_RETRYABLE
from nexus.db import utcnow
from nexus.models import CrmStatus, Lead, OutboxEvent, OutboxStatus, Promoter, Role, User
from nexus.outbox import enqueue_lead
from nexus.security import hash_password

DEMO_ADMIN_EMAIL = "admin@demo.example.com"
DEMO_PASSWORD = "nexus-demo-2026"  # noqa: S105 — public on purpose, shown on the login page

PROMOTERS = [
    "Valeria Ruiz",
    "Diego Morales",
    "Camila Torres",
    "Mateo Herrera",
    "Lucía Castro",
    "Andrés Navarro",
]
FIRST = [
    "Sofía",
    "Javier",
    "Isabella",
    "Carlos",
    "Mariana",
    "Luis",
    "Daniela",
    "José",
    "Paula",
    "Miguel",
    "Gabriela",
    "Ricardo",
    "Elena",
    "Fernando",
    "Natalia",
    "Tomás",
]
LAST = [
    "García",
    "Martínez",
    "López",
    "Hernández",
    "González",
    "Pérez",
    "Sánchez",
    "Ramírez",
    "Flores",
    "Rivera",
    "Gómez",
    "Díaz",
    "Vargas",
    "Mendoza",
]


def seed_demo(db: Session, *, leads: int = 140, seed: int = 7) -> bool:
    """Create the demo users, promoters and leads. Returns False if already seeded."""
    if db.query(User).filter_by(email=DEMO_ADMIN_EMAIL).first():
        return False

    rng = random.Random(seed)  # noqa: S311 — fake data, not security
    db.add_all(
        [
            User(
                email=DEMO_ADMIN_EMAIL,
                name="Demo Admin",
                role=Role.ADMIN,
                password_hash=hash_password(DEMO_PASSWORD),
            ),
            User(
                email="viewer@demo.example.com",
                name="Demo Viewer",
                role=Role.COLLABORATOR,
                password_hash=hash_password(DEMO_PASSWORD),
            ),
        ]
    )
    promoters = [Promoter(name=n) for n in PROMOTERS]
    promoters[-1].archived_at = utcnow() - timedelta(days=20)
    db.add_all(promoters)
    weights = [9, 7, 5, 4, 2, 3]

    now = utcnow()
    for i in range(leads):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        promoter = rng.choices(promoters + [None], weights=weights + [2])[0]
        # Most leads are recent, a long tail goes back ~3 months.
        age = timedelta(hours=rng.expovariate(1 / 400))
        if promoter is promoters[-1]:
            age += timedelta(days=21)  # the archived promoter only has old leads
        domain = "example.com"
        roll = rng.random()
        if roll < 0.04:
            domain = FAIL_PERMANENT.lstrip("@")
        elif roll < 0.10:
            domain = FAIL_RETRYABLE.lstrip("@")
        lead = Lead(
            promoter=promoter,
            first_name=first,
            last_name=last,
            email=f"{_ascii(first)}.{_ascii(last)}.{i}@{domain}".lower(),
            phone=f"+1 555 {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            created_at=now - age,
        )
        db.add(lead)
        db.flush()
        event = enqueue_lead(db, lead)
        event.created_at = lead.created_at
        _settle(lead, event, domain)
    db.commit()
    return True


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _settle(lead: Lead, event: OutboxEvent, domain: str) -> None:
    """Give each sample lead a realistic sync state without calling any CRM."""
    if domain == FAIL_PERMANENT.lstrip("@"):
        lead.crm_status = CrmStatus.FAILED
        event.status, event.attempts = OutboxStatus.DEAD, 1
        event.last_error = "Mock CRM rejected the contact (simulated)"
    elif domain == FAIL_RETRYABLE.lstrip("@"):
        event.attempts = 2
        event.last_error = "Mock CRM is down (simulated)"
        event.next_attempt_at = utcnow() + timedelta(minutes=1)
    else:
        lead.crm_status = CrmStatus.SYNCED
        lead.crm_id = f"mock-demo-{lead.id}"
        event.status, event.attempts, event.processed_at = OutboxStatus.DONE, 1, lead.created_at
