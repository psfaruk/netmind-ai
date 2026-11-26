"""Typed environment-driven configuration (no hardcoded secrets in production)."""
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-insecure-secret-change-in-prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETMIND_", env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "NETMIND Coordinator"
    version: str = "0.3.0"

    # Dev profile: SQLite needs no server (works from Termux). Prod: postgresql+asyncpg://...
    database_url: str = "sqlite+aiosqlite:///./netmind_dev.db"

    jwt_secret: str = _DEV_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    rate_limit_per_minute: int = 60
    cors_origins: str = ""  # comma-separated; empty = no CORS middleware

    # ── Phase 2 execution engine ──
    claim_ttl_sec: float = 120.0  # a claim older than this is requeued
    max_task_attempts: int = 3   # after N claims expiring, the task fails permanently

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def enforce_production_safety(self) -> None:
        """Charter rule: never hardcode API secrets. Refuse to boot prod with the dev secret."""
        if self.environment == "prod" and self.jwt_secret == _DEV_SECRET:
            raise RuntimeError(
                "NETMIND_JWT_SECRET must be set to a real secret when NETMIND_ENVIRONMENT=prod"
            )
