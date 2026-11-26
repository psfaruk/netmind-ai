# AI Model Registry

> Status: **Registry schema + seed data: Implemented & Tested (Phase 1 skeleton)** · runtime deployment: Planned (Phase 2). Registry rows below describe real open-weight models from 2026 research (`RESEARCH_AND_FEASIBILITY.md` §2); `availability=false` everywhere until a runtime is verified — no model is assumed available (charter rule #4).

## 1. Registry Record Schema

| Field | Type | Notes |
|---|---|---|
| `id` | string | registry key, e.g. `qwen3-1.7b-q4` |
| `name` / `version` | string | upstream identity |
| `license` | string | must be verified (Apache-2.0, MIT, Gemma Terms…) before `availability=true` |
| `capabilities` | array | `chat, reasoning, coding, embeddings, vision, speech, translation` |
| `languages` | array | incl. Bengali support quality: `native / partial / untested` |
| `context_length` | int | tokens |
| `quantization` | string | `Q4_K_M`, `Q8_0`, `f16`… |
| `memory_requirement_mb` | int | measured, not guessed |
| `runtimes` | array | `llama.cpp`, `onnx` |
| `benchmark_refs` | array | evaluation-set scores (populated by S-05) |
| `deployment_location` | string | node id / `coordinator-local` / `none` |
| `availability` | bool | **false until runtime verified on an actual node** |

Implemented as table `model_registry` in Phase 1 (`DATABASE_SCHEMA.md`).

## 2. Starter Catalog (seed data, verified against Nov 2026 sources)

| Registry id | Model | License | Role in NETMIND | Min RAM (approx, Q4) |
|---|---|---|---|---|
| `qwen3-0.6b-q4` | Qwen3 0.6B | Apache-2.0 | phone-class chat/fallback | ~0.6 GB |
| `qwen3-1.7b-q4` | Qwen3 1.7B | Apache-2.0 | default CPU chat on laptops | ~1.2 GB |
| `qwen3-4b-q4` | Qwen3 4B | Apache-2.0 | balanced CPU node model | ~2.6 GB |
| `qwen3-8b-q4` | Qwen3 8B | Apache-2.0 | strong CPU/server node | ~5 GB |
| `gpt-oss-20b-q4` | gpt-oss 20B | Apache-2.0 | reasoning on capable nodes | ~12–16 GB |
| `phi-4-14b-q4` | Phi-4 | MIT | compact reasoning/coding | ~9 GB |
| `gemma3-4b-q4` | Gemma 3 4B (multimodal) | Gemma Terms | vision+text — license reviewed first | ~2.6 GB |
| `whisper-small` | Whisper | MIT | speech → text (incl. Bengali) | ~1 GB |
| `banglaspeech2text` | BanglaSpeech2Text (Whisper ft) | MIT | Bengali ASR | ~1 GB |
| `bge-m3` | bge-m3 embeddings | MIT | Knowledge Engine embeddings, multilingual | ~2 GB |

Memory figures are planning estimates pending measured values (rule: registry stores *measured* memory once a node reports it). 2026 landscape references: Qwen3 family 0.6B–235B under Apache-2.0 ([qwenlm.github.io](https://qwenlm.github.io/blog/qwen3)); gpt-oss-20b/120b Apache-2.0 128K ([HF round-up](https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally)); Gemma 3 1B–27B multimodal; Phi-4 MIT; BanglaSpeech2Text ([repo](https://github.com/shhossain/BanglaSpeech2Text)); bge-m3 (BAAI, MIT).

## 3. Routing Rules (S-03)

1. **Never invoke every model for a request.** The router picks by: required capabilities → language needs → task size → node memory available → latency budget → license class.
2. Specialization defaults:
   - coding request → coding-capable model (Qwen3/Phi-4 class)
   - hard math/reasoning → reasoning model (gpt-oss class, if a capable node exists; else Qwen3 thinking mode)
   - document/knowledge search → Knowledge Engine retrieval + small composer model
   - image input → vision-capable model (Gemma 3 4B+ class)
   - Bengali ASR → `banglaspeech2text` / `whisper`
   - embeddings → `bge-m3`
3. **Fallback ladder:** specialist → general small model → coordinator-local fallback → queue with notice. Router logs *why* each hop was taken (auditable routing decisions).
4. Cost/energy weighting: prefer warm nodes (model already loaded) — cold-start can dominate total latency on CPU nodes.

## 4. License & Verification Rules

- A model row can only flip `availability=true` after: license text reviewed and recorded; weights fetched from the official source; runtime executes a smoke prompt on a registered node; memory measured. (Charter rules #4, #11.)
- Quantization: default `Q4_K_M`; `Q8` for evaluation-sensitive tasks. GGUF via llama.cpp; ONNX only where llama.cpp is unavailable.
- Weight distribution to nodes: content-addressed (SHA-256), download from official upstream or coordinator object store; nodes verify the digest before loading (model artifact verification, charter §7).

## 5. Evaluation Hooks (S-05, Phase 9–10)

Registry rows reference benchmark entries: answer accuracy, reasoning quality, coding performance, latency (p50/p95), resource consumption, reliability, **Bengali language quality**, **English language quality** — the two language gates are mandatory per the master prompt §8.
