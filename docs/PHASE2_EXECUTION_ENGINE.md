# Phase 2 Execution Engine

> Status: **Implemented & Tested (coordination core)** — model routing, task claim/submit, claim-expiry requeue, worker node service. **Prototype (inference)** — the execution path is exercised end-to-end with the honestly-labeled mock runtime; real GGUF inference via llama.cpp is implemented as an adapter and runs where a llama-server exists (see `WORKER_NODE_GUIDE.md`). Streaming responses, multi-model orchestration and intent detection remain later Phase 2 sub-deliverables.

## 1. What Phase 2 adds

Phase 1 persisted tasks and said so. Phase 2 closes the loop:

```
user ── POST /tasks ──▶ routing (kind → registry model) ──▶ queued
worker ── POST /workers/claim ──▶ claimed (claimed_by, claimed_at)
worker ── runtime.generate() ──▶ real or mock inference
worker ── POST /workers/results ──▶ completed | failed
user ── GET /tasks/{id} ──▶ result record
```

Every step is persisted; the coordinator holds no authoritative in-memory state (ADR-011).

## 2. Task state machine

```
                 ┌──────────────────────────────────────────────┐
                 │ claim TTL expired (default 120 s)            │
                 │ → requeue, attempts+1; at 3 attempts → failed│
                 ▼                                              │
queued ──claim──▶ claimed ──result──▶ completed | failed ◀─cancel─┘
```

| Transition | Trigger | Fields written |
|---|---|---|
| queued → claimed | `POST /workers/claim` | `claimed_by`, `claimed_at` |
| claimed → completed | `POST /workers/results` (status=completed) | `result` (output, backend, tokens, duration_ms) |
| claimed → failed | result (status=failed) or runtime error | `result.error` |
| claimed → queued | claim TTL expiry (liveness assumption for volunteer nodes) | attempts+1, claim cleared |
| queued → failed | attempts ≥ `NETMIND_MAX_TASK_ATTEMPTS` (3) | `result.error="claim expired Nx (max attempts reached)"` |
| queued → failed | deadline passed before claim | `result.error="deadline exceeded before claim"` |
| any active → cancelled | owner `POST /tasks/{id}/cancel` | status only |

A late result for an expired claim is **rejected (409)** — the task may already belong to another worker; late results must not clobber live claims.

## 3. Model routing (minimal, deterministic)

`app/routing.py` maps each task kind to a registry model (small models first — CPU/phone budget):

| kind | routed model |
|---|---|
| chat | `qwen3-0.6b-q4` |
| research, coding, math | `qwen3-1.7b-q4` |
| translation | `qwen3-4b-q4` |
| vision | *none* — queued honestly; no multimodal runtime exists yet |

Submitters can override with an explicit `model_id`. Routing records intent, **not** availability: a routed task executes only when a worker advertising that model claims it. Unroutable tasks queue and responses say so.

Capability+load-aware routing (registry availability, node load, latency) is a later Phase 2 increment; the current table is deliberately dumb and testable.

## 4. Worker node service (`services/worker/`)

Pull-based loop, outbound-only (ADR-004): register → heartbeat → claim → execute → submit.

- **`worker/runtime/`** — pluggable backends behind `InferenceRuntime.generate()`:
  - `MockRuntime` — deterministic, output always labeled `[MOCK RUNTIME] No model inference has occurred`. Exists so CI proves the pipeline without a model; never pretends to be model output.
  - `LlamaCppRuntime` — OpenAI-compatible HTTP client for `llama-server` (ADR-005, CPU-first, Termux-compatible). Health probe + generation with token accounting.
- **`worker/coordinator_client.py`** — thin typed client; `httpx` with `X-API-Key` (node-signed envelopes arrive Phase 5).
- **`worker/poller.py` (`WorkerNode`)** — one method per step, each unit-testable; `run_forever()` just loops them. Phase 5 swaps HTTP polling for a persistent WSS channel without touching execution logic.
- **`worker/main.py`** — control API: `/health`, `/status` (advertised models, hardware, counters), `/local-generate` (runtime sanity without the coordinator).

## 5. Reliability model (why claim TTL exists)

Volunteer nodes vanish mid-task: phone locks, Doze, airplane mode, crashes. The coordinator's liveness assumption is the **claim TTL** (default 120 s): heartbeats refresh node state, and any new claim call first requeues expired claims. This is the mechanism the Phase 5 acceptance test (kill-node-mid-task → task completes via reassignment) will formally exercise; the unit tests already cover it (`test_workers.py::test_expired_claim_requeued_to_next_worker`).

## 6. Concurrency notes

- Claim selection uses `SELECT ... FOR UPDATE SKIP LOCKED` where the dialect supports it (PostgreSQL production profile). SQLite (dev/tests) has no row locks — single-process development only.
- SQLite round-trips tz-aware datetimes as naive; the engine normalizes before comparison (`_aware()`), a no-op on PostgreSQL.

## 7. Test coverage (71 tests, all passing at delivery)

| Suite | What it proves |
|---|---|
| coordinator `test_workers.py` (14) | routing stamps models; claim/submit roundtrip; model filter; priority+fifo order; wrong-node and unclaimed submits rejected (409); auth required; expiry requeue; late-result rejection; attempts exhaustion; deadline failure |
| coordinator Phase-1 suites (35) | no regressions |
| worker `test_runtime_mock.py` (4) | honest labeling, determinism |
| worker `test_runtime_llamacpp.py` (4) | OpenAI-shape parsing, error mapping (stubbed server) |
| worker `test_coordinator_client.py` (5) | request formation, auth header, error raising |
| worker `test_worker_node.py` (6) | execute/submit happy path, failure path, conflicts counted |
| worker `test_e2e_mock.py` (3) | **full in-process pipeline** incl. 3-task drain and unroutable-vision stays queued |
| live smoke (`scripts/phase2_smoke.sh`) | two real uvicorn processes over HTTP: submit → claim → completed record → monitoring |

## 8. What Phase 2 still owes (later sub-phases)

- Streaming answers (SSE) — acceptance criterion "streamed answer" not yet met; currently results are one-shot records.
- Intent detection + Universal Task Planner step 1 (the "Intelligence" half of the phase title).
- Response orchestration across models; feedback endpoint (`/feedback` 501 placeholder exists).
- Real-model smoke on owner hardware/VPS (llama-server + Qwen3-0.6B GGUF, Q4_K_M, ≈0.5 GB download) — adapter implemented, live run deferred by environment, honestly.
- Bengali language quality baseline (evaluation sets still unbuilt).
