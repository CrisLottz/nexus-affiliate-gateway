"""Leaderboard and counters — SQL aggregates over Nexus's own database, never CRM queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, func, or_, select

from nexus.db import get_session
from nexus.models import Lead, Promoter
from nexus.security import login_required

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

PERIODS = ("today", "week", "month", "all")


def period_start(period: str, tz: ZoneInfo, now: datetime | None = None) -> datetime | None:
    """Start of the period in the viewer's time zone, returned as naive UTC (storage format).

    "Today" in Managua starts at 06:00 UTC, not at midnight UTC — that is why the zone matters.
    Weeks start on Monday.
    """
    if period == "all":
        return None
    local_now = (now or datetime.now(UTC)).astimezone(tz)
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start -= timedelta(days=start.weekday())
    elif period == "month":
        start = start.replace(day=1)
    return start.astimezone(UTC).replace(tzinfo=None)


def _args() -> tuple[str, ZoneInfo]:
    period = request.args.get("period", "month")
    if period not in PERIODS:
        period = "month"
    try:
        tz = ZoneInfo(request.args.get("tz", "UTC"))
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    return period, tz


@bp.get("/leaderboard")
@login_required()
def leaderboard():
    period, tz = _args()
    start = period_start(period, tz)
    db = get_session()

    # LEFT JOIN with the date filter inside the ON clause, so promoters with zero leads in the
    # period still appear (with 0) instead of disappearing from the ranking.
    on = Lead.promoter_id == Promoter.id
    if start is not None:
        on = and_(on, Lead.created_at >= start)
    count = func.count(Lead.id).label("leads")
    rows = db.execute(
        select(Promoter, count)
        .outerjoin(Lead, on)
        .group_by(Promoter.id)
        # Archived promoters only show up if they still have leads in the period.
        .having(or_(Promoter.archived_at.is_(None), count > 0))
        .order_by(count.desc(), Promoter.name)
    ).all()

    ranking, rank, previous = [], 0, None
    for i, (promoter, leads) in enumerate(rows, start=1):
        if leads != previous:  # ties share a rank: 1, 2, 2, 4
            rank, previous = i, leads
        ranking.append({"rank": rank, "promoter": promoter.to_dict(), "leads": leads})
    return jsonify(period=period, tz=tz.key, since=_iso(start), leaderboard=ranking)


@bp.get("/summary")
@login_required()
def summary():
    period, tz = _args()
    start = period_start(period, tz)
    stmt = select(Lead.crm_status, func.count(Lead.id)).group_by(Lead.crm_status)
    unattributed = select(func.count(Lead.id)).where(Lead.promoter_id.is_(None))
    if start is not None:
        stmt = stmt.where(Lead.created_at >= start)
        unattributed = unattributed.where(Lead.created_at >= start)
    db = get_session()
    by_status = dict(db.execute(stmt).all())
    return jsonify(
        period=period,
        tz=tz.key,
        since=_iso(start),
        total=sum(by_status.values()),
        synced=by_status.get("synced", 0),
        pending=by_status.get("pending", 0),
        failed=by_status.get("failed", 0),
        unattributed=db.scalar(unattributed),
        active_promoters=db.scalar(
            select(func.count(Promoter.id)).where(Promoter.archived_at.is_(None))
        ),
    )


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None
