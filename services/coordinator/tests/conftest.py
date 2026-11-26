"""Shared fixtures: app + async client on a per-test SQLite database."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.db import init_db, seed_model_registry
from app.main import create_app

PWD = "password123"


def make_settings(tmp_path, **overrides) -> Settings:
    defaults = {
        "environment": "test",
        "database_url": f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        "rate_limit_per_minute": 100000,
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
async def client(tmp_path):
    app = create_app(make_settings(tmp_path))
    await init_db()
    await seed_model_registry()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register_and_login(client, email, password=PWD):
    r = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert r.status_code in (201, 409), r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def auth(client):
    return await register_and_login(client, "owner@example.com")


@pytest.fixture
async def auth2(client):
    return await register_and_login(client, "other@example.com")
