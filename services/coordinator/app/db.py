"""Async database plumbing. Coordinator holds no authoritative in-memory state (ADR-011)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


class Base(DeclarativeBase):
    pass


def configure_engine(database_url: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("database engine not configured — call configure_engine() first")
    return _engine


def get_session_factory() -> async_sessionmaker:
    if _session_factory is None:
        raise RuntimeError("database engine not configured — call configure_engine() first")
    return _session_factory


async def init_db() -> None:
    """Bootstrap schema (ADR-003: create_all now, Alembic mandatory before Phase 5)."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_model_registry() -> None:
    """Seed registry metadata (honest: availability=false everywhere — no runtime yet)."""
    from app.models import ModelRegistry
    from app.registry_seed import CATALOG

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.scalar(select(func.count()).select_from(ModelRegistry))
        if existing:
            return
        for row in CATALOG:
            session.add(ModelRegistry(**row))
        await session.commit()
