"""/api/v1/nodes — node registration, capability advertisement, heartbeats (Phase 1, Tested).

Interim auth note: heartbeat currently requires a user JWT/API key; node-signed
envelopes (Ed25519) arrive with Phase 5 per docs/NETWORK_PROTOCOL.md."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models import Node, NodeHeartbeat, User
from app.schemas import HeartbeatIn, HeartbeatOut, NodePublicOut, NodeRegisterIn

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("/register", response_model=NodePublicOut, status_code=201)
async def register_node(
    payload: NodeRegisterIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Register or update a node: identity + advertised capabilities.

    Listings expose only public fields; contribution limits and owner stay private
    (master prompt §3: never expose sensitive device information)."""
    node = await db.scalar(select(Node).where(Node.node_id == payload.node_id))
    if node is None:
        node = Node(
            node_id=payload.node_id,
            owner_user_id=user.id,
            platform=payload.platform,
            cpu_cores=payload.cpu_cores,
            ram_mb=payload.ram_mb,
            gpu=payload.gpu,
            runtimes=payload.runtimes,
            region=payload.region,
            contribution_limits=payload.contribution_limits,
            state="registered",
        )
        db.add(node)
    else:
        if node.owner_user_id != user.id:
            raise HTTPException(status_code=403, detail="node owned by another user")
        node.platform = payload.platform
        node.cpu_cores = payload.cpu_cores
        node.ram_mb = payload.ram_mb
        node.gpu = payload.gpu
        node.runtimes = payload.runtimes
        node.region = payload.region
        node.contribution_limits = payload.contribution_limits
    await db.commit()
    await db.refresh(node)
    return NodePublicOut.model_validate(node, from_attributes=True)


@router.get("", response_model=list[NodePublicOut])
async def list_nodes(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    nodes = await db.scalars(select(Node).order_by(Node.created_at))
    return [NodePublicOut.model_validate(n, from_attributes=True) for n in nodes]


@router.post("/{node_id}/heartbeat", response_model=HeartbeatOut)
async def heartbeat(
    node_id: str,
    payload: HeartbeatIn,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    node = await db.scalar(select(Node).where(Node.node_id == node_id))
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    now = datetime.now(timezone.utc)
    node.last_heartbeat_at = now
    if node.state in ("registered", "stale"):
        node.state = "active"
    db.add(
        NodeHeartbeat(
            node_id=node.node_id,
            ts=now,
            cpu_load_pct=payload.cpu_load_pct,
            free_ram_mb=payload.free_ram_mb,
            active_tasks=payload.active_tasks,
        )
    )
    await db.commit()
    return HeartbeatOut(node_id=node.node_id, state=node.state)
