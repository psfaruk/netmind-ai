# Task Execution Flow

> Status: **Pipeline specification Implemented (Phase 0)** · orchestration engine Planned (Phase 2). Phase 1 skeleton persists tasks through the first three states only (see §4).

![Universal Task Planner — execution pipeline](../diagrams/task_execution_flow.png)

## 1. The 17 Steps (single source of truth)

| # | Step | Owning module | Phase |
|---|------|---------------|-------|
| 1 | Receive request | API `POST /api/v1/tasks` | 1 ✅ |
| 2 | Analyze intent | Intent Detector (S-01) | 2 |
| 3 | Identify task type | Intent Detector | 2 |
| 4 | Estimate complexity | Task Planner | 2 |
| 5 | Identify required knowledge | UKR | 2 |
| 6 | Decide live research | UKR + Research Agent | 4 |
| 7 | Select AI models | Model Router (S-03) | 2 |
| 8 | Decompose complex work | Task Planner | 2 |
| 9 | Mark parallelizable tasks | Task Planner | 2 |
| 10 | Find suitable compute nodes | Scheduler (S-04) | 5 |
| 11 | Assign tasks | Scheduler (signed packages) | 5 |
| 12 | Execute tasks | Node runtime | 5 |
| 13 | Collect intermediate results | Coordinator | 5 |
| 14 | Validate outputs | Result Verifier | 5 |
| 15 | Resolve contradictions | Verifier + arbitration | 5 |
| 16 | Generate final response | Composer (streaming) | 2 |
| 17 | Store permitted feedback metadata | Feedback store (opt-in) | 2 |

## 2. Task State Machine

```
SUBMITTED → QUEUED → PLANNED → DISPATCHED → RUNNING → VALIDATING → COMPLETED
                                    ↓           ↓          ↓
                                 REASSIGNED   FAILED   CONFLICTED → (arbitration → COMPLETED/FAILED)
any state → CANCELLED (user), EXPIRED (deadline)
```

Phase 1 skeleton implements `SUBMITTED → QUEUED → CANCELLED/EXPIRED` persistence; the rest arrive with Phases 2 and 5.

## 3. Scheduling Rules (S-04)

1. **Match, don't wish:** a task is dispatched only to nodes whose *advertised* capabilities (runtime, free RAM, availability) satisfy the task's resource budget. No suitable node ⇒ task stays `QUEUED` with a timeout notice (graceful, not an error).
2. **Warm-first:** prefer nodes with the model already loaded; cold starts are a scheduling cost, not free.
3. **Priorities:** interactive (user waiting) > batch research > background maintenance; priority is explicit in the task package.
4. **Retry policy:** failure/timeout ⇒ reassign to a *different* node (max 2 retries) ⇒ then fallback to coordinator-local model or `FAILED` with honest reason.
5. **Duplicate protection:** `idempotency_key` + task-level dedup; the same logical task never runs twice concurrently.
6. **Checkpointing:** long tasks checkpoint every 30 s to survive reassignment.
7. **Cancellation propagation:** user cancel reaches nodes (best-effort) and always stops further dispatch.

## 4. What Phase 1 Delivers vs. Promises

The skeleton's `POST /api/v1/tasks` **persists** a task (validated, authenticated, priority, deadline) and returns its state; **no execution happens yet** — there is no model runtime in Phase 1, and the API response says exactly that (`detail: "task queued; execution engine arrives in Phase 2"`). This is deliberate: no fake AI responses (charter rule #3).

## 5. Failure Matrix (full test matrix in `TESTING_STRATEGY.md`)

| Scenario | Required behavior |
|---|---|
| Node disconnects mid-execution | heartbeat gap → task reassignable → completes elsewhere |
| Node returns wrong result | verification catches schema/quality violation → rejected, error counter |
| Two nodes disagree | `CONFLICTED` → arbitration or explicit uncertainty surfaced |
| No suitable node | queue + timeout notice, never an exception to the user |
| Model unavailable | node `refused` → router picks alternate model/node pair |
| Knowledge stale | TTL miss → research refresh or dated answer with timestamps |
| Latency spike | deadline enforcement, partial results acceptable for some kinds |
| User cancels | state `CANCELLED`, nodes notified, resources freed |
| Node exceeds budget | node-side kill, `partial` + budget-exceeded reason |

## 6. Anti-Patterns (banned by design)

- Distributing model layers across phones by default (Petals-style) — Phase 8 experimental only, benchmark-gated.
- Invoking every model for every request.
- Retrying on the same failing node forever.
- Presenting a `conflicted` result as clean.
