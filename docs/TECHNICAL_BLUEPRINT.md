# Technical Blueprint

> Status: **Implemented (Phase 0/1)** — stack selection is binding unless changed via `DECISIONS.md` (ADR).

## 1. Stack Selection (smallest viable set first)

| Layer | Choice | Why | Deferred alternatives |
|---|---|---|---|
| Language | **Python 3.12** | one language for coordinator + worker + research | — |
| API framework | **FastAPI + Pydantic v2** | async, automatic OpenAPI docs, strict validation, tiny surface | Litestar (no benefit yet) |
| Config | **pydantic-settings** | typed env config, profiles (dev SQLite / prod Postgres) | — |
| Database | **PostgreSQL 16** (dev profile: SQLite via aiosqlite) | relational core: users, nodes, tasks, registry; SQL standard | — |
| ORM | **SQLAlchemy 2.0 (async)** | mature async ORM, works with both drivers | Tortoise (weaker ecosystem) |
| Cache/queue | **Redis** — *deferred to Phase 2*, SQLite/task-table polling until then | avoid unused dependencies (Engineering rule: simplest reliable solution) | Celery (heavier than needed) |
| Auth | **JWT (PyJWT) + scrypt password hashing (stdlib)** | no native-wheel dependency risk on Termux; upgrade path to argon2 recorded (ADR-006) | passlib/bcrypt |
| Logging | stdlib logging + **JSON formatter + request IDs** | structured logs with zero extra deps | structlog (Phase 2 if needed) |
| Inference runtime | **llama.cpp (GGUF)** | CPU-first, quantized, official Android support ([docs/android.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md)), runs in Termux | ONNX Runtime, PyTorch |
| Serving (GPU nodes, later) | vLLM | throughput serving for optional server nodes | SGLang |
| Vectors | **pgvector first**, Qdrant when scale demands | one database fewer to operate at Alpha scale | Qdrant, Milvus |
| Object storage | filesystem → S3-compatible (MinIO) later | Phase 3 documents | — |
| P2P transport | **Secure WebSocket (WSS) in Phase 5**; **libp2p (QUIC) research in Phase 7** | libp2p gives NAT traversal/hole-punching + relay ([libp2p.io](https://libp2p.io)); WebRTC unnecessary in coordinator-star topology | WebRTC |
| Federated learning | **Flower** (Phase 9) | framework-agnostic ([flower.ai](https://flower.ai)) | custom FL |
| Android | **Kotlin + Jetpack Compose**; Termux worker as prototype bridge | prototype speed vs production app | Flutter |
| Web | **Next.js + TypeScript** (Phase 5+) | responsive dashboard | — |
| Infra | **Docker + docker-compose**, GitHub Actions CI | reproducible, mobile-friendly (can run on VPS) | k8s (explicitly rejected until scale demands) |

## 2. Repository Structure

```
netmind-ai/
├── docs/                          # Section 18 documentation set
├── diagrams/                      # rendered PNG diagrams
├── services/
│   ├── coordinator/               # FastAPI service (Phase 1 skeleton delivered)
│   │   ├── app/
│   │   │   ├── main.py            # create_app(), /health, /ready, middleware
│   │   │   ├── config.py          # NETMIND_* env settings, dev/prod profiles
│   │   │   ├── logging.py         # JSON logs + X-Request-ID
│   │   │   ├── db.py              # async engine, session, init_db()
│   │   │   ├── models.py         # SQLAlchemy models (Phase 1 subset)
│   │   │   ├── schemas.py         # Pydantic API schemas
│   │   │   ├── core/security.py   # scrypt hash, JWT create/verify
│   │   │   └── api/v1/            # auth, models, nodes, tasks, monitoring routers
│   │   ├── tests/                 # pytest + httpx.AsyncClient (SQLite)
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── docker-compose.yml     # postgres + coordinator (prod profile)
│   ├── node-worker/               # Planned (Phase 5): Python worker
│   └── android/                   # Planned (Phase 6): Kotlin app
└── web/                            # Planned (Phase 5+): Next.js interface
```

## 3. Runtime Strategy

- **Alpha (Phase 2):** one small GGUF model (Qwen3-family 1.7B–4B class, Apache-2.0) loaded by llama.cpp on the developer machine; coordinator routes to it via the node worker.
- **Production:** model registry lists which node holds which model; cold-start weights are cached on nodes; the scheduler prefers warm nodes to avoid model-load latency.
- **Quantization:** Q4_K_M as default balance; Q8 for evaluation-sensitive tasks; document actual memory use in the registry.

## 4. Mobile-First Development Workflow (Android phone as primary device)

The project owner may initially have only an Android smartphone. Supported paths:

1. **Termux (local, free):**
   ```bash
   pkg update && pkg install python git
   git clone <repo> && cd netmind-ai/services/coordinator
   python -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   pytest -q                     # run the whole suite from the phone
   uvicorn app.main:app --port 8000   # serve locally
   ```
2. **GitHub (any phone browser):** repo hosting, PR review, Issues; GitHub Actions runs CI so tests execute without a local machine.
3. **Cloud dev (when more power needed):** GitHub Codespaces / any SSH-able VPS running the same `docker-compose.yml`; Termux `ssh` connects from the phone.
4. **Separation of concerns:** local dev (phone/Termux) never hosts production data; the remote coordinator does. Configuration is entirely env-driven (`NETMIND_*`), so the same code runs in both places.

Commands are deliberately kept short and copy-pastable per the master prompt's Android-first requirement.

## 5. CI/CD (Planned — Phase 1 completion)

GitHub Actions matrix: Python 3.12 on ubuntu-latest; steps = install → `ruff check` (lint, non-blocking initially) → `pytest -q`. Docker image build on tag. Deployment automation is Phase 10 scope.

## 6. Observability

- `/health` (liveness) and `/ready` (DB connectivity) — **Implemented**.
- `/api/v1/monitoring/stats` — entity counts (users, nodes, models, tasks) — **Implemented**.
- Structured JSON logs with request IDs — **Implemented**.
- Metrics/telemetry stack (Prometheus/Grafana) — **Planned (Phase 10)**.
