"""API schemas (Pydantic v2) — request validation and response shapes."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

TaskKind = Literal["chat", "research", "coding", "math", "translation", "vision"]


# ── Auth ──────────────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str | None
    is_admin: bool
    created_at: datetime


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ApiKeyCreateIn(BaseModel):
    label: str | None = Field(default=None, max_length=200)


class ApiKeyCreatedOut(BaseModel):
    id: str
    label: str | None
    key: str  # plaintext shown exactly once


class ApiKeyOut(BaseModel):
    id: str
    label: str | None
    revoked: bool
    created_at: datetime


# ── Nodes ────────────────────────────────────────────────────────────────
class NodeRegisterIn(BaseModel):
    node_id: str = Field(min_length=16, max_length=128, description="Ed25519 public key (hex)")
    platform: Literal["android", "windows", "linux", "macos", "server"]
    cpu_cores: int = Field(ge=1, le=256)
    ram_mb: int = Field(ge=128)
    gpu: bool = False
    runtimes: list[str] = Field(default_factory=list)
    region: str | None = Field(default=None, max_length=64)
    contribution_limits: dict[str, Any] = Field(default_factory=dict)


class NodePublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    platform: str
    cpu_cores: int
    ram_mb: int
    gpu: bool
    runtimes: list[str]
    region: str | None
    state: str
    last_heartbeat_at: datetime | None


class HeartbeatIn(BaseModel):
    cpu_load_pct: int = Field(ge=0, le=100, default=0)
    free_ram_mb: int = Field(ge=0, default=0)
    active_tasks: int = Field(ge=0, default=0)


class HeartbeatOut(BaseModel):
    node_id: str
    state: str
    heartbeat_interval_sec: int = 30


# ── Models ───────────────────────────────────────────────────────────────
class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    license: str
    capabilities: list[str]
    languages: list[str]
    context_length: int
    quantization: str
    memory_requirement_mb: int
    runtimes: list[str]
    deployment_location: str
    availability: bool


class ModelCreateIn(BaseModel):
    id: str = Field(min_length=2, max_length=128)
    name: str = Field(min_length=2, max_length=200)
    version: str = "stable"
    license: str = Field(min_length=2, max_length=64)
    capabilities: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    context_length: int = 0
    quantization: str = "Q4_K_M"
    memory_requirement_mb: int = Field(ge=0, default=0)
    runtimes: list[str] = Field(default_factory=list)
    deployment_location: str = "none"
    availability: bool = False


# ── Tasks ────────────────────────────────────────────────────────────────
class TaskCreateIn(BaseModel):
    kind: TaskKind
    input: dict[str, Any]
    priority: int = Field(ge=1, le=9, default=5)
    deadline_sec: int | None = Field(default=None, ge=10)
    model_id: str | None = Field(
        default=None, max_length=128,
        description="Explicit model override; default = automatic routing by kind",
    )


class TaskOut(BaseModel):
    id: str
    kind: str
    status: str
    priority: int
    model_id: str | None
    claimed_by: str | None
    attempts: int
    deadline_at: datetime | None
    result: dict[str, Any] | None
    created_at: datetime
    note: str


# ── Workers (Phase 2 execution engine) ──
class ClaimIn(BaseModel):
    node_id: str = Field(min_length=8, max_length=128)
    models: list[str] = Field(
        default_factory=list,
        description="Model ids this worker can serve; empty = claim any routable task",
    )


class ClaimedTaskOut(BaseModel):
    id: str
    kind: str
    model_id: str | None
    input: dict[str, Any]
    priority: int
    attempts: int
    deadline_at: datetime | None


class ClaimOut(BaseModel):
    accepted: bool
    task: ClaimedTaskOut | None
    requeued: int = Field(description="expired claims requeued by this call")


class ResultIn(BaseModel):
    task_id: str
    node_id: str = Field(min_length=8, max_length=128)
    status: Literal["completed", "failed"]
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=2000)


class ResultOut(BaseModel):
    task_id: str
    status: str


# ── Monitoring ──
class StatsOut(BaseModel):
    users: int
    nodes_by_state: dict[str, int]
    models_total: int
    models_available: int
    tasks_by_status: dict[str, int]
