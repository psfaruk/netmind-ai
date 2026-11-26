"""/api/v1/monitoring — network/service statistics (Phase 1, Tested)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models import ModelRegistry, Node, Task, User
from app.schemas import StatsOut

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/stats", response_model=StatsOut)
async def stats(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    users = await db.scalar(select(func.count()).select_from(User))
    nodes_by_state: dict[str, int] = {}
    for state, count in await db.execute(
        select(Node.state, func.count()).group_by(Node.state)
    ):
        nodes_by_state[state] = count
    tasks_by_status: dict[str, int] = {}
    for status, count in await db.execute(
        select(Task.status, func.count()).group_by(Task.status)
    ):
        tasks_by_status[status] = count
    models_total = await db.scalar(select(func.count()).select_from(ModelRegistry))
    models_available = await db.scalar(
        select(func.count()).select_from(ModelRegistry).where(ModelRegistry.availability.is_(True))
    )
    return StatsOut(
        users=users or 0,
        nodes_by_state=nodes_by_state,
        models_total=models_total or 0,
        models_available=models_available or 0,
        tasks_by_status=tasks_by_status,
    )
