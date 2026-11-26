"""Node registration, listing, heartbeats."""

NODE = {
    "node_id": "ab" * 32,  # 64 hex chars standing in for an Ed25519 public key
    "platform": "linux",
    "cpu_cores": 8,
    "ram_mb": 16384,
    "gpu": False,
    "runtimes": ["llama.cpp"],
    "region": "BD",
    "contribution_limits": {"max_cpu_pct": 50, "max_ram_mb": 4096},
}


async def test_register_node(client, auth):
    r = await client.post("/api/v1/nodes/register", headers=auth, json=NODE)
    assert r.status_code == 201
    body = r.json()
    assert body["node_id"] == NODE["node_id"]
    assert body["platform"] == "linux"
    assert body["state"] == "registered"


async def test_node_listing_hides_private_fields(client, auth):
    await client.post("/api/v1/nodes/register", headers=auth, json=NODE)
    r = await client.get("/api/v1/nodes", headers=auth)
    assert r.status_code == 200
    listing = r.json()
    assert len(listing) == 1
    # privacy: public listing must not expose owner/contribution limits
    assert "contribution_limits" not in listing[0]
    assert "owner_user_id" not in listing[0]


async def test_reregister_updates_capabilities(client, auth):
    await client.post("/api/v1/nodes/register", headers=auth, json=NODE)
    updated = dict(NODE, gpu=True, ram_mb=32768)
    r = await client.post("/api/v1/nodes/register", headers=auth, json=updated)
    assert r.status_code == 201
    r = await client.get("/api/v1/nodes", headers=auth)
    assert r.json()[0]["gpu"] is True
    assert r.json()[0]["ram_mb"] == 32768


async def test_heartbeat_unknown_node_404(client, auth):
    r = await client.post(
        "/api/v1/nodes/ffff/heartbeat", headers=auth, json={"cpu_load_pct": 5}
    )
    assert r.status_code == 404


async def test_heartbeat_activates_node(client, auth):
    await client.post("/api/v1/nodes/register", headers=auth, json=NODE)
    r = await client.post(
        f"/api/v1/nodes/{NODE['node_id']}/heartbeat",
        headers=auth,
        json={"cpu_load_pct": 12, "free_ram_mb": 8000, "active_tasks": 0},
    )
    assert r.status_code == 200
    assert r.json()["state"] == "active"
    assert r.json()["heartbeat_interval_sec"] == 30

    r = await client.get("/api/v1/nodes", headers=auth)
    assert r.json()[0]["state"] == "active"
    assert r.json()[0]["last_heartbeat_at"] is not None


async def test_register_requires_auth(client):
    r = await client.post("/api/v1/nodes/register", json=NODE)
    assert r.status_code == 401
