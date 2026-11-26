# Development Phases

> Status: **Phase 0 ✓ · Phase 1 ✓ (core; CI wiring remaining) · Phase 2 In Progress (execution engine delivered; streaming/intent/planner remaining)**. A phase is complete only when every acceptance criterion passes — never by calendar.

![Development roadmap](../diagrams/development_roadmap.png)

Capacity assumption: one developer, ~10–15 h/week, Android-first tooling (owner's constraint). Estimates are ranges, not promises.

| Phase | Duration (est.) | Deliverables | Acceptance criteria (gate) | Status |
|---|---|---|---|---|
| **0 Research & Feasibility** | done | research report (cited), feasibility, architecture, risk register, docs set, Alpha design | owner review & approval of architecture | **✓ Completed Nov 2026** |
| **1 Architecture Foundation** | 2–3 wk | FastAPI skeleton, auth (JWT+API keys), config, JSON logging, DB models, health monitoring, tests, Docker | CI green: health/auth/registry endpoints pass on every commit; docs at `/docs` | **◆ In Progress — delivered & tested locally; CI wiring remaining** |
| **2 Intelligence Coordinator** | 4–6 wk | intent detection, task planner, model routing, response orchestration with one small GGUF model | end-to-end: request → routed model → streamed answer persisted as task record | **◆ In Progress — execution engine delivered & tested (routing, claim/submit, requeue, worker service; E2E via labeled mock runtime + live uvicorn smoke); intent planner, streaming (SSE), live-GGUF smoke remaining** |
| **3 Knowledge Engine** | 4–6 wk | ingestion, embeddings, vector index, retrieval, cited RAG | cited answers over 1,000+ doc corpus; recall@5 ≥ 0.75 | Planned |
| **4 Multi-Agent Intelligence** | ~4 wk | Research/Coding/Reasoning/Verification agents, messaging, orchestration | decomposed task completes in budget; no agent loops possible | Planned |
| **5 Distributed Node Prototype** | 4–6 wk | 3 logical nodes (3 processes), registration, discovery, scheduling, execution, failure handling | kill-node-mid-task → completes via reassignment; conflict detection works | Planned |
| **6 Android Compute Node** | 6–8 wk | Android app: register, connect, advertise, execute light work, dashboard, pause/stop | thermal/battery/data limits respected; opt-in + stop switch demonstrable; no silent background work | Planned |
| **7 Global P2P Network** | 8+ wk (experimental) | peer discovery, secure transport, NAT traversal + relay, distributed scheduling, reputation | two nodes behind different NATs exchange signed traffic; coordinator outage tolerated for queued work | Planned |
| **8 Advanced Distributed Inference** | research | model sharding, pipeline parallelism prototypes vs task-level benchmarks | adopted **only** if measured better than task-level distribution on real hardware | Planned (experimental) |
| **9 Distributed Learning** | ~8 wk | federated experiments (Flower), dataset/model versioning, distillation | measured improvement on eval sets; zero private data leaves devices | Planned |
| **10 Production Readiness** | 4–6 wk | security audit, load/perf/recovery/privacy tests, docs, deployment automation | all `TESTING_STRATEGY.md` categories green, incl. the 9 failure scenarios | Planned |
| **11 Global Expansion** | ongoing | multi-region, public onboarding, developer docs, contribution policy, public API | third-party node onboarding runbook works end-to-end | Planned |

## Rules of Progression

1. **No phase starts before the previous gate passes** (owner-approved exceptions recorded in `DECISIONS.md`).
2. **No silent scope changes:** architecture-level changes follow the 7-step process (document proposal → rationale → affected components → security/perf impact → update docs → implement+test → record decision).
3. **Status vocabulary is enforced** in READMEs, docs, and API responses: Planned / In Progress / Prototype / Experimental / Implemented / Tested / Production Ready.
4. **Every phase ships tests with it** — a feature without a test is not "Implemented".
5. Estimates are owner-capacity assumptions; slippage is reported, never hidden.
