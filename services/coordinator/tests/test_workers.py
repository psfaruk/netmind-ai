"""/api/v1/workers — claim, submit, expiry/requeue (Phase 2 execution engine)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.db import init_db, seed_model_registry
from app.main import create_app


async def _register_node(client, headers, node_id="node" + "a" * 27):
    r = await client.post(
        "/api/v1/nodes/register",
        headers=headers,
        json={
            "node_id": node_id,
            "platform": "linux",
            "cpu_cores": 4,
            "ram_mb": 4096,
            "runtimes": ["llama.cpp"],
        },
    )
    assert r.status_code == 201, r.text
    return node_id


async def _create_task(client, headers, kind="chat", **overrides):
    payload = {"kind": kind, "input": {"prompt": "hello"}, **overrides}
    r = await client.post("/api/v1/tasks", headers=headers, json=payload)
    assert r.status_code == 202, r.text
    return r.json()


def _claim_payload(node_id, models=None):
    payload = {"node_id": node_id}
    if models is not None:
        payload["models"] = models
    return payload


async def test_routing_stamps_model_on_create(client, auth):
    body = await _create_task(client, auth, kind="chat")
    assert body["model_id"] == "qwen3-0.6b-q4"
    assert body["attempts"] == 0
    assert "Routed to qwen3-0.6b-q4" in body["note"]


async def test_routing_per_kind(client, auth):
    assert (await _create_task(client, auth, kind="coding"))["model_id"] == "qwen3-1.7b-q4"
    assert (await _create_task(client, auth, kind="translation"))["model_id"] == "qwen3-4b-q4"
    assert (await _create_task(client, auth, kind="vision"))["model_id"] is None


async def test_explicit_model_override_wins(client, auth):
    body = await _create_task(client, auth, kind="chat", model_id="phi-4-14b-q4")
    assert body["model_id"] == "phi-4-14b-q4"


async def test_claim_requires_registered_node(client, auth):
    r = await client.post(
        "/api/v1/workers/claim", headers=auth, json=_claim_payload("ghost-node-000000001")
    )
    assert r.status_code == 404
    assert "not registered" in r.json()["detail"]


async def test_claim_and_submit_roundtrip(client, auth):
    node_id = await _register_node(client, auth)
    task = await _create_task(client, auth)

    r = await client.post(
        "/api/v1/workers/claim",
        headers=auth,
        json=_claim_payload(node_id, models=["qwen3-0.6b-q4", "qwen3-1.7b-q4"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["task"]["id"] == task["id"]
    assert body["task"]["model_id"] == "qwen3-0.6b-q4"

    r = await client.get(f"/api/v1/tasks/{task['id']}", headers=auth)
    assert r.json()["status"] == "claimed"
    assert r.json()["claimed_by"] == node_id

    r = await client.post(
        "/api/v1/workers/results",
        headers=auth,
        json={
            "task_id": task["id"],
            "node_id": node_id,
            "status": "completed",
            "result": {"output": "text", "backend": "mock", "tokens": 5, "duration_ms": 12},
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    r = await client.get(f"/api/v1/tasks/{task['id']}", headers=auth)
    final = r.json()
    assert final["status"] == "completed"
    assert final["result"]["backend"] == "mock"
    assert final["note"] == ""  # finished tasks carry no misleading promise


async def test_claim_respects_model_filter(client, auth):
    node_id = await _register_node(client, auth)
    await _create_task(client, auth)  # routed to qwen3-0.6b-q4

    r = await client.post(
        "/api/v1/workers/claim",
        headers=auth,
        json=_claim_payload(node_id, models=["phi-4-14b-q4"]),  # cannot serve it
    )
    assert r.status_code == 200
    assert r.json()["accepted"] is False
    assert r.json()["task"] is None


async def test_claim_priority_then_fifo(client, auth):
    node_id = await _register_node(client, auth)
    low = await _create_task(client, auth, priority=9)
    high = await _create_task(client, auth, priority=1)

    r = await client.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_id))
    assert r.json()["task"]["id"] == high["id"]
    r = await client.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_id))
    assert r.json()["task"]["id"] == low["id"]


async def test_unroutable_task_never_claimed(client, auth):
    node_id = await _register_node(client, auth)
    await _create_task(client, auth, kind="vision")  # model_id stays None
    r = await client.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_id))
    assert r.json()["accepted"] is False


async def test_submit_rejected_for_wrong_node(client, auth):
    node_id = await _register_node(client, auth)
    other = await _register_node(client, auth, "node" + "b" * 27)
    task = await _create_task(client, auth)
    await client.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_id))

    r = await client.post(
        "/api/v1/workers/results",
        headers=auth,
        json={"task_id": task["id"], "node_id": other, "status": "completed", "result": {}},
    )
    assert r.status_code == 409


async def test_submit_rejected_for_unclaimed_task(client, auth):
    node_id = await _register_node(client, auth)
    task = await _create_task(client, auth)
    r = await client.post(
        "/api/v1/workers/results",
        headers=auth,
        json={"task_id": task["id"], "node_id": node_id, "status": "completed", "result": {}},
    )
    assert r.status_code == 409


async def test_worker_endpoints_require_auth(client):
    r = await client.post("/api/v1/workers/claim", json=_claim_payload("node" + "a" * 27))
    assert r.status_code == 401


# ── claim expiry / requeue (volunteer liveness) ───────────────────────
@pytest.fixture
async def expiry_client(tmp_path):
    """claim_ttl_sec = -1 → every claim call requeues previously claimed tasks."""
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'expiry.db'}",
        rate_limit_per_minute=100000,
        claim_ttl_sec=-1.0,
        max_task_attempts=3,
    )
    app = create_app(settings)
    await init_db()
    await seed_model_registry()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _auth_headers(c):
    r = await c.post(
        "/api/v1/auth/register", json={"email": "w@example.com", "password": "password123"}
    )
    assert r.status_code == 201
    r = await c.post("/api/v1/auth/login", json={"email": "w@example.com", "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_expired_claim_requeued_to_next_worker(expiry_client):
    c = expiry_client
    auth = await _auth_headers(c)
    node_a = await _register_node(c, auth, "node" + "a" * 27)
    node_b = await _register_node(c, auth, "node" + "b" * 27)
    task = await _create_task(c, auth)

    r = await c.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_a))
    assert r.json()["accepted"] is True

    # node A vanished; node B's claim call requeues A's expired claim and takes over
    r = await c.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_b))
    body = r.json()
    assert body["requeued"] == 1
    assert body["task"]["id"] == task["id"]
    assert body["task"]["attempts"] == 1

    r = await c.get(f"/api/v1/tasks/{task['id']}", headers=auth)
    assert r.json()["claimed_by"] == node_b


async def test_late_result_after_expiry_rejected(expiry_client):
    c = expiry_client
    auth = await _auth_headers(c)
    node_a = await _register_node(c, auth, "node" + "a" * 27)
    node_b = await _register_node(c, auth, "node" + "b" * 27)
    task = await _create_task(c, auth)
    await c.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_a))
    await c.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_b))

    # node A finally finishes and submits — must not clobber node B's claim
    r = await c.post(
        "/api/v1/workers/results",
        headers=auth,
        json={"task_id": task["id"], "node_id": node_a, "status": "completed", "result": {"late": True}},
    )
    assert r.status_code == 409


async def test_attempts_exhaustion_fails_task(expiry_client):
    c = expiry_client
    auth = await _auth_headers(c)
    node = await _register_node(c, auth)
    task = await _create_task(c, auth)

    # claims 1-3 are taken (attempts 0,1,2) and expire between claim calls
    for expected_attempts in (0, 1, 2):
        r = await c.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node))
        assert r.json()["task"]["attempts"] == expected_attempts
    # the 4th claim call requeues claim 3 → attempts=3 ≥ max → permanent failure
    r = await c.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node))
    assert r.json()["accepted"] is False

    r = await c.get(f"/api/v1/tasks/{task['id']}", headers=auth)
    body = r.json()
    assert body["status"] == "failed"
    assert "max attempts" in body["result"]["error"]


async def test_deadline_exceeded_before_claim(client, auth):
    node_id = await _register_node(client, auth)
    task = await _create_task(client, auth, deadline_sec=10)
    # simulate the deadline having passed by inserting the task in the past
    from datetime import datetime, timedelta, timezone

    from app.db import get_session_factory
    from app.models import Task as TaskModel

    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(TaskModel, task["id"])
        row.deadline_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()

    r = await client.post("/api/v1/workers/claim", headers=auth, json=_claim_payload(node_id))
    assert r.json()["accepted"] is False
    r = await client.get(f"/api/v1/tasks/{task['id']}", headers=auth)
    assert r.json()["status"] == "failed"
    assert "deadline exceeded" in r.json()["result"]["error"]
