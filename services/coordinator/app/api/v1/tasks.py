"""/api/v1/tasks — task submission, status, cancellation, routing (Phase 2, Tested).

Phase 1 persisted and queued tasks; the Phase 2 execution engine now routes
every task to a registry model and hands it to workers via /workers/claim.
Whether real inference runs still depends on a worker being online with that
model — status labels and notes stay truthful (charter rule #3)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, rate_limited
from app.models import Task, User
from app.routing import route_task
from app.schemas import TaskCreateIn, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _note(task: Task) -> str:
    if task.status == "queued":
        return (
            f"Routed to {task.model_id or 'no model (unroutable kind)'}; queued. "
            "A worker advertising that model must claim it before any inference runs."
        )
    return ""


def _to_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        kind=task.kind,
        status=task.status,
        priority=task.priority,
        model_id=task.model_id,
        claimed_by=task.claimed_by,
        attempts=task.attempts,
        deadline_at=task.deadline_at,
        result=task.result,
        created_at=task.created_at,
        note=_note(task),
    )


@router.post("", response_model=TaskOut, status_code=202)
async def create_task(
    payload: TaskCreateIn,
    user: User = Depends(rate_limited),
    db: AsyncSession = Depends(get_db),
):
    deadline_at = None
    if payload.deadline_sec is not None:
        deadline_at = datetime.now(timezone.utc) + timedelta(seconds=payload.deadline_sec)
    model_id = payload.model_id or route_task(payload.kind)
    task = Task(
        user_id=user.id,
        kind=payload.kind,
        input=payload.input,
        priority=payload.priority,
        status="queued",
        model_id=model_id,
        deadline_at=deadline_at,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _to_out(task)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    user: User = Depends(rate_limited),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="task not found")
    return _to_out(task)


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(rate_limited),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    rows = await db.scalars(
        select(Task).where(Task.user_id == user.id).order_by(Task.created_at.desc()).limit(limit).offset(offset)
    )
    return [_to_out(t) for t in rows]


@router.post("/{task_id}/cancel", response_model=TaskOut)
async def cancel_task(
    task_id: str,
    user: User = Depends(rate_limited),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"task already {task.status}")
    task.status = "cancelled"
    await db.commit()
    await db.refresh(task)
    return _to_out(task)
