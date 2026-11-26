# Known Limitations

> Honest inventory of what does **not** work yet or is bounded. Every item states the constraint and the plan. This file exists so nothing is oversold (charter §19 rule: never leave undocumented placeholder functionality).

## Now (v0.3.0)

1. **Inference runs on adapters, one live-model smoke outstanding.** The execution engine (routing → claim → execute → result) is complete and tested end-to-end with the labeled mock runtime. The llama.cpp adapter (llama-server HTTP) is implemented but has **not** been exercised against a live GGUF model yet — deferred to owner hardware/VPS (no prebuilt wheel and no model download in the dev sandbox; recorded in ADR-013 and CHANGELOG). No test or doc claims real model output anywhere.
2. **Phase 2 remainder:** streaming answers (SSE) not implemented (results are one-shot records); intent detection + Universal Task Planner + response orchestration still open; `/feedback` remains a documented 501.
3. **Single coordinator instance.** Alpha runs one coordinator process; the *design* is state-free + PostgreSQL-backed (ADR-011) but replication is not deployed or tested. It is a single point of failure until Phase 5+.
4. **Worker polling loop (5 s default).** Claim loop is HTTP polling until the Phase 5 WSS channel; fine at Alpha scale, not a long-term design.
5. **Schema via `create_all()`, no Alembic.** Bootstrap schema only (ADR-003); migrations mandatory before multi-node phases. Phase 2 added task execution columns — existing dev SQLite files must be recreated (`rm netmind_dev.db`).
6. **SQLite dev profile is for development/tests only.** No row locks (`FOR UPDATE SKIP LOCKED` is a no-op there) and tz-aware datetimes round-trip naive (engine normalizes); vector features and concurrent writes need PostgreSQL; documented, not hidden.
7. **Rate limiting is per-process.** In-memory token bucket; multi-replica deployments need a shared store (Redis) — deferred deliberately (ADR-002).
8. **Security is partial.** JWT/API-key auth + scrypt hashing + rate limits are in; worker endpoints authenticate with the owner's API key (interim — node-signed envelopes Phase 5); Ed25519 signing, sandboxing, audits are Phase 5+ design-ready only.
9. **Bengali language quality: unmeasured.** Both language gates (BN/EN) are specified; evaluation sets not yet built (Phase 2 baseline).
10. **License and operational defaults await owner ratification.** Apache-2.0, Singapore VPS, Bangla-education domain adopted as working defaults (ADR-012/014) — reversible, but not yet owner-approved.

## Structural / accepted limits (by design, re-checked at named phases)

11. **Mobile compute is light work only** — embeddings, classification, small quantized models. Phones will not host slices of large models; we refuse that default even though it sounds more "distributed".
12. **Distributed ≠ automatically faster/cheaper.** Distribution wins when tasks parallelize and models fit nodes; the benchmark methodology (Phase 8 gate) decides adoption, not ideology.
13. **Volunteer availability is volatile.** Churn, Doze, thermal throttling are treated as normal input, not exceptions — graceful degradation is the requirement (the claim-TTL requeue is the first mechanism; Phase 5's kill-node test is the gate).
14. **Coordinator remains the trust anchor for verification** until Phase 7's reputation/verification research matures; full decentralization of trust is a research goal, not a promise.
15. **No hard real-time guarantees.** Deadlines are enforced, latency is measured, but volunteer networks give statistical, not deterministic, latency.
16. **Legal/licensing surface requires per-model diligence** — registry gate exists (ADR-009), but the owner must sign off on restriction-bearing licenses (e.g., Gemma Terms) case by case.

If any of these becomes a blocker, the alternative is proposed via `DECISIONS.md`, never silently.
