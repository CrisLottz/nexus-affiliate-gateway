from nexus.blueprints import spa
from nexus.db import get_session
from nexus.demo import DEMO_ADMIN_EMAIL, DEMO_PASSWORD, seed_demo
from nexus.models import Lead, Promoter
from tests.conftest import ApiClient


def test_config_exposes_only_public_values(make_app):
    app = make_app(brand_name="Acme Leads", brand_primary_color="#ff0066", hubspot_token="pat-x")
    data = app.test_client().get("/api/config").get_json()
    assert data["brand_name"] == "Acme Leads"
    assert data["brand_primary_color"] == "#ff0066"
    assert data["demo"] == {"enabled": False}
    assert "pat-x" not in str(data)


def test_unknown_api_route_is_json_404_not_the_spa(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.is_json


def test_spa_fallback_serves_index_for_client_routes(client, tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)")
    monkeypatch.setattr(spa, "DIST", tmp_path)

    page = client.get("/join?ref=abc")
    assert page.status_code == 200
    assert b"root" in page.data
    assert page.headers["Cache-Control"] == "no-cache"

    asset = client.get("/assets/app-123.js")
    assert "immutable" in asset.headers["Cache-Control"]


def test_missing_build_returns_helpful_503(client, tmp_path, monkeypatch):
    monkeypatch.setattr(spa, "DIST", tmp_path)
    res = client.get("/")
    assert res.status_code == 503
    assert b"npm run build" in res.data


def test_seed_demo_is_idempotent_and_login_works(make_app):
    app = make_app(demo_mode=True)
    with app.app_context():
        db = get_session()
        assert seed_demo(db) is True
        assert seed_demo(db) is False
        assert db.query(Lead).count() == 140
        assert db.query(Promoter).filter(Promoter.archived_at.isnot(None)).count() == 1

    cfg = app.test_client().get("/api/config").get_json()
    assert cfg["demo"] == {"enabled": True, "email": DEMO_ADMIN_EMAIL, "password": DEMO_PASSWORD}

    c = ApiClient(app)
    assert c.login(DEMO_ADMIN_EMAIL, DEMO_PASSWORD).status_code == 200
    summary = c.get("/api/dashboard/summary?period=all").get_json()
    assert summary["total"] == 140
    assert summary["failed"] > 0 and summary["pending"] > 0 and summary["synced"] > 0


def test_user_management_is_read_only_in_demo(make_app):
    app = make_app(demo_mode=True)
    with app.app_context():
        seed_demo(get_session(), leads=5)
    c = ApiClient(app)
    c.login(DEMO_ADMIN_EMAIL, DEMO_PASSWORD)
    assert c.get("/api/users").status_code == 200
    res = c.patch("/api/users/1", {"password": "hijacked-password"})
    assert res.status_code == 403
    assert res.get_json()["error"] == "demo_mode"
