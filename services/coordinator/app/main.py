"""NETMIND Coordinator — FastAPI application factory (Phase 1 skeleton).

Run:  uvicorn app.main:app --port 8000   (docs at /docs)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1 import api_router
from app.config import Settings
from app.db import configure_engine, get_engine, init_db, seed_model_registry
from app.logging import RequestIdAndAccessLogMiddleware, configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.enforce_production_safety()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=(
            "NETMIND AI coordinator — hybrid coordination layer. "
            "Phase 2: task execution engine (routing, claim/submit, claim-expiry "
            "requeue). Inference runs on worker nodes; CI exercises the full "
            "pipeline with a clearly-labeled mock runtime, never fabricated output."
        ),
    )
    app.state.settings = settings
    configure_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db()
        await seed_model_registry()
        yield

    app.router.lifespan_context = lifespan
    app.add_middleware(RequestIdAndAccessLogMiddleware)
    if settings.cors_origins:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list(),
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health", tags=["system"], summary="Liveness probe")
    async def health() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.version,
            "phase": "2 (execution engine)",
        }

    @app.get("/ready", tags=["system"], summary="Readiness probe (DB connectivity)")
    async def ready() -> dict:
        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ready", "database": "ok"}
        except Exception as exc:  # noqa: BLE001
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=503, content={"status": "not-ready", "database": str(exc.__class__.__name__)}
            )

    app.include_router(api_router)
    return app


app = create_app()
