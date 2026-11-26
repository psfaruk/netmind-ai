"""/api/v1/models — model registry metadata (Phase 1, Tested).

Registry rows are metadata only. `availability=false` until a verified runtime
exists on a registered node (charter rule #4 — never assume a model is available)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models import ModelRegistry, User
from app.schemas import ModelCreateIn, ModelOut

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelOut])
async def list_models(
    capability: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = await db.scalars(select(ModelRegistry).order_by(ModelRegistry.id))
    out = [ModelOut.model_validate(r, from_attributes=True) for r in rows]
    if capability:
        out = [m for m in out if capability in m.capabilities]
    return out


@router.get("/{model_id}", response_model=ModelOut)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(ModelRegistry, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model not found")
    return ModelOut.model_validate(row, from_attributes=True)


@router.post("", response_model=ModelOut, status_code=201)
async def add_model(
    payload: ModelCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin-only: add a registry record (license + memory metadata required)."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin privileges required")
    if await db.get(ModelRegistry, payload.id) is not None:
        raise HTTPException(status_code=409, detail="model id already registered")
    row = ModelRegistry(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ModelOut.model_validate(row, from_attributes=True)
