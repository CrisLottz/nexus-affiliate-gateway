def test_anonymous_cannot_list(client):
    assert client.get("/api/promoters").status_code == 401


def test_admin_crud_and_archive(admin_client):
    res = admin_client.post("/api/promoters", {"name": "Ana", "email": "ANA@example.com"})
    assert res.status_code == 201
    p = res.get_json()["promoter"]
    assert len(p["public_id"]) == 8
    assert p["email"] == "ana@example.com"

    renamed = admin_client.patch(f"/api/promoters/{p['id']}", {"name": "Ana María"}).get_json()
    assert renamed["promoter"]["name"] == "Ana María"
    assert renamed["promoter"]["public_id"] == p["public_id"]  # rename keeps the ref

    admin_client.post(f"/api/promoters/{p['id']}/archive")
    assert admin_client.get("/api/promoters").get_json()["promoters"] == []
    all_ = admin_client.get("/api/promoters?include_archived=1").get_json()["promoters"]
    assert all_[0]["archived"] is True

    admin_client.post(f"/api/promoters/{p['id']}/unarchive")
    assert len(admin_client.get("/api/promoters").get_json()["promoters"]) == 1


def test_collaborator_is_read_only(admin_client, collab_client):
    admin_client.post("/api/promoters", {"name": "Luis"})
    assert len(collab_client.get("/api/promoters").get_json()["promoters"]) == 1
    assert collab_client.post("/api/promoters", {"name": "X"}).status_code == 403


def test_there_is_no_delete(admin_client):
    p = admin_client.post("/api/promoters", {"name": "Luis"}).get_json()["promoter"]
    res = admin_client.client.delete(
        f"/api/promoters/{p['id']}", headers={"X-CSRFToken": admin_client.token()}
    )
    assert res.status_code == 405
