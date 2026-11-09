"""HubSpot adapter against mocked HTTP (the `responses` library). No real account needed."""

import pytest
import requests
import responses

from nexus.crm.base import CRMError, LeadPayload
from nexus.crm.hubspot import API, HubSpotProvider

CONTACTS = f"{API}/crm/v3/objects/contacts"

PAYLOAD = LeadPayload(
    lead_id=1,
    email="maria@example.com",
    first_name="María",
    last_name="López",
    phone=None,
    promoter_public_id="a1b2c3d4",
    promoter_name="Ana",
)


@pytest.fixture
def hub():
    return HubSpotProvider("pat-test", "nexus_promoter_id", timeout=1)


@responses.activate
def test_create_contact(hub):
    responses.post(CONTACTS, json={"id": "101"}, status=201)
    assert hub.upsert_lead(PAYLOAD) == "101"
    sent = responses.calls[0].request
    assert sent.headers["Authorization"] == "Bearer pat-test"
    body = responses.calls[0].request.body.decode()
    assert '"nexus_promoter_id": "a1b2c3d4"' in body
    assert "phone" not in body


@responses.activate
def test_existing_contact_is_updated(hub):
    responses.post(
        CONTACTS,
        json={"message": "Contact already exists. Existing ID: 555"},
        status=409,
    )
    responses.patch(f"{CONTACTS}/555", json={"id": "555"}, status=200)
    assert hub.upsert_lead(PAYLOAD) == "555"


@pytest.mark.parametrize(
    ("status", "retryable"), [(429, True), (500, True), (401, True), (400, False)]
)
@responses.activate
def test_error_classification(hub, status, retryable):
    responses.post(CONTACTS, json={"message": "x"}, status=status)
    with pytest.raises(CRMError) as exc:
        hub.upsert_lead(PAYLOAD)
    assert exc.value.retryable is retryable


@responses.activate
def test_network_error_is_retryable(hub):
    responses.post(CONTACTS, body=requests.ConnectionError("down"))
    with pytest.raises(CRMError) as exc:
        hub.upsert_lead(PAYLOAD)
    assert exc.value.retryable is True
