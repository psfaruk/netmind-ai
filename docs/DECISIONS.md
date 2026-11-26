# Decisions (ADR Log)

> Architecture Decision Records. Every architectural change follows the charter §18 process: propose → rationale → affected components → security/perf impact → update docs → implement+test → record.

**ADR-001 · Task-level distribution first; layer-sharding experimental only** *(Nov 2026)*
Context: Petals demonstrated internet-scale layer/pipeline distribution but measured single-digit tok/s for large models and is dormant since Aug 2024 ([repo](https://github.com/bigscience-workshop/petals)); exo (device clusters) reports deployment fragility in 2026.
Decision: NETMIND's default is whole-task-per-node with small quantized models. Model sharding/pipeline parallelism enters only as benchmark-gated Phase 8 experiments.
Consequences: realistic CPU/phone value; gives up "run 100B on phones" narrative; network payloads stay KB-scale.

**ADR-002 · Coordinator: FastAPI + SQLAlchemy 2 async + PostgreSQL (SQLite dev profile)** *(Nov 2026)*
Decision: one Python service, async ORM, two DB profiles via env config; Redis deferred (task-table polling suffices at Alpha scale).
Consequences: smallest reliable stack; SQLite dev lets the owner develop from Termux with zero servers; production parity via docker-compose.

**ADR-003 · `create_all()` bootstrap now; Alembic mandatory before Phase 5** *(Nov 2026)*
Decision: schema bootstrap via metadata create in Phase 1 for speed; Alembic required once multi-process/multi-node deployments begin.
Consequences: documented tech debt with a hard deadline; no silent schema drift allowed afterward.

**ADR-004 · Phase 5 transport = secure WebSocket (outbound from nodes); libp2p research deferred to Phase 7** *(Nov 2026)*
Decision: nodes dial out over WSS; no inbound to phones. libp2p/QUIC (hole punching ~60% + relay) studied later for true P2P.
Consequences: NAT problem sidestepped for Alpha; coordinator remains the meeting point (acceptable while it is replicable).

**ADR-005 · GGUF/llama.cpp as the node inference runtime; CPU-first** *(Nov 2026)*
Decision: quantized GGUF via llama.cpp on CPU; official Android support and Termux operation documented by upstream. vLLM only for optional server/GPU nodes later.
Consequences: models must exist in GGUF (catalog constraint); ONNX kept as secondary adapter.

**ADR-006 · Password hashing: scrypt (stdlib) now, argon2 when wheels are convenient** *(Nov 2026)*
Decision: hashlib.scrypt (memory-hard) avoids native-wheel failures on Termux; argon2-cffi swap recorded as a later hardening item.
Consequences: no dependency risk on the owner's phone-first workflow; documented upgrade path.

**ADR-007 · Vectors: pgvector first; Qdrant only beyond ~10M chunks** *(Nov 2026)*
Decision: fewer moving parts at Alpha; Qdrant migration documented in `KNOWLEDGE_ENGINE.md` when scale demands.
Consequences: one database to operate; retrieval scale ceiling acknowledged.

**ADR-008 · Android: Termux worker prototype before native app** *(Nov 2026)*
Decision: Phase 5 validates the node protocol with a Termux-based Python worker on the owner's phone; the Kotlin/Compose app (Phase 6) then wraps proven behavior with proper foreground-service UX.
Consequences: protocol proven cheaply; app development starts from a working reference.

**ADR-009 · Model registry is license-gated** *(Nov 2026)*
Decision: registry rows carry license + memory + runtime metadata; `availability` stays false until a verified runtime smoke-test passes on a registered node. License-restricted families (e.g. Gemma Terms) require an explicit owner sign-off entry before use.

**ADR-010 · Volunteer economics; no tokens** *(Nov 2026)*
Decision: contribution is volunteer-based and fully transparent (visible usage, stop switch); no cryptocurrency mining, no token issuance. Any future reward mechanism: transparent + legally reviewed, per charter §9.

**ADR-011 · Coordinator state-free design** *(Nov 2026)*
Decision: coordinator holds no authoritative in-memory state; everything persisted in PostgreSQL so the process can be replicated or restarted freely. This is the path to decentralized coordination later without a rewrite.

**ADR-012 · Repository license: Apache-2.0** *(Nov 2026, adopted as default — owner ratification pending)*
Context: Phase 2 needed the license settled to accept third-party contributions and to mirror the model licenses (Qwen3 family is Apache-2.0).
Decision: Apache-2.0 — permissive for volunteer contributors, compatible with every catalog model license in use, patent grant included.
Consequences: sign-off entry remains open in the review doc; owner may override to MIT without architectural impact.

**ADR-013 · Phase 2 execution: pull-based claim/submit with claim TTL; runtime adapters** *(Nov 2026)*
Decision: workers poll `POST /workers/claim` (priority + FIFO, `FOR UPDATE SKIP LOCKED` on PostgreSQL) and push results to `/workers/results`; expired claims (TTL 120 s) requeue with attempts cap 3. Inference backends implement `InferenceRuntime.generate()` — MockRuntime for CI (labeled, no fake output), LlamaCppRuntime (llama-server HTTP, OpenAI-compatible) for real nodes.
Consequences: protocol stays HTTP-only until Phase 5's WSS channel; one execute path is testable end-to-end without any model download; SQLite dev profile documented as lock-free (single-process only); late results for expired claims are rejected (409) to protect the new claimant.

**ADR-014 · Operational defaults for Phase 2→3: Singapore VPS; Bangla education first knowledge domain** *(Nov 2026, adopted as defaults — owner ratification pending)*
Decision: first coordinator VPS in Singapore (best Bangladesh latency/price balance among provider options; closer regions lack the provider mix), first knowledge-engine domain = Bengali educational content (NCTB-adjacent open materials), aligning with the Bangla ASR/Whisper research path.
Consequences: both are reversible operational choices, not architecture; recorded here because the roadmap dates depend on them. Owner override = new ADR, no code impact.
