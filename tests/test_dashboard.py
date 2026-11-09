from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from nexus.blueprints.dashboard import period_start
from nexus.db import get_session, utcnow
from nexus.models import Lead, Promoter


def test_period_start_respects_time_zone():
    managua = ZoneInfo("America/Managua")  # UTC-6, no DST
    now = datetime(2026, 11, 11, 3, 0, tzinfo=UTC)  # Tue 10/11 21:00 in Managua
    assert period_start("today", managua, now) == datetime(2026, 11, 10, 6, 0)
    assert period_start("week", managua, now) == datetime(2026, 11, 9, 6, 0)  # Monday
    assert period_start("month", managua, now) == datetime(2026, 11, 1, 6, 0)
    assert period_start("all", managua, now) is None


def _seed(app):
    with app.app_context():
        db = get_session()
        ana, luis, zoe = Promoter(name="Ana"), Promoter(name="Luis"), Promoter(name="Zoe")
        old = Promoter(name="Old", archived_at=utcnow())
        db.add_all([ana, luis, zoe, old])
        now = utcnow()
        rows = [
            (ana, now),
            (ana, now),
            (luis, now),
            (luis, now),
            (luis, now - timedelta(days=400)),
            (old, now - timedelta(days=400)),
            (None, now),
        ]
        for i, (p, ts) in enumerate(rows):
            db.add(
                Lead(promoter=p, first_name="F", last_name="L", email=f"{i}@x.co", created_at=ts)
            )
        db.commit()


def test_leaderboard_today_includes_zero_and_ties(app, admin_client):
    _seed(app)
    data = admin_client.get("/api/dashboard/leaderboard?period=today").get_json()
    board = [(r["rank"], r["promoter"]["name"], r["leads"]) for r in data["leaderboard"]]
    assert board == [(1, "Ana", 2), (1, "Luis", 2), (3, "Zoe", 0)]  # archived "Old" hidden


def test_leaderboard_all_time_shows_archived_with_leads(app, admin_client):
    _seed(app)
    data = admin_client.get("/api/dashboard/leaderboard?period=all").get_json()
    board = [(r["promoter"]["name"], r["leads"]) for r in data["leaderboard"]]
    assert board == [("Luis", 3), ("Ana", 2), ("Old", 1), ("Zoe", 0)]


def test_summary(app, collab_client):
    _seed(app)
    s = collab_client.get("/api/dashboard/summary?period=all&tz=America/Managua").get_json()
    assert s["total"] == 7
    assert s["pending"] == 7
    assert s["unattributed"] == 1
    assert s["active_promoters"] == 3
    assert s["tz"] == "America/Managua"


def test_bad_params_fall_back(admin_client):
    data = admin_client.get("/api/dashboard/summary?period=year&tz=Mars/Base").get_json()
    assert data["period"] == "month"
    assert data["tz"] == "UTC"
