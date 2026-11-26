"""Shared dependencies: DB session, current user (JWT or API key), rate limiting."""
import hashlib
import secrets
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.security import decode_access_token
from app.db import get_session_factory
from app.models import ApiKey, User


async def get_db() -> AsyncSession:
    async with get_session_factory()() as session:
        yield session


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Auth via `Authorization: Bearer <jwt>` or `X-API-Key: <key>`."""
    auth = request.headers.get("authorization", "")
    api_key = request.headers.get("x-api-key", "")

    if auth.lower().startswith("bearer "):
        user_id = decode_access_token(
            auth.split(" ", 1)[1].strip(), settings.jwt_secret, settings.jwt_algorithm
        )
        if user_id is None:
            raise HTTPException(status_code=401, detail="invalid or expired token")
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="unknown user")
        return user

    if api_key:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        found = await db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if found is None or found.revoked:
            raise HTTPException(status_code=401, detail="invalid or revoked API key")
        user = await db.get(User, found.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="unknown user")
        from datetime import datetime, timezone

        found.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return user

    raise HTTPException(status_code=401, detail="authentication required")


# ── Rate limiting: in-memory sliding window (single-process; Redis when replicated) ──
_buckets: dict[str, tuple[float, int]] = {}
_WINDOW_SEC = 60.0


def check_rate_limit(key: str, limit: int) -> None:
    now = time.monotonic()
    window_start, count = _buckets.get(key, (now, 0))
    if now - window_start >= _WINDOW_SEC:
        window_start, count = now, 0
    count += 1
    _buckets[key] = (window_start, count)
    if count > limit:
        retry_after = int(_WINDOW_SEC - (now - window_start)) + 1
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


async def rate_limited(
    request: Request,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> User:
    """Dependency: authenticate + enforce per-key rate limit."""
    auth = request.headers.get("authorization", "")
    key = f"u:{user.id}"
    if not auth.lower().startswith("bearer "):
        key = f"k:{user.id}"
    check_rate_limit(key, settings.rate_limit_per_minute)
    return user


def generate_api_key() -> str:
    return "nm_" + secrets.token_urlsafe(32)
