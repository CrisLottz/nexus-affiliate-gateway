from datetime import timedelta

from sqlalchemy import select

from nexus.crm.mock import FAIL_PERMANENT, FAIL_RETRYABLE
from nexus.db import get_session
from nexus.models import Lead, OutboxEvent


def _lead(email="maria@example.com", ref=None, **extra):
    body = {"first_name": "María", "last_name": "López", "email": email}
    if ref:
        body["ref"] = ref
    body.update(extra)
    return body


def _promoter(admin_client, name="Ana"):
    return admin_client.post("/api/promoters", {"name": name}).get_json()["promoter"]


def test_promoter_card_hides_archived_and_unknown(admin_client, client):
    p = _promoter(admin_client)
    res = client.get(f"/api/public/promoters/{p['public_id']}")
    assert res.get_json()["promoter"] == {"public_id": p["public_id"], "name": "Ana"}
    admin_client.post(f"/api/promoters/{p['id']}/archive")
    assert client.get(f"/api/public/promoters/{p['public_id']}").status_code == 404
    assert client.get("/api/public/promoters/nope").status_code == 404


def test_lead_is_attributed_and_synced(app, admin_client, client):
    p = _promoter(admin_client)
    res = client.post("/api/public/leads", _lead(ref=p["public_id"], phone="+505 8888-0000"))
    assert res.status_code == 201

    lead = admin_client.get("/api/leads").get_json()["leads"][0]
    assert lead["promoter"]["public_id"] == p["public_id"]
    assert lead["crm_status"] == "synced"
    assert lead["crm_id"].startswith("mock-")
    assert (
        app.extensions["nexus_crm"].contacts[lead["crm_id"]]["promoter_public_id"]
        == (p["public_id"])
    )


def test_unknown_ref_still_stores_the_lead(admin_client, client):
    client.post("/api/public/leads", _lead(ref="deadbeef"))
    lead = admin_client.get("/api/leads").get_json()["leads"][0]
    assert lead["promoter"] is None


def test_duplicate_email_keeps_first_attribution(admin_client, client):
    a, b = _promoter(admin_client, "A"), _promoter(admin_client, "B")
    client.post("/api/public/leads", _lead(ref=a["public_id"]))
    again = client.post("/api/public/leads", _lead(email="MARIA@example.com", ref=b["public_id"]))
    assert again.status_code == 201  # same answer: does not reveal the e-mail exists
    leads = admin_client.get("/api/leads").get_json()["leads"]
    assert len(leads) == 1
    assert leads[0]["promoter"]["name"] == "A"


def test_honeypot_stores_nothing(admin_client, client):
    assert client.post("/api/public/leads", _lead(website="spam.example")).status_code == 201
    assert admin_client.get("/api/leads").get_json()["total"] == 0


def test_validation_errors(client):
    res = client.post("/api/public/leads", {"first_name": "", "email": "nope", "phone": "abc"})
    assert res.status_code == 422
    assert {"first_name", "last_name", "email", "phone"} <= set(res.get_json()["fields"])


def test_crm_outage_keeps_lead_pending_then_flush_delivers(app, admin_client, client):
    client.post("/api/public/leads", _lead(email="x" + FAIL_RETRYABLE))
    lead = admin_client.get("/api/leads").get_json()["leads"][0]
    assert lead["crm_status"] == "pending"  # stored even though the CRM failed

    with app.app_context():
        db = get_session()
        event = db.scalar(select(OutboxEvent))
        assert event.attempts == 1
        assert "simulated" in event.last_error
        # Pretend the CRM recovered and the backoff delay has passed.
        db.get(Lead, event.lead_id).email = "x@recovered.test"
        event.payload = {**event.payload, "email": "x@recovered.test"}
        event.next_attempt_at -= timedelta(hours=1)
        db.commit()

    # Same code path Cloud Scheduler triggers, through the CLI.
    out = app.test_cli_runner().invoke(args=["outbox-flush"])
    assert "synced=1" in out.output
    lead = admin_client.get("/api/leads").get_json()["leads"][0]
    assert lead["crm_status"] == "synced"


def test_internal_flush_without_configured_token_is_disabled(client):
    res = client.client.post("/internal/outbox/flush", headers={"Authorization": "Bearer x"})
    assert res.status_code == 503


def test_internal_flush_requires_token(make_app):
    app = make_app(internal_token="s3cret")
    c = app.test_client()
    assert c.post("/internal/outbox/flush").status_code == 401
    assert c.post(
        "/internal/outbox/flush", headers={"Authorization": "Bearer bad"}
    ).status_code == (401)
    ok = c.post("/internal/outbox/flush", headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200
    assert ok.get_json() == {"processed": 0, "synced": 0, "failed": 0}


def test_permanent_rejection_marks_failed_and_retry_requeues(admin_client, client):
    client.post("/api/public/leads", _lead(email="x" + FAIL_PERMANENT))
    lead = admin_client.get("/api/leads").get_json()["leads"][0]
    assert lead["crm_status"] == "failed"

    res = admin_client.post(f"/api/leads/{lead['id']}/retry")
    assert res.get_json()["lead"]["crm_status"] == "pending"
    assert admin_client.get("/api/leads?crm_status=pending").get_json()["total"] == 1


def test_retry_is_admin_only(admin_client, collab_client, client):
    client.post("/api/public/leads", _lead())
    lead = admin_client.get("/api/leads").get_json()["leads"][0]
    assert collab_client.post(f"/api/leads/{lead['id']}/retry").status_code == 403
    assert admin_client.post(f"/api/leads/{lead['id']}/retry").status_code == 409  # synced


def test_leads_search_and_pagination(admin_client, client):
    for i in range(30):
        client.post("/api/public/leads", _lead(email=f"user{i}@example.com"))
    page2 = admin_client.get("/api/leads?page=2").get_json()
    assert page2["total"] == 30
    assert len(page2["leads"]) == 5
    assert admin_client.get("/api/leads?q=user29").get_json()["total"] == 1
