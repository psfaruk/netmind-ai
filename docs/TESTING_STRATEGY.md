# Testing Strategy

> Status: **Phase 1 suite Implemented & passing (23 tests, SQLite dev profile)** · later-phase suites Planned per phase. "Never claim a feature works without testing it" is charter rule #1; this document is how that is operationalized.

## 1. Test Categories → Phases

| Category | Tooling | First required in |
|---|---|---|
| Unit tests | pytest | Phase 1 ✅ |
| API tests | httpx AsyncClient against the app | Phase 1 ✅ |
| Model routing tests | routing table cases + recorded outcomes | Phase 2 |
| Knowledge retrieval tests | recall@k on eval corpus | Phase 3 |
| Agent execution tests | orchestration depth/budget scenarios | Phase 4 |
| Node communication tests | worker + coordinator against `NETWORK_PROTOCOL.md` | Phase 5 |
| Security tests | authz bypass, envelope forgery, sandbox probes | Phase 5/10 |
| Performance tests | latency p50/p95, throughput, cost/answer | Phase 10 (benchmarks from Phase 2) |
| Failure recovery tests | the 9-scenario matrix below | Phase 5+ |

## 2. Current Suite (Phase 1, what actually passes)

- health/readiness probes (`/health`, `/ready`)
- auth: register (validation + duplicate rejection), login (bad password rejected), /me via JWT, API-key creation + auth round-trip, revoked key rejected
- models: seeded registry list, detail lookup, 404 path, admin-only creation
- nodes: register + capability storage, listing, heartbeat updates, unknown-node heartbeat 404
- tasks: create (validation, priority clamp), ownership check, cancel path, list
- monitoring: stats counts consistent with seeded state
- rate limiting: 429 + Retry-After beyond budget

Run: `cd services/coordinator && pytest -q` (34 passed at delivery; count grows with phases).

## 3. Failure-Scenario Matrix (mandatory before Phase 10)

| # | Scenario | Expected behavior | Test ID |
|---|---|---|---|
| F1 | Node disconnects during execution | heartbeat gap → reassignment → completion elsewhere | T-F1 |
| F2 | Node returns incorrect result | verifier rejects; error counter; not shown to user | T-F2 |
| F3 | Two nodes return conflicting results | `conflicted` → arbitration or explicit uncertainty | T-F3 |
| F4 | No suitable compute node available | queue + timeout notice, no exception | T-F4 |
| F5 | Model unavailable on node | refusal → alternate model/node pair | T-F5 |
| F6 | Knowledge source outdated | TTL miss → dated answer or refresh | T-F6 |
| F7 | Network latency increases | deadlines enforced, graceful partials where allowed | T-F7 |
| F8 | User cancels a task | `cancelled`, nodes notified, resources freed | T-F8 |
| F9 | Node exceeds its resource limit | node-side kill, `partial` + reason | T-F9 |

## 4. Benchmark Methodology (Phases 2, 8, 10)

Compare on identical workloads: (a) single CPU (one node, llama.cpp), (b) single GPU if available, (c) distributed task-level execution, (d) hybrid. Record: latency distribution, throughput, answers/hour, wall-clock cost estimate, energy where measurable. **Adopt a distributed method only if it beats (a) on measured latency or cost** — the benchmark, not the ideology, decides (master prompt §16; Phase 8 gate).

## 5. CI & Quality Gates

- GitHub Actions (Planned completion of Phase 1): Python 3.12 matrix; `ruff check`; `pytest -q`; Docker build on tags.
- Coverage target: coordinator core paths ≥ 85% (measured when CI lands).
- Manual QA checklist per phase in the phase's PR description; acceptance criteria in `DEVELOPMENT_PHASES.md` are the gate.
- Bengali + English language quality: evaluation sets run per model registry entry (Phase 2 baseline, Phase 9 formalization) — both languages are mandatory gates per charter §8.
