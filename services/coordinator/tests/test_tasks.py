"""Task submission, routing, status, ownership, cancellation (Phase 2)."""


async def test_create_task_queues(client, auth):
    r = await client.post(
        "/api/v1/tasks",
        headers=auth,
        json={"kind": "chat", "input": {"text": "hello"}, "priority": 7},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "queued"
    # truth-in-advertising: the note must say a worker has to claim it first
    assert "Routed to qwen3-0.6b-q4" in body["note"]
    assert "must claim" in body["note"]


async def test_create_task_rejects_bad_kind(client, auth):
    r = await client.post(
        "/api/v1/tasks", headers=auth, json={"kind": "oracle", "input": {}}
    )
    assert r.status_code == 422


async def test_create_task_rejects_bad_priority(client, auth):
    r = await client.post(
        "/api/v1/tasks", headers=auth, json={"kind": "chat", "input": {}, "priority": 99}
    )
    assert r.status_code == 422


async def test_get_own_task(client, auth):
    r = await client.post(
        "/api/v1/tasks", headers=auth, json={"kind": "research", "input": {"query": "petals status"}}
    )
    task_id = r.json()["id"]
    r = await client.get(f"/api/v1/tasks/{task_id}", headers=auth)
    assert r.status_code == 200
    assert r.json()["kind"] == "research"


async def test_foreign_task_invisible(client, auth, auth2):
    r = await client.post(
        "/api/v1/tasks", headers=auth, json={"kind": "chat", "input": {}}
    )
    task_id = r.json()["id"]
    r = await client.get(f"/api/v1/tasks/{task_id}", headers=auth2)
    assert r.status_code == 404  # not 403: existence is not leaked cross-user


async def test_cancel_task(client, auth):
    r = await client.post(
        "/api/v1/tasks", headers=auth, json={"kind": "chat", "input": {}}
    )
    task_id = r.json()["id"]
    r = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    r = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=auth)
    assert r.status_code == 409  # already cancelled


async def test_list_tasks_scoped_to_owner(client, auth, auth2):
    await client.post("/api/v1/tasks", headers=auth, json={"kind": "chat", "input": {}})
    await client.post("/api/v1/tasks", headers=auth2, json={"kind": "math", "input": {}})
    r = await client.get("/api/v1/tasks", headers=auth)
    assert r.status_code == 200
    kinds = [t["kind"] for t in r.json()]
    assert kinds == ["chat"]  # only own tasks; other user's math task invisible
