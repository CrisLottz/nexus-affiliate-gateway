"""Domain model.

- A Promoter is identified by an immutable `public_id` (the `ref` in the referral link), never by
  name, so renaming does not break attribution. Promoters are archived, never deleted.
- A Lead is written locally first. Its CRM sync is tracked by an OutboxEvent (outbox pattern).
"""

from __future__ import annotations

import secrets
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexus.db import Base, utcnow


class Role(StrEnum):
    ADMIN = "admin"
    COLLABORATOR = "collaborator"


class CrmStatus(StrEnum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"  # gave up after the max number of attempts


class OutboxStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    DEAD = "dead"


def new_public_id() -> str:
    return secrets.token_hex(4)  # 8 hex chars, ~4.3 billion values


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=Role.COLLABORATOR)
    is_active: Mapped[bool] = mapped_column(default=True)
    # Bumped on password change / deactivation: invalidates every existing session cookie.
    session_version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() + "Z",
        }


class Promoter(Base):
    __tablename__ = "promoters"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(16), unique=True, default=new_public_id)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    archived_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    leads: Mapped[list[Lead]] = relationship(back_populates="promoter")

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "public_id": self.public_id,
            "name": self.name,
            "email": self.email,
            "archived": self.is_archived,
            "created_at": self.created_at.isoformat() + "Z",
        }


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_promoter_created", "promoter_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    promoter_id: Mapped[int | None] = mapped_column(ForeignKey("promoters.id"))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    crm_status: Mapped[str] = mapped_column(String(20), default=CrmStatus.PENDING)
    crm_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    promoter: Mapped[Promoter | None] = relationship(back_populates="leads")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "promoter": self.promoter.to_dict() if self.promoter else None,
            "crm_status": self.crm_status,
            "crm_id": self.crm_id,
            "created_at": self.created_at.isoformat() + "Z",
        }


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_status_next", "status", "next_attempt_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    kind: Mapped[str] = mapped_column(String(40), default="lead.created")
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default=OutboxStatus.PENDING)
    attempts: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(default=None)

    lead: Mapped[Lead] = relationship()
