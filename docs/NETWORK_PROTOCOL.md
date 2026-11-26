# Network Protocol (Coordinator ↔ Node)

> Status: **Design implemented (Phase 0) · wire implementation Planned for Phase 5.** The Phase 1 skeleton ships the REST surface (`POST /api/v1/nodes/register`, heartbeat) that this protocol builds on.

## 1. Transport Strategy (staged)

| Phase | Transport | Rationale |
|---|---|---|
| 5 (Alpha) | **Secure WebSocket (WSS)**, outbound-only from node → coordinator | TLS everywhere; NAT-friendly (nodes connect out, coordinator never needs inbound to a phone); simplest reliable option |
| 7 (research) | **libp2p over QUIC** with relay fallback | direct P2P, hole punching (~60% success with dcUTR per libp2p community), AutoNAT; relay mandatory fallback |
| 8+ | QUIC/WebRTC data channels for node↔node experiments | only if benchmarked better than coordinator-relayed flow |

Never assume a mobile node can accept direct inbound connections (master prompt §3). All mobile node connections are outbound-initiated.

## 2. Node Lifecycle

```
generate keypair → register(identity, capabilities) ─ heartbeat loop (30 s) ─ receive signed task
     → execute (isolated) → return signed result → ... → deregister / timeout-stale (90 s no beat)
```

1. **Identity.** Node generates an Ed25519 keypair locally; the public key becomes `node_id`. Registration is signed by the node key. Passwords, tokens and private user data never travel to nodes.
2. **Capabilities advertisement.** CPU cores, available RAM, optional GPU, runtimes (`llama.cpp`, `onnx`), context limits, network quality class, current load, availability window, coarse region (country-level only — no fine location), contribution caps (max CPU %, max RAM MB, max data MB/day).
3. **Heartbeat** every 30 s carrying load/health; missing 3 beats ⇒ node marked `stale`, its in-flight tasks are automatically reassignable.
4. **Deregistration** is honored instantly; a node may also simply vanish — the coordinator must cope (task reassignment is the normal path, not an error path).

## 3. Message Envelope (all messages)

```json
{
  "msg_id": "uuid4",
  "type": "task.assignment | task.result | node.heartbeat | node.register | node.deregister | error",
  "ts": "2026-11-26T12:00:00Z",
  "sender": "node_id (Ed25519 pubkey)",
  "signature": "ed25519(payload_bytes)",
  "payload": { }
}
```

Rules: every envelope is signed; unknown types are dropped (forward compatibility); replay is rejected (`msg_id` once-only, 10-min window).

## 4. Task Package (coordinator → node)

```json
{
  "task_id": "uuid4",
  "task_kind": "embedding | inference | retrieval | evaluation | research_subtask",
  "input": { },
  "input_schema": "url",
  "output_schema": "url",
  "model_hint": { "registry_id": "qwen3-1.7b-q4", "required": false },
  "deadline_sec": 120,
  "resource_budget": { "max_ram_mb": 512, "max_cpu_seconds": 90 },
  "idempotency_key": "uuid4",
  "priority": 5
}
```

- **Idempotency/duplicate protection:** `idempotency_key` lets a node safely re-execute a re-delivered task exactly once; coordinator deduplicates on task_id.
- **Timeouts & retries:** `deadline_sec` enforced both sides; retry = reassign to a *different* node (max 2 retries), then queue or fallback.
- **Checkpointing:** long tasks checkpoint every 30 s; a dead node's partial checkpoint can seed a reassignment (Phase 5+).

## 5. Result Message (node → coordinator)

```json
{
  "task_id": "uuid4",
  "status": "ok | failed | partial | refused",
  "result": { },
  "metrics": { "cpu_seconds": 41.2, "ram_peak_mb": 380, "tokens_out": 512 },
  "error": null,
  "signature": "ed25519(...)"
}
```

Verification pipeline (coordinator): schema validation → plausibility checks (metrics vs budget) → for **important** tasks: independent re-run on another node or a trusted evaluator model. Contradictions ⇒ arbitration run or task marked `conflicted` and surfaced honestly to the user.

## 6. Failure Semantics

| Event | Coordinator behavior |
|---|---|
| Node disconnects mid-task | heartbeat gap ⇒ task reassignable; reassignment is normal operation |
| Node returns malformed result | result rejected; node error-counter incremented |
| Two nodes contradict | `conflicted` → arbitration (trusted evaluator) or explicit uncertainty |
| No suitable node available | task stays `queued` (with timeout notice) or falls back to coordinator-local model |
| Model unavailable on node | node refuses (`refused`); scheduler picks another node/model pair |
| Node exceeds resource budget | task killed node-side; coordinator sees `partial` + budget-exceeded error |

Full matrix with test IDs: `TESTING_STRATEGY.md` §3.

## 7. Privacy & Security Rules

- TLS is mandatory on every hop (WSS/QUIC); task payloads carry **only** the minimum data the task needs.
- Nodes are untrusted: signed envelopes, rate-limited ingestion, input/output schema enforcement, isolated execution (Docker sandbox on servers; process isolation + Android WorkManager constraints on phones).
- Privacy-preserving logging: no user prompt content in logs at default level (Phase 10 adds scrubbers/retention policy).
- Reputation: reliability score from verified outcome ratio only — deliberately simple, not currency-like (charter §7).
