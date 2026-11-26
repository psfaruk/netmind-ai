"""Auth: registration, login, /me, API keys, revocation."""
from tests.conftest import PWD, register_and_login


async def test_register_creates_user(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "user1@example.com", "password": PWD, "display_name": "User One"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "user1@example.com"
    assert body["is_admin"] is True  # bootstrap rule: first registered user in a fresh DB becomes admin
    assert "password" not in body and "password_hash" not in body


async def test_register_duplicate_rejected(client):
    await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": PWD})
    r = await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": PWD})
    assert r.status_code == 409


async def test_register_short_password_rejected(client):
    r = await client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 422


async def test_login_wrong_password_rejected(client):
    await client.post("/api/v1/auth/register", json={"email": "lp@example.com", "password": PWD})
    r = await client.post("/api/v1/auth/login", json={"email": "lp@example.com", "password": "wrong-pass"})
    assert r.status_code == 401


async def test_login_returns_token(client):
    await register_and_login(client, "tk@example.com")
    r = await client.post("/api/v1/auth/login", json={"email": "tk@example.com", "password": PWD})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["expires_in"] > 0


async def test_me_requires_auth(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_with_token(client):
    headers = await register_and_login(client, "me@example.com")
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


async def test_api_key_roundtrip(client):
    headers = await register_and_login(client, "key@example.com")
    r = await client.post("/api/v1/auth/api-keys", headers=headers, json={"label": "ci"})
    assert r.status_code == 201
    plaintext = r.json()["key"]
    assert plaintext.startswith("nm_")

    r = await client.get("/api/v1/auth/me", headers={"X-API-Key": plaintext})
    assert r.status_code == 200

    r = await client.get("/api/v1/auth/api-keys", headers=headers)
    assert r.status_code == 200
    assert r.json()[0]["label"] == "ci"
    assert "key" not in r.json()[0]  # plaintext never shown again


async def test_revoked_api_key_rejected(client):
    headers = await register_and_login(client, "rev@example.com")
    r = await client.post("/api/v1/auth/api-keys", headers=headers, json={"label": "tmp"})
    key_id, plaintext = r.json()["id"], r.json()["key"]

    r = await client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=headers)
    assert r.status_code == 204

    r = await client.get("/api/v1/auth/me", headers={"X-API-Key": plaintext})
    assert r.status_code == 401
