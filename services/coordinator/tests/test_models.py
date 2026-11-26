"""Model registry endpoints."""


async def test_list_models_seeded(client, auth):
    r = await client.get("/api/v1/models", headers=auth)
    assert r.status_code == 200
    models = r.json()
    assert len(models) == 10
    ids = {m["id"] for m in models}
    assert "qwen3-4b-q4" in ids and "bge-m3" in ids and "banglaspeech2text" in ids
    # honesty rule: nothing is claimed available before a runtime exists
    assert all(m["availability"] is False for m in models)


async def test_get_model_detail(client, auth):
    r = await client.get("/api/v1/models/qwen3-4b-q4", headers=auth)
    assert r.status_code == 200
    assert r.json()["license"] == "Apache-2.0"
    assert r.json()["memory_requirement_mb"] == 2600


async def test_get_model_404(client, auth):
    r = await client.get("/api/v1/models/does-not-exist", headers=auth)
    assert r.status_code == 404


async def test_models_require_auth(client):
    r = await client.get("/api/v1/models")
    assert r.status_code == 401


async def test_admin_can_add_model(client, auth):
    payload = {
        "id": "test-model-q4",
        "name": "Test Model",
        "license": "Apache-2.0",
        "capabilities": ["chat"],
        "memory_requirement_mb": 500,
    }
    r = await client.post("/api/v1/models", headers=auth, json=payload)
    assert r.status_code == 201
    assert r.json()["availability"] is False

    r = await client.get("/api/v1/models/test-model-q4", headers=auth)
    assert r.status_code == 200


async def test_non_admin_cannot_add_model(client, auth, auth2):
    payload = {
        "id": "evil-model",
        "name": "Evil",
        "license": "MIT",
        "capabilities": ["chat"],
    }
    r = await client.post("/api/v1/models", headers=auth2, json=payload)
    assert r.status_code == 403
