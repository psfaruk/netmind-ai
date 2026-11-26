"""/api/v1/{agents,knowledge,research,compute,feedback} — documented 501 placeholders.

These endpoint groups exist so the API surface is explicit and versioned from day one.
They return 501 Not Implemented with the phase that will implement them — honest
placeholders, per docs/API_REFERENCE.md (charter rule #14: documented, not silent)."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["planned"])

_GROUPS = {
    "agents": {"path": "/agents", "phase": 4},
    "knowledge": {"path": "/knowledge", "phase": 3},
    "research": {"path": "/research", "phase": 4},
    "compute": {"path": "/compute", "phase": 5},
    "feedback": {"path": "/feedback", "phase": 2},
}


def _planned(group: str, phase: int):
    async def handler() -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={"detail": f"Planned for Phase {phase}", "phase": phase, "group": group},
        )

    return handler


for _group, _meta in _GROUPS.items():
    router.add_api_route(
        _meta["path"],
        _planned(_group, _meta["phase"]),
        methods=["GET"],
        summary=f"[Planned — Phase {_meta['phase']}] {_group} endpoint group",
    )
