# NETMIND AI

**Intelligence Without Infrastructure Boundaries.**

NETMIND AI is a distributed artificial-intelligence network that combines computing resources from voluntarily participating devices — ordinary computers, Android phones, optional servers — instead of depending on a centralized GPU cluster owned by the project.

- **Hybrid coordination:** a lightweight coordinator manages identity, discovery, scheduling and verification.
- **Distributed computation:** actual inference work happens on independently operated nodes.
- **Honest engineering:** every capability is labeled by its real status; nothing is claimed before it is tested.

This repository currently contains **Phase 0 deliverables** (research, architecture, roadmap, documentation set), the **Phase 1 backend skeleton**, and the **Phase 2 execution engine** (routing, claim/submit, worker service). See `docs/DEVELOPMENT_PHASES.md` for the full phase plan.

---

## Repository Layout

```
netmind-ai/
├── README.md                     ← you are here
├── docs/                         ← Section 18 documentation set (15 files + research)
├── diagrams/                     ← architecture diagrams (PNG, embedded in docs)
└── services/
    ├── coordinator/              ← Phase 1+2 backend (FastAPI + SQLAlchemy)
    │   ├── app/
    │   │   ├── main.py           app factory, health/readiness, middleware
    │   │   ├── config.py         pydantic-settings configuration
    │   │   ├── logging.py        structured JSON logging + request IDs
    │   │   ├── db.py             async engine/session, schema init
    │   │   ├── models.py         SQLAlchemy ORM models (incl. task execution columns)
    │   │   ├── schemas.py         Pydantic request/response schemas
    │   │   ├── routing.py         kind → registry model routing (Phase 2)
    │   │   ├── core/security.py   password hashing (scrypt) + JWT
    │   │   └── api/v1/            routers: auth, models, nodes, tasks, workers, monitoring
    │   ├── tests/                pytest + httpx AsyncClient suite
    │   ├── requirements.txt / Dockerfile / docker-compose.yml
    └── worker/                  ← Phase 2 worker node service
        ├── worker/
        │   ├── main.py           control API (/health, /status, /local-generate)
        │   ├── config.py         env config, node identity persistence
        │   ├── poller.py          WorkerNode: register → heartbeat → claim → execute → submit
        │   ├── coordinator_client.py   typed coordinator HTTP client
        │   ├── hardware.py        capability detection (Termux/Linux aware)
        │   └── runtime/           InferenceRuntime adapters: mock (labeled) + llama.cpp
        ├── tests/                unit + in-process E2E (coordinator + worker, mock runtime)
        ├── requirements.txt / Dockerfile / pytest.ini
```

## Documentation Index

