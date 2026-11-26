# Changelog

Format: Keep-a-Changelog-ish, dates ISO. Project follows phase gates in `DEVELOPMENT_PHASES.md`.

## [0.3.0] — 2026-11-26 — Phase 2 (execution engine core)
### Added
- Task execution engine: model routing (kind → registry model, explicit override), worker claim (`POST /api/v1/workers/claim`, priority+FIFO, `FOR UPDATE SKIP LOCKED` on PostgreSQL), result submission (`POST /api/v1/workers/results`), claim-TTL expiry requeue with attempts cap, deadline enforcement at claim time, late-result rejection (409).
- Worker node service (`services/worker/`): pull-based loop (register → heartbeat → claim → execute → submit), pluggable runtimes — MockRuntime (honest, labeled) and LlamaCppRuntime (llama-server OpenAI-compatible HTTP), coordinator client, control API (`/health`, `/status`, `/local-generate`), persistent node identity, Dockerfile.
- Tests: 37 new cases (14 coordinator worker-endpoints, 23 worker incl. 3 in-process E2E) — 71 total, all passing; live two-process uvicorn smoke (submit → claim → completed record).
- Docs: PHASE2_EXECUTION_ENGINE.md, WORKER_NODE_GUIDE.md, ADR-012/013/014, updated API_REFERENCE, DATABASE_SCHEMA (task execution columns), KNOWN_LIMITATIONS, README.
### Honest deferrals
- Real-model smoke (llama-server + Qwen3 GGUF) deferred to owner hardware — adapter implemented, not yet exercised against a live model.
- Streaming (SSE), intent detection/Universal Task Planner, response orchestration — later Phase 2 sub-phases.

## [0.2.0] — 2026-11-26 — Phase 1 (partial, skeleton)
### Added
- Coordinator service skeleton: FastAPI app factory, health/readiness, request-ID + JSON logging middleware.
- Auth: registration, login (JWT), `/me`, API keys (hashed, revocable).
- Routers: `/api/v1/auth`, `/models` (seeded registry metadata), `/nodes` (register/heartbeat/list), `/tasks` (create/status/cancel — persisted queue only, execution arrives Phase 2, stated honestly in responses), `/monitoring/stats`; documented 501 groups for agents/knowledge/research/compute/feedback.
- SQLAlchemy models: users, api_keys, nodes, node_heartbeats, model_registry, tasks; SQLite dev profile + PostgreSQL production profile; docker-compose.
- Test suite: 34 pytest cases (auth, keys, nodes, tasks, models, monitoring, rate limit) — all passing at delivery.
- docs updated: TECHNICAL_BLUEPRINT, API_REFERENCE, DATABASE_SCHEMA, TESTING_STRATEGY, DECISIONS (ADR-002…011), README statuses.

## [0.1.0] — 2026-11-26 — Phase 0
### Added
- Research & feasibility report with 2026 sources (Petals, exo, BOINC, llama.cpp, Flower, libp2p, model landscape, Bengali ASR).
- Master architecture (five systems), network protocol, model registry design, knowledge engine design, task execution pipeline (17 steps), security architecture, API surface, DB schema, Android node design, phases with acceptance criteria, testing strategy, ADR set, known limitations.
- Five rendered diagrams: system architecture, dependency graph, task execution flow, roadmap, Alpha topology.
