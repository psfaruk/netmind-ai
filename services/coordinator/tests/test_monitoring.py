"""Monitoring stats and documented 501 placeholders."""


async def test_stats_counts(client, auth):
    await client.post(
        "/api/v1/nodes/register",
        headers=auth,
        json={
            "node_id": "cd" * 32,
            "platform": "android",
            "cpu_cores": 8,
            "ram_mb": 6144,
            "runtimes": ["onnx"],
            "region": "BD",
        },
    )
    await client.post("/api/v1/tasks", headers=auth, json={"kind": "chat", "input": {}})

    r = await client.get("/api/v1/monitoring/stats", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["users"] == 1
    assert body["nodes_by_state"] == {"registered": 1}
    assert body["models_total"] == 10
    assert body["models_available"] == 0  # honesty: nothing deployed yet
    assert body["tasks_by_status"] == {"queued": 1}


async def test_stats_requires_auth(client):
    r = await client.get("/api/v1/monitoring/stats")
    assert r.status_code == 401


async def test_placeholder_groups_return_501_with_phase(client, auth):
    for path, phase in [
        ("/api/v1/agents", 4),
        ("/api/v1/knowledge", 3),
        ("/api/v1/research", 4),
        ("/api/v1/compute", 5),
        ("/api/v1/feedback", 2),
    ]:
        r = await client.get(path, headers=auth)
        assert r.status_code == 501
        body = r.json()
        assert body["phase"] == phase
        assert "Planned for Phase" in body["detail"]
