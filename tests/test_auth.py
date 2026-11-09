from tests.conftest import ApiClient


def test_login_logout_me(admin_client):
    me = admin_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["role"] == "admin"

    assert admin_client.post("/api/auth/logout").status_code == 200
    assert admin_client.get("/api/auth/me").status_code == 401


def test_wrong_password_and_unknown_email_look_the_same(app, admin_client):
    c = ApiClient(app)
    wrong = c.login("admin@example.com", "nope")
    unknown = c.login("ghost@example.com", "nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()


def test_writes_without_csrf_token_are_rejected(app):
    res = app.test_client().post("/api/auth/login", json={"email": "a@b.co", "password": "x"})
    assert res.status_code == 400
    assert res.get_json()["error"] == "csrf_failed"


def test_login_is_rate_limited(make_app):
    app = make_app(_ratelimit=True, login_rate_limit="3 per minute")
    c = ApiClient(app)
    codes = [c.login("ghost@example.com", "x").status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_password_change_revokes_existing_sessions(app, admin_client, collab_client):
    users = admin_client.get("/api/users").get_json()["users"]
    collab = next(u for u in users if u["role"] == "collaborator")
    res = admin_client.patch(f"/api/users/{collab['id']}", {"password": "a-brand-new-password"})
    assert res.status_code == 200
    assert collab_client.get("/api/auth/me").status_code == 401


def test_deactivated_user_cannot_log_in(app, admin_client, collab_client):
    users = admin_client.get("/api/users").get_json()["users"]
    collab = next(u for u in users if u["role"] == "collaborator")
    admin_client.patch(f"/api/users/{collab['id']}", {"is_active": False})
    assert collab_client.get("/api/auth/me").status_code == 401
    assert ApiClient(app).login("collab@example.com").status_code == 401


def test_admin_cannot_demote_self(admin_client):
    me = admin_client.get("/api/auth/me").get_json()["user"]
    res = admin_client.patch(f"/api/users/{me['id']}", {"role": "collaborator"})
    assert res.status_code == 403


def test_users_endpoint_is_admin_only(collab_client):
    assert collab_client.get("/api/users").status_code == 403


def test_create_user_validates_and_rejects_duplicates(admin_client):
    bad = admin_client.post("/api/users", {"email": "x", "name": "", "password": "short"})
    assert bad.status_code == 422
    assert set(bad.get_json()["fields"]) == {"email", "name", "password"}

    body = {"email": "New@Example.com", "name": "New", "password": "long-enough-pw"}
    created = admin_client.post("/api/users", body)
    assert created.status_code == 201
    assert created.get_json()["user"]["email"] == "new@example.com"
    assert admin_client.post("/api/users", body).status_code == 409
