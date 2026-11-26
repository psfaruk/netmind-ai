"""System probes: /health and /ready."""


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "NETMIND Coordinator"
    assert "x-request-id" in r.headers


async def test_ready(client):
    r = await client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "database": "ok"}
