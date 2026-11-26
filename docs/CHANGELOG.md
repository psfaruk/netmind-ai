# Changelog

Format: Keep-a-Changelog-ish, dates ISO. Project follows phase gates in `DEVELOPMENT_PHASES.md`.

## [Android 0.2.0-alpha.1] — 2026-11-27 — app overhaul (Claude-style UI + multilingual)
### Added
- Gemma 3 4B (Q4_K_M) as default model preset — validated locally: fluent, structured বাংলা answers (2361 chars, no repetition), 140+ languages, ~2.4 GB download / ~4 GB RAM. Qwen3-0.6B remains as the light preset; existing installs keep their downloaded Qwen file (migration in Prefs).
- Deep Think mode ON by default: live "Thinking · N tokens" row while Qwen3 reasons, then streaming answer with text cursor; toggle chip for instant (/no_think) mode.
- Claude-style chat UI: warm cream+coral day/night theme, serif wordmark, welcome screen (time-aware greeting + 4 suggestion cards), user bubbles / plain assistant text with avatar, per-message stats (thought/answered tokens, tok/s), copy action, send/stop morphing button, model auto-load via status chip (Prepare button removed).
### Changed
- Multilingual + thorough system prompt (mirror user's language, structured depth); max generation 512 → 1024 tokens; Qwen3 thinking-mode sampling (temp 0.6, top_p 0.95, top_k 20) in the JNI engine.
### Fixed
- Thinking-mode repetition loops (temp/sampling), empty-reply row cleanup, meta stats for non-thinking models.
### Known limits (honest)
- Qwen3-0.6B produces word-salad Bangla (model capacity, not a prompt bug) — hence the Gemma default. 0.6B ≠ Claude Opus: quality gap is hardware/model-size bound; the distributed-network phase is the path beyond it.

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
