# Security Architecture

> Status: **Design Implemented (Phase 0)** · Phase 1 skeleton implements: JWT auth, scrypt password hashing, API-key auth, rate limiting. Everything else below is Planned with the phase named.

## 1. Threat Model (nodes are UNTRUSTED)

| Threat | Vector | Control |
|---|---|---|
| Malicious node returns crafted result | task execution | signed results, schema validation, independent re-verification for important tasks, reliability counters |
| Node impersonation / Sybil | registration | Ed25519 challenge-response at registration; one node per device key; Sybil-resistant reputation (reliability-based, not payment-based) |
| Payload tampering in transit | network | TLS (WSS/QUIC) + envelope signatures end-to-end |
| Prompt/user-data leakage to nodes | task packaging | minimum-data rule: tasks carry only what the subtask needs — never passwords, tokens, or unrelated context |
| Arbitrary code execution on coordinator | "node-submitted code" | **never** executed on the coordinator; code execution runs sandboxed on nodes/evaluators only |
| Abuse of public API | spam/scraping | rate limiting per key (implemented), quota tiers, abuse metrics (Phase 5+) |
| Malicious model artifact | model distribution | content-addressed weights (SHA-256 verified by nodes before load), registry license vetting |
| Replay/reordering | protocol | msg_id once-only window, monotonic sequence per node |
| Coordinated wrong-answer collusion | multiple nodes agreeing | **never trust N-agreeing** — important results use independent verification or trusted evaluators |
| Privacy leakage via logs | observability | no prompt content at default log level; retention policy Phase 10 |

## 2. Identity

- **Users:** email + password (scrypt-hashed), JWT access tokens (short-lived) + API keys (hashed at rest) for programmatic access. Implemented in Phase 1.
- **Nodes:** Ed25519 keypair generated on-device; `node_id` = public key. Registration and every message signed. Challenge-response at registration proves key possession.
- **Coordinator→node:** task packages signed by the coordinator's Ed25519 key so nodes can reject forged assignments.

## 3. Task Data Minimization

A task package contains: input data needed **for that subtask only**, schemas, budget, deadline, idempotency key. It never contains: user credentials, other users' data, full conversation history (only the minimal context slice), or anything the subtask does not need.

## 4. Execution Isolation

- Server nodes: one Docker container per task invocation, network-restricted, CPU/memory capped (cgroups).
- Developer nodes: process isolation + filesystem allowlist for scratch space.
- Android nodes: WorkManager constraints + app-private scratch; no personal-file access (permission model denies it by default).
- Code produced by agents is executed **only** in these sandboxes; the coordinator never runs node-submitted code.

## 5. Availability Controls

- Rate limiting per API key (token bucket, implemented in the skeleton).
- Node admission control: coordinator caps concurrent tasks per node by its *advertised* limits.
- Abuse detection (Phase 5+): anomaly scoring on failure patterns, malformed-result rate, heartbeat irregularity.
- Secure update path: node software updates signed; update manifest versioned (Phase 6+).

## 6. Reputation & Verification Policy

- Reputation = function of **verified outcome ratio** (validated results / attempted), decayed over time; used for scheduling preference, never as payment.
- Important results ⇒ independent verification: re-run on a second disjoint node, or evaluation by a trusted coordinator-side model; contradictions escalate to arbitration.
- Reputation is deliberately simple and transparent; complex token-economics are out of scope (charter §9).

## 7. Cryptographic Inventory

| Purpose | Primitive |
|---|---|
| Password hashing | scrypt (stdlib; N=2^15, r=8, p=1) — ADR-006 upgrade path to argon2 |
| User auth tokens | JWT HS256, `NETMIND_JWT_SECRET`, 30-min expiry |
| Node/coordinator identity | Ed25519 (sign/verify) — Planned Phase 5 |
| Payload integrity | SHA-256 content addressing for artifacts |

## 8. Security Test Gate (Phase 10)

The security audit checklist: auth bypass attempts, token replay, envelope forgery, sandbox escape probes, rate-limit efficacy, minimum-data leakage inspection, log content review, dependency CVE sweep. All must pass before Production Ready.
