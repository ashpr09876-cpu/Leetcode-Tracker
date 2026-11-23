from tests.conftest import H, register


def test_register_login_me(client):
    h = register(client)
    assert client.get("/api/v1/auth/me", headers=h).json()["email"] == "a@example.com"
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_duplicate_email_rejected(client):
    register(client)
    r = client.post("/api/v1/auth/register", json={"email": "A@example.com", "password": "password123"})
    assert r.status_code == 409


def test_weak_password_rejected(client):
    assert client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "short"}).status_code == 422


def test_invalid_credentials(client):
    register(client)
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpassword"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"}).status_code == 401


def test_protected_routes_need_token(client):
    for path in ("/api/v1/auth/me", "/api/v1/problems", "/api/v1/dashboard/summary", "/api/v1/goals"):
        assert client.get(path).status_code == 401
    assert client.get("/api/v1/problems", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_rotation_and_reuse_detection(client):
    register(client)
    old = client.cookies.get("refresh_token")
    assert old
    r = client.post("/api/v1/auth/refresh", headers=H)
    assert r.status_code == 200 and r.json()["access_token"]
    new = client.cookies.get("refresh_token")
    assert new and new != old
    url = "/api/v1/auth/refresh"
    client.cookies.clear()
    # replaying the already-rotated token is rejected and revokes the whole family
    assert client.post(url, headers=H, cookies={"refresh_token": old}).status_code == 401
    client.cookies.clear()
    assert client.post(url, headers=H, cookies={"refresh_token": new}).status_code == 401


def test_refresh_requires_csrf_header(client):
    register(client)
    assert client.post("/api/v1/auth/refresh").status_code == 403


def test_logout_revokes_session(client):
    register(client)
    assert client.post("/api/v1/auth/logout", headers=H).status_code == 200
    assert client.post("/api/v1/auth/refresh", headers=H).status_code == 401


def test_password_reset_flow(client, caplog):
    register(client)
    with caplog.at_level("WARNING"):
        assert client.post("/api/v1/auth/forgot-password", json={"email": "a@example.com"}).status_code == 200
    token = [r.message for r in caplog.records if "PASSWORD RESET LINK" in r.message][0].split("token=")[1].strip()
    assert client.post("/api/v1/auth/reset-password", json={"token": "bad", "password": "newpassword1"}).status_code == 400
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "password": "newpassword1"}).status_code == 200
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "password": "another12345"}).status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "newpassword1"}).status_code == 200
    # unknown email gives the same response (no account enumeration)
    assert client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"}).status_code == 200


def test_google_not_configured(client):
    assert client.get("/api/v1/auth/providers").json() == {"google": False}
    assert client.get("/api/v1/auth/google/login", follow_redirects=False).status_code == 503


def test_google_callback_rejects_bad_state(client):
    r = client.get("/api/v1/auth/google/callback?code=x&state=forged", follow_redirects=False)
    assert r.status_code in (302, 307) and "google_failed" in r.headers["location"]


def test_health(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json()["database"] == "ok"
