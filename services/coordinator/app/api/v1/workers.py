"""/api/v1/workers — task claiming and result submission (Phase 2, Tested).

Execution model (docs/PHASE2_EXECUTION_ENGINE.md):
  queued --claim--> claimed --result--> completed | failed
                ^                       |
                +---- claim TTL expiry (requeue, attempts+1; failed at max) ----+

Auth: the worker holds the *node owner's* API key. Interim measure until
node-signed envelopes (Ed25519) arrive with Phase 5 (see docs/NETWORK_PROTOCOL.md).

Concurrency: claim uses SELECT ... FOR UPDATE SKIP LOCKED where the dialect
supports it (PostgreSQL profile). The SQLite dev profile has no row locks —
single-process dev only; production runs PostgreSQL.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_settings
from app.config import Settings
from app.models import Node, Task, User
from app.schemas import ClaimIn, ClaimOut, ClaimedTaskOut, ResultIn, ResultOut

router = APIRouter(prefix="/workers", tags=["workers"])


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite round-trips tz-aware datetimes as naive (offset dropped);
    normalize before any Python-side comparison. PostgreSQL keeps tzinfo —
    this helper is a no-op there."""
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


async def _requeue_expired_claims(db: AsyncSession, settings: Settings, now: datetime) -> int:
    """Return expired claims to the queue; permanently fail exhausted tasks.

    Volunteer nodes vanish mid-task (phone lock, airplane mode, crash) — the
    claim TTL is the liveness assumption, and requeue-on-expiry is the failure
    handling Phase 5's kill-node-mid-task gate will formally test.
    """
    cutoff = now - timedelta(seconds=settings.claim_ttl_sec)
    expired = (await db.scalars(
        select(Task).where(Task.status == "claimed", Task.claimed_at < cutoff)
    )).all()
    requeued = 0
    for task in expired:
        if _aware(task.claimed_at) is not None and _aware(task.claimed_at) >= cutoff:
            continue  # defensive: skip non-expired rows (dialect quirks)
        task.attempts += 1
        if task.attempts >= settings.max_task_attempts:
            task.status = "failed"
            task.result = {"error": f"claim expired {task.attempts}x (max attempts reached)"}
            task.claimed_by = None
            task.claimed_at = None
        else:
            task.status = "queued"
            task.claimed_by = None
            task.claimed_at = None
            requeued += 1
    if expired:
        await db.commit()
    return requeued


async def _require_registered_node(db: AsyncSession, node_id: str) -> Node:
    node = await db.scalar(select(Node).where(Node.node_id == node_id))
    if node is None:
        raise HTTPException(status_code=404, detail="node not registered")
    return node


@router.post("/claim", response_model=ClaimOut)
async def claim_task(
    payload: ClaimIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(get_current_user),
):
    """Claim the next queued task for this node (priority, then FIFO).

    `models` filters to tasks the worker can actually serve. Tasks with no
    routable model (e.g. kind=vision today) are never claimed — they queue
    until a capable runtime exists; responses never pretend otherwise.
    """
    now = datetime.now(timezone.utc)
    requeued = await _requeue_expired_claims(db, settings, now)
    await _require_registered_node(db, payload.node_id)

    stmt = select(Task).where(Task.status == "queued", Task.model_id.is_not(None))
    if payload.models:
        stmt = stmt.where(Task.model_id.in_(payload.models))
    stmt = stmt.order_by(Task.priority.asc(), Task.created_at.asc()).limit(1)
    # FOR UPDATE SKIP LOCKED on PostgreSQL; a no-op clause on SQLite (dev).
    stmt = stmt.with_for_update(skip_locked=True)

    task = (await db.scalars(stmt)).first()
    if task is None:
        return ClaimOut(accepted=False, task=None, requeued=requeued)

    if task.deadline_at is not None and _aware(task.deadline_at) < now:
        task.status = "failed"
        task.result = {"error": "deadline exceeded before claim"}
        await db.commit()
        return ClaimOut(accepted=False, task=None, requeued=requeued)

    task.status = "claimed"
    task.claimed_by = payload.node_id
    task.claimed_at = now
    await db.commit()
    return ClaimOut(
        accepted=True,
        task=ClaimedTaskOut(
            id=task.id,
            kind=task.kind,
            model_id=task.model_id,
            input=task.input,
            priority=task.priority,
            attempts=task.attempts,
            deadline_at=task.deadline_at,
        ),
        requeued=requeued,
    )


@router.post("/results", response_model=ResultOut)
async def submit_result(
    payload: ResultIn,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Record a worker's outcome for a task it holds a live claim on.

    A result for an expired claim (requeued meanwhile) is rejected with 409 —
    another worker may already own the task; late results must not clobber it.
    """
    task = await db.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status != "claimed" or task.claimed_by != payload.node_id:
        raise HTTPException(
            status_code=409,
            detail=f"task not claimed by this node (status={task.status})",
        )
    if payload.status == "completed":
        task.status = "completed"
        task.result = payload.result
    else:
        task.status = "failed"
        task.result = {"error": payload.error or "worker reported failure", **payload.result}
    await db.commit()
    return ResultOut(task_id=task.id, status=task.status)
