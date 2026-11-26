# Master Architecture

> Status: **Implemented (design) · Phase 0** — this document is the reviewed architecture baseline. Implementation status of each subsystem is labeled inline.

NETMIND AI is a global distributed intelligence network built from five cooperating systems plus a deliberately lightweight coordination layer. The single most important architectural rule:

> **The coordinator coordinates; it does not become the mandatory inference server.**

![NETMIND system architecture](../diagrams/system_architecture.png)

## 1. Design Principles

1. **Task-level distribution first.** One node executes one independent task (a research subtask, an embedding batch, a code evaluation, a reasoning step). Model-layer partitioning (pipeline/tensor parallelism) is an *experimental* Phase 8+ track that must beat task-level distribution in benchmarks before adoption. Precedent: Petals proved layer-distribution across the internet works but delivers single-digit tokens/sec for large models ([github.com/bigscience-workshop/petals](https://github.com/bigscience-workshop/petals) — last commit Aug 2024, effectively dormant).
2. **Coordinator is replicable by design.** All coordinator state lives in PostgreSQL; no coordinator process may keep authoritative state only in memory. This is what allows the coordination layer to be duplicated or moved without a rewrite.
3. **Nodes are untrusted.** Every task package is signed; every result is verified; nodes never receive credentials or unnecessary user data.
4. **Graceful degradation everywhere.** A task must complete even if nodes vanish mid-flight; if no node is available it queues or falls back to a coordinator-local model.
5. **Honest capability labels.** Every subsystem carries one of: Planned / In Progress / Prototype / Experimental / Implemented / Tested / Production Ready.

## 2. System Map

| # | System | Responsibility | Status |
|---|--------|----------------|--------|
| S-01 | **Intelligence Engine** (Intelligence Coordinator) | intent detection, task planning, model routing, agent orchestration, result verification, Universal Knowledge Router | Planned (Phase 2) |
| S-02 | **Knowledge Engine** | ingestion, embedding, vector + full-text search, knowledge graph, source attribution, freshness | Planned (Phase 3) |
| S-03 | **Multi-Model Intelligence** | model registry, routing by capability/latency/license/availability, runtime adapters (llama.cpp/ONNX) | Registry: **Tested** (Phase 1 skeleton); routing: Planned (Phase 2) |
| S-04 | **Distributed Compute Network** | node identity/discovery, capability registry, task scheduling, task-level distribution, fault tolerance | Node registry: **Tested** (Phase 1 skeleton); execution: Planned (Phase 5) |
| S-05 | **Learning & Evaluation** | opt-in feedback, evaluation pipeline, benchmarks (incl. Bengali + English quality), later LoRA/federated | Planned (Phases 9–10) |
| S-06 | **Security & Trust** | Ed25519 node identity, signed tasks/results, sandboxing, abuse detection | Design: Implemented; enforcement: Planned (Phase 5+) |

## 3. Intelligence Engine (S-01)

Modules (all inside the coordinator service; see `TASK_EXECUTION_FLOW.md` for the full 17-step pipeline):

- **Intent Detector** — classifies requests (chat, research, coding, math, translation, vision, knowledge lookup).
- **Universal Task Planner** — estimates complexity, decomposes work, marks parallelizable subtasks, sets deadlines and budgets.
- **Universal Knowledge Router (UKR)** — answers nine questions per request: what the user wants; what is already known; what is missing; which source is relevant; whether live research helps; which model fits; which node fits; how to verify; how to compose the answer. UKR distinguishes known / retrieved / inferred / unverified / time-sensitive information and emits citations for everything external.
- **Agent Orchestrator** — runs specialized agents (Research, Reasoning, Coding, Math, Knowledge Retrieval, Translation, Vision, Verification, Planning, Security) with max execution depth and resource budgets to prevent loops.
- **Result Verifier** — schema validation plus independent re-verification for important results (never trust a result merely because two nodes agree).

## 4. Knowledge Engine (S-02)

Own knowledge infrastructure — not just a wrapper around a search engine. Sources: open educational datasets, public scientific publications, licensed materials, government portals, public APIs, authorized web resources, user-provided documents (explicit permission), community-verified contributions, internal technical docs, and previously approved records.

Hard rules: unverified information is never presented as verified; user documents never enter training data without explicit permission. Full design in `KNOWLEDGE_ENGINE.md`.

## 5. Multi-Model Intelligence (S-03)

A registry — not a hardcoded model. Each record carries identifier, license, capabilities, languages, context length, quantization, memory footprint, runtime, benchmarks, deployment location, availability. Routing prefers specialist models (coding → coding model; math → reasoning model; document search → Knowledge Engine; visual → vision model) and never invokes all models for one request. 2026 starter catalog and memory guidelines: `AI_MODEL_REGISTRY.md`.

## 6. Distributed Compute Network (S-04)

Voluntary node classes: Android, Windows, Linux, macOS, server, optional GPU. Each node has an Ed25519 identity and advertises capabilities (CPU, memory, GPU, runtimes, network quality, current load, availability, coarse region, contribution limits). Mobile participation is strictly opt-in with visible usage and an immediate stop control; battery, thermal and data limits are respected. Wire protocol: `NETWORK_PROTOCOL.md`.

## 7. Learning & Evaluation (S-05)

Improvement loops: approved user feedback, evaluation datasets, model comparisons, benchmark results, knowledge-base upgrades, routing-decision tuning, verified error corrections, controlled fine-tuning (LoRA/QLoRA/distillation). Federated learning only after the network is stable (Phase 9). Never automatic training on user conversations.

## 8. Economics

Volunteer compute first; the project must start without purchasing dedicated AI hardware. Transparent contribution policy: users always see CPU, memory, network data, active tasks, and how to stop. No cryptocurrency mining or hidden extraction; any future reward mechanism must be transparent and legally compliant (contrasting with marketplace models like Golem/Akash, which are payment-based — see `RESEARCH_AND_FEASIBILITY.md`).

## 9. Alpha Topology (Phase 5 target)

![NETMIND Alpha topology](../diagrams/alpha_topology.png)

Three logical nodes (three processes on one machine is acceptable for Alpha), one coordinator, one test client. Acceptance: kill one node mid-task → the task still completes through reassignment; conflicting results are detected and resolved.

## 10. Component Dependencies

![Component dependency graph](../diagrams/dependency_graph.png)

Critical path: Foundation (T-0) → Task Execution (T-2) → Intelligence (T-3) → Node Runtimes (T-5). The Knowledge Engine (T-4) can proceed in parallel with T-3. No component imports from a tier below it; exceptions require an ADR.
