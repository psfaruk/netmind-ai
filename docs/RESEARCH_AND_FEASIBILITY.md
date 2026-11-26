# Research & Feasibility Report (Phase 0)

> Status: **Implemented** · Compiled 2026-11-26 from live web research. All sources listed in §6.

## 1. Existing Systems — What The World Already Has

| System | What it does | Current status | What NETMIND reuses / does differently |
|---|---|---|---|
| **Petals** ([repo](https://github.com/bigscience-workshop/petals), 10.7k★, MIT) | BitTorrent-style distributed LLM inference + fine-tuning; each volunteer serves a slice of transformer layers (pipeline parallelism); public swarms for Llama-3.1-405B etc. | **Dormant** — last commit Aug 25, 2024; last release Sep 2023 | Proof that layer-distribution over the internet works, *and* its measured cost (≈6 tok/s for 70B single-batch) is why NETMIND defaults to **task-level** distribution and treats layer-sharding as experimental (Phase 8) |
| **exo** (exo labs) ([repo](https://github.com/exo-labs/exo)) | Runs LLMs as a cluster across everyday devices (iPhone/iPad/Android/Mac/Linux) | Active-ish; **maturity warnings** — two-node pipeline-deployment failures reported in the community (r/LocalLLaMA, Nov 2026) | Validates "everyday devices as an AI cluster"; we adopt its device breadth but add identity, verification and opt-in controls it lacks for our use case |
| **BOINC** ([boinc.berkeley.edu](https://boinc.berkeley.edu)) | Volunteer computing platform; ~30 science projects; official Android app; decades of node-management practice | Active, battle-tested | The governing precedent that **Android volunteer compute is legitimate**; we copy its consent model (explicit join, visible usage, immediate stop) rather than inventing one |
| **llama.cpp** ([repo](https://github.com/ggml-org/llama.cpp)) | CPU-first GGUF inference; official Android build docs; runs in Termux | Active | The node runtime for CPU workloads — this is what makes "no dedicated GPU purchase" realistic ([Termux guides](https://jonathansblog.co.uk/running-local-llms-on-android-with-llama-cpp-in-termux)) |
| **Flower** ([flower.ai](https://flower.ai)) | Federated learning, framework-agnostic | Active | Phase 9 learning track — do not hand-roll FL |
| **libp2p** ([libp2p.io](https://libp2p.io)) | Modular P2P stack: NAT traversal (hole punching ≈60% with dcUTR), AutoNAT, relay, QUIC/WebRTC transports | Active | Phase 7 transport research for true peer-to-peer; Phase 5 ships on plain secure WebSocket first (simpler, NAT-tolerant via outbound connections) |
| **Golem / Akash** | Marketplaces that *rent* compute for payment | Active | Economic-model contrast only: NETMIND is volunteer-based, no token/mining mechanics (charter §9) |
| **vLLM / Ollama / LM Studio** | Local inference servers | Active | Patterns for serving on optional server/GPU nodes (Phase 5+) |

## 2. Open-Weight Model Landscape (2026, for the registry)

| Model family | Sizes | License | Notes for NETMIND |
|---|---|---|---|
| **Qwen3 / Qwen3.5** ([qwen blog](https://qwenlm.github.io/blog/qwen3)) | 0.6B–235B (+MoE) | **Apache-2.0** | Default general/reasoning line; 100+ languages incl. Bengali-support level worth benchmarking; small sizes fit phones (0.6B–4B) |
| **gpt-oss** (OpenAI) ([HF blog round-up](https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally)) | 20B / 120B | **Apache-2.0**, 128K ctx | Reasoning model for capable nodes (20B ≈ 16 GB RAM) |
| **Gemma 3** | 1B–27B | Gemma Terms (restriction-bearing) | Multimodal (4B+); license reviewed before registry entry |
| **Phi-4** | 14B | MIT | Compact reasoning/coding |
| **Whisper** + **BanglaSpeech2Text** ([repo](https://github.com/shhossain/BanglaSpeech2Text)) | small/medium | MIT | Bengali ASR path — owner language priority |
| **bge-m3** (BAAI) | — | MIT | Multilingual embeddings (100+ langs) for the Knowledge Engine |

Full catalog with memory estimates: `AI_MODEL_REGISTRY.md`.

## 3. Feasibility Verdict

**Feasible with staged scope, with these conditions:**

1. **Task-level distribution is the only defensible default.** Petals-class layer-splitting over WAN gives single-digit tok/s for big models and is now unmaintained; exo reports deployment fragility. Task-level split (whole task per node, small quantized models) is how CPU nodes stay useful.
2. **Android nodes are for light workloads.** Realistic: embeddings, document processing, classification, small (≤4B, Q4) model inference when charging + unmetered. Not: hosting slices of large models.
3. **Coordinator-first networking is fine for Phases 1–6.** Outbound-only WSS from nodes sidesteps NAT traversal; true P2P (libp2p, hole-punching ≈60% success) is Phase 7 research with relay fallback mandatory.
4. **The zero-purchase start is real.** Developer laptop/phone + free-tier VPS + open-weight Apache-2.0 models cover Phases 0–5. No paid infrastructure required until optional server nodes (documented if ever used).
5. **Bengali + English quality gates are measurable** — evaluation sets and the model registry carry language-support fields from day one.

## 4. Risk Register (top 10)

| ID | Risk | Sev | Likelihood | Mitigation |
|---|---|---|---|---|
| R-01 | Coordinator is a single point of failure in Alpha | High | Certain (by design, early) | State-free coordinator + PostgreSQL; replication documented from Phase 1 (ADR-006); P2P scheduler only Phase 7+ |
| R-02 | Untrusted nodes return wrong/malicious results | High | Medium | Signed results, schema validation, independent re-verification for important results; never trust "two nodes agree" |
| R-03 | Mobile OS kills background compute (Doze, thermal) | Medium | High | Foreground services + WorkManager with constraints; participation UI shows live status; treat disconnection as normal (reassignment) |
| R-04 | Cold-start latency (model load per task) hurts UX | Medium | High | Warm-node scheduling preference, model caching on nodes, small-model defaults |
| R-05 | Volunteer churn > capacity | Medium | High | Task queue with priorities; graceful "no node → queue/fallback" path; acceptance tests cover it |
| R-06 | License violation via unvetted models | High | Low (process) | Registry requires license + memory + runtime metadata before availability=true; ADR-009 records vetting rule |
| R-07 | Privacy leak through task payloads | High | Low (process) | Minimum-data task packaging (charter §7); no credentials/tokens to nodes; privacy tests in Phase 10 |
| R-08 | Bandwidth cost of shipping prompts/models | Medium | Medium | Task-level split (KB payloads vs GB weights); models downloaded once per node, content-addressed |
| R-09 | Abuse of public API / free-riding | Medium | Medium | Rate limiting (implemented in skeleton), API keys, abuse metrics; abuse detection Phase 5+ |
| R-10 | Scope creep toward "distributed everything" | High | High | Phase gating with acceptance criteria; Phase 8/9 explicitly experimental with benchmark gates |

## 5. Build-vs-Reuse Decision

**Reuse (don't build):** llama.cpp runtimes, PostgreSQL/pgvector, FastAPI/SQLAlchemy/PyJWT, Flower (Phase 9), libp2p (Phase 7 research), Docker.
**Build (novel for NETMIND):** Universal Knowledge Router, task-level scheduler with signed task packages, node identity/reputation rules, model-routing policy engine, Bengali/English evaluation sets, the Android contributor app UX.

## 6. Sources Consulted (Nov 2026)

- Petals repository — https://github.com/bigscience-workshop/petals (status, stars, last commit, benchmarks)
- exo labs repository — https://github.com/exo-labs/exo; r/LocalLLaMA thread "Exo fails at the last layer when deploying on two nodes" (Nov 2026)
- BOINC — https://boinc.berkeley.edu ; D. P. Anderson, "BOINC: A Platform for Volunteer Computing" (2019); ZDNet BOINC-on-Android coverage
- llama.cpp — https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md ; Termux guides: jonathansblog.co.uk (Oct 2026), nkaushik.in (Jul 2026)
- Qwen3 — https://qwenlm.github.io/blog/qwen3 (Apr 2025) and Qwen3.8 repo (Apache-2.0, 262K ctx)
- Open-weight landscape 2026 — https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally ; https://onyx.app/self-hosted-llm-leaderboard ; vdf.ai Qwen on-premise tiers (Sep 2026)
- BanglaSpeech2Text — https://github.com/shhossain/BanglaSpeech2Text
- Flower — https://flower.ai/docs/framework/tutorial-series-what-is-federated-learning.html
- libp2p — https://libp2p.io ; libp2p NAT-traversal tracking (github.com/libp2p/specs/issues/312); discuss.libp2p.io dcUTR hole-punching ≈60%
- Golem/Akash marketplace overviews (medium.com decentralized GPU cloud round-ups, Nov 2026)

Open questions for the owner (recorded, not blocking): reward/recognition design for contributors; target deployment region for the first coordinator VPS; preferred initial knowledge domain (educational Bangla content vs general).
