"""SQLAlchemy models — Phase 1 subset of docs/DATABASE_SCHEMA.md (UUID as 36-char string,
JSON columns for portability between SQLite-dev and PostgreSQL-prod profiles)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(String(200))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(200))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    node_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    platform: Mapped[str] = mapped_column(String(32))
    cpu_cores: Mapped[int] = mapped_column(Integer)
    ram_mb: Mapped[int] = mapped_column(Integer)
    gpu: Mapped[bool] = mapped_column(Boolean, default=False)
    runtimes: Mapped[list] = mapped_column(JSON, default=list)
    region: Mapped[str | None] = mapped_column(String(64))
    contribution_limits: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(16), default="registered")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NodeHeartbeat(Base):
    __tablename__ = "node_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    cpu_load_pct: Mapped[int] = mapped_column(Integer, default=0)
    free_ram_mb: Mapped[int] = mapped_column(Integer, default=0)
    active_tasks: Mapped[int] = mapped_column(Integer, default=0)


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(64), default="stable")
    license: Mapped[str] = mapped_column(String(64))
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    context_length: Mapped[int] = mapped_column(Integer, default=0)
    quantization: Mapped[str] = mapped_column(String(32), default="Q4_K_M")
    memory_requirement_mb: Mapped[int] = mapped_column(Integer, default=0)
    runtimes: Mapped[list] = mapped_column(JSON, default=list)
    benchmark_refs: Mapped[dict] = mapped_column(JSON, default=dict)
    deployment_location: Mapped[str] = mapped_column(String(200), default="none")
    availability: Mapped[bool] = mapped_column(Boolean, default=False)


class Task(Base):
    """Task record. Phase 2 state machine:
    queued -> claimed -> completed | failed | cancelled, with claim expiry + requeue."""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # ── Phase 2 execution columns ──
    model_id: Mapped[str | None] = mapped_column(String(128), index=True)  # routing decision
    claimed_by: Mapped[str | None] = mapped_column(String(128))  # node_id of claiming worker
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
