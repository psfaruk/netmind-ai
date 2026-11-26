"""API v1 aggregation."""
from fastapi import APIRouter

from app.api.v1 import auth, models, monitoring, nodes, placeholders, tasks, workers

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(models.router)
api_router.include_router(nodes.router)
api_router.include_router(tasks.router)
api_router.include_router(workers.router)
api_router.include_router(monitoring.router)
api_router.include_router(placeholders.router)
