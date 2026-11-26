"""Rate limiting: token bucket per user, 429 + Retry-After."""
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.db import init_db, seed_model_registry
from tests.conftest import PWD, make_settings, register_and_login


async def test_rate_limit_returns_429(tmp_path):
    settings = make_settings(tmp_path, rate_limit_per_minute=2)
    app = create_app(settings)
    await init_db()
    await seed_model_registry()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await register_and_login(client, "rl@example.com")

        # limit=2/min on rate-limited endpoints (tasks):
        r1 = await client.post("/api/v1/tasks", headers=headers, json={"kind": "chat", "input": {}})
        r2 = await client.post("/api/v1/tasks", headers=headers, json={"kind": "chat", "input": {}})
        r3 = await client.post("/api/v1/tasks", headers=headers, json={"kind": "chat", "input": {}})

        assert r1.status_code == 202
        assert r2.status_code == 202
        assert r3.status_code == 429
        assert r3.headers.get("retry-after")
        assert r3.json()["detail"] == "rate limit exceeded"
