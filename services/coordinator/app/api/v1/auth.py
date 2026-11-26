"""/api/v1/auth — registration, JWT login, API keys (Phase 1, Tested)."""
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import generate_api_key, get_current_user, get_db, rate_limited
from app.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import ApiKey, User
from app.schemas import (
    ApiKeyCreateIn,
    ApiKeyCreatedOut,
    ApiKeyOut,
    LoginIn,
    RegisterIn,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    """Create a user. The first registered user becomes admin (owner bootstrap)."""
    exists = await db.scalar(select(func.count()).select_from(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=409, detail="email already registered")
    user_count = await db.scalar(select(func.count()).select_from(User))
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        is_admin=(user_count == 0),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(
    payload: LoginIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    token = create_access_token(
        user.id, settings.jwt_secret, settings.jwt_algorithm, settings.jwt_expire_minutes
    )
    return TokenOut(access_token=token, expires_in=settings.jwt_expire_minutes * 60)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/api-keys", response_model=ApiKeyCreatedOut, status_code=201)
async def create_api_key(
    payload: ApiKeyCreateIn,
    user: User = Depends(rate_limited),
    db: AsyncSession = Depends(get_db),
):
    """Create an API key. The plaintext key is returned exactly once."""
    plaintext = generate_api_key()
    key = ApiKey(
        user_id=user.id,
        key_hash=hashlib.sha256(plaintext.encode()).hexdigest(),
        label=payload.label,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return ApiKeyCreatedOut(id=key.id, label=key.label, key=plaintext)


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    user: User = Depends(rate_limited), db: AsyncSession = Depends(get_db)
):
    keys = await db.scalars(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at)
    )
    return [
        ApiKeyOut(id=k.id, label=k.label, revoked=k.revoked, created_at=k.created_at) for k in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    user: User = Depends(rate_limited),
    db: AsyncSession = Depends(get_db),
):
    key = await db.get(ApiKey, key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="api key not found")
    key.revoked = True
    await db.commit()