| Document | Purpose |
|---|---|
| [docs/MASTER_ARCHITECTURE.md](docs/MASTER_ARCHITECTURE.md) | The five-system architecture and design principles |
| [docs/TECHNICAL_BLUEPRINT.md](docs/TECHNICAL_BLUEPRINT.md) | Technology stack, repo structure, mobile-first dev workflow |
| [docs/RESEARCH_AND_FEASIBILITY.md](docs/RESEARCH_AND_FEASIBILITY.md) | Existing-project research (cited), feasibility, risk register |
| [docs/NETWORK_PROTOCOL.md](docs/NETWORK_PROTOCOL.md) | Node lifecycle, message envelope, transports, NAT strategy |
| [docs/AI_MODEL_REGISTRY.md](docs/AI_MODEL_REGISTRY.md) | Model registry schema and starter catalog (2026 landscape) |
| [docs/KNOWLEDGE_ENGINE.md](docs/KNOWLEDGE_ENGINE.md) | Knowledge sources, ingestion, RAG pipeline |
| [docs/TASK_EXECUTION_FLOW.md](docs/TASK_EXECUTION_FLOW.md) | The 17-step Universal Task Planner pipeline |
| [docs/PHASE2_EXECUTION_ENGINE.md](docs/PHASE2_EXECUTION_ENGINE.md) | Phase 2 task state machine, claim TTL, runtime adapters, test coverage |
| [docs/WORKER_NODE_GUIDE.md](docs/WORKER_NODE_GUIDE.md) | Running a worker node (Termux/Linux; mock or llama.cpp runtime) |
| [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) | Threat model, node identity, signed tasks, sandboxing |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | `/api/v1` endpoint groups with examples |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | PostgreSQL schema — implemented vs planned tables |
| [docs/ANDROID_NODE.md](docs/ANDROID_NODE.md) | Android client + compute-contributor design, Termux path |
| [docs/DEVELOPMENT_PHASES.md](docs/DEVELOPMENT_PHASES.md) | Phase 0–11 roadmap with acceptance criteria |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Test categories, failure-scenario matrix, benchmarks |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records (ADR) |
| [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | What does **not** work yet — stated honestly |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Version history |

Diagrams: [system architecture](diagrams/system_architecture.png) · [dependency graph](diagrams/dependency_graph.png) · [task execution flow](diagrams/task_execution_flow.png) · [Phase 2 execution flow](diagrams/phase2_execution_flow.png) · [development roadmap](diagrams/development_roadmap.png) · [Alpha topology](diagrams/alpha_topology.png)

## Quick Start (works from an Android phone via Termux, or any Linux machine)

```bash
git clone <this-repo> netmind-ai && cd netmind-ai/services/coordinator

python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Dev profile uses SQLite so no database server is needed for the first run.
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/docs` for the interactive OpenAPI documentation, or:

```bash
curl http://localhost:8000/health
```

Run the test suite:

```bash
pytest -q
```

## Run a worker node (Phase 2)

Second terminal, same machine or any other (Android via Termux works):

```bash
cd ../worker
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

export NETMIND_COORDINATOR_URL=http://127.0.0.1:8000
export NETMIND_API_KEY=nm_...        # create via /api/v1/auth/api-keys
export NETMIND_RUNTIME=mock          # honest mock; use "llamacpp" with a llama-server
uvicorn worker.main:app --port 8090
```

Submit a task on one side, watch it get claimed and completed on the other —
full instructions and the real-inference path: `docs/WORKER_NODE_GUIDE.md`.

Worker test suite: `cd services/worker && pytest -q`.

Production profile (PostgreSQL) uses `docker-compose.yml` — see `docs/TECHNICAL_BLUEPRINT.md`.

## Status Legend (used across all docs and code)

| Label | Meaning |
|---|---|
| **Planned** | designed, not started |
| **In Progress** | being built |
| **Prototype** | runs in a limited setting, not hardened |
| **Experimental** | runs, but outcome/quality unproven |
| **Implemented** | feature-complete against its design |
| **Tested** | covered by automated tests that pass |
| **Production Ready** | hardened, documented, load/security tested |

Current headline status:

| Component | Status |
|---|---|
| Phase 0 research & architecture docs | **Implemented** (this set) |
| Coordinator API skeleton (auth/nodes/models/tasks/monitoring) | **Tested** (pytest suite, SQLite dev profile) |
| Task execution engine: routing, claim/submit, claim-expiry requeue | **Tested** (14 endpoint tests + failure paths) |
| Worker node service (pull loop, mock + llama.cpp adapters) | **Tested** via mock E2E (in-process + two-process uvicorn smoke) |
| Real GGUF inference (llama.cpp) | **Implemented adapter** — live-model smoke deferred to owner hardware (honest) |
| PostgreSQL production profile | **Implemented** (compose file), not yet load-tested |
| Streaming (SSE), intent planner, Knowledge Engine, Agents, P2P, Android app | **Planned** (Phase 2 remainder / 3+) |

## Ground Rules (from the engineering charter)

1. Nothing is claimed to work before it is tested.
2. No fake API integrations; no fabricated model outputs.
3. Compute participation is always explicit opt-in, with visible usage and a stop switch.
4. Model licenses are verified before any model enters the registry.
5. No cryptocurrency mining, no hidden resource extraction, no silent background work on phones.

License for this repository: **Apache-2.0** (working default per `docs/DECISIONS.md` ADR-012; owner ratification pending).
