# NETMIND AI

**A distributed AI network powered by volunteer devices — and an Android app that runs 100% on your own phone.**

[![Build APK](https://github.com/psfaruk/netmind-ai/actions/workflows/android-build.yml/badge.svg)](https://github.com/psfaruk/netmind-ai/actions/workflows/android-build.yml)
[![Coordinator tests](https://github.com/psfaruk/netmind-ai/actions/workflows/coordinator-tests.yml/badge.svg)](https://github.com/psfaruk/netmind-ai/actions/workflows/coordinator-tests.yml)

> **Core policy:** no vendor model API. No OpenAI, Anthropic, Google or any
> other company's inference service is contacted. All inference runs locally
> with [llama.cpp](https://github.com/ggml-org/llama.cpp) on open-weight
> GGUF models (Gemma terms / Apache-2.0). The app works fully offline after
> the one-time model download.

---

## Install on your Android phone / ফোনে ইনস্টল

**English**

1. Go to [Releases](https://github.com/psfaruk/netmind-ai/releases) and download the latest `NETMIND-Node-v*.apk`.
2. Open it on your phone and allow "install from unknown sources" when asked.
3. Open **NETMIND AI** → tap the status chip once → the default open-weight model (Gemma 3 4B, ~2.4 GB — real বাংলা & 140+ languages) downloads once and loads automatically. Prefer a tiny model? Pick *Qwen3-0.6B (~484 MB)* in the layers-icon model picker.
4. Chat (with live Deep-Think indicator, streaming, copy, stats), manage local tasks, and inspect your device's node profile — all offline.

**বাংলা**

1. [Releases](https://github.com/psfaruk/netmind-ai/releases) পেজ থেকে সর্বশেষ `NETMIND-Node-v*.apk` ডাউনলোড করুন।
2. ফোনে খুলে "unknown sources" অনুমতি দিন — ইনস্টল হবে।
3. **NETMIND AI** অ্যাপ খুলুন → উপরের স্ট্যাটাস চিপে একবার ট্যাপ করুন → ডিফল্ট ওপেন-ওয়েট মডেল (Gemma 3 4B, ~2.4 GB — আসল বাংলা + ১৪০+ ভাষা) একবার ডাউনলোড হয়ে নিজেই লোড হবে। ছোট মডেল চাইলে লেয়ার্স-আইকনের মডেল পিকার থেকে *Qwen3-0.6B (~484 MB)* বেছে নিন।
4. এরপর সম্পূর্ণ অফলাইন: চ্যাট (লাইভ Deep-Think ইন্ডিকেটর, স্ট্রিমিং, কপি, স্ট্যাটস), লোকাল টাস্ক, নোড প্রোফাইল — কোনো সার্ভার বা কোম্পানির মডেল ছাড়াই।

Requirements: Android 9+ (API 28), arm64 phone (or x86_64 emulator). Default
Gemma 3 4B model needs ~4 GB free RAM; the light Qwen3-0.6B option needs ~2 GB.

Every push to `main` is built by GitHub Actions; tagged versions (`v*`) are published as GitHub Releases automatically.

### v0.2.0-alpha.1 (Claude-style app)

The big app overhaul — the chat experience was rebuilt:

- **মডেল/Model:** default changed to **Gemma 3 4B** — the first phone-sized
  open-weight model with genuinely good **বাংলা** (Bengali) and 140+
  languages (validated: fluent structured Bangla answers, no repetition
  loops). Qwen3-0.6B stays as the light "Deep Think" option. Existing
  installs that already have the Qwen file keep using it (no forced re-download).
- **Deep Think:** Qwen3 reasoning is now ON by default with a live
  "Thinking · N tokens" row (Claude extended-thinking UX) instead of hidden
  blank time; toggle it off for instant replies. Sampling follows Qwen3's
  thinking-mode recommendation (temp 0.6 / top_p 0.95 / top_k 20).
- **Answers are deeper & longer:** new multilingual system prompt (mirror the
  user's language, structured full answers) + max generation 512 → 1024 tokens.
- **New UI:** warm cream + coral "studio" theme (day/night), serif wordmark,
  welcome screen with greeting + 4 suggestion cards, Claude-style message
  bubbles with avatar and per-message stats (thought/answered tokens, tok/s),
  copy action, rounded input dock with send/stop morph, model auto-load —
  no more "Prepare model" button (the status chip drives download/load).
- Fixed alpha.2 leftovers: thinking-mode repetition loops, empty replies.

### v0.1.0-alpha.2 (bug-fix release)

If `alpha.1` seemed to "hang" after sending a message (blank reply), install `alpha.2`:

- **Blank bubble for 15-60 s:** the Qwen3-0.6B model always runs a long hidden
  "thinking" phase before answering, and the app was stripping it from the UI
  entirely — so nothing visible happened for up to a minute on phones.
  alpha.2 sends Qwen3's documented `/no_think` switch with every prompt, so
  answers start streaming immediately, and shows a live
  "Generating — N tokens, X tok/s" indicator plus a "…" placeholder.
- **Qwen3 sampling:** temp 0.3 → 0.7, top_p 0.95, top_k 20 (Qwen3's
  recommended settings) — low temperature caused repetition loops.
- **UI covered by system bars:** edge-to-edge was enforced without insets
  padding, so the status row sat under the status bar and the input row
  under the gesture nav bar. Insets are now applied (status / nav / IME).
- **Engine race:** "Prepare model" could fail with a state error if pressed
  right after app start; loading now waits for engine init (30 s cap).
- Context size 8192 → 4096 (halves RAM pressure on low-end phones).

## What is in this repository

| Path | Contents |
| --- | --- |
| `android/` | **NETMIND Node** — the installable Android app (Kotlin + llama.cpp binding) |
| `services/coordinator/` | Phase 1 coordinator API skeleton (FastAPI, JWT auth, node registry, task queue) with pytest suite |
| `docs/` | Phase 0 research & architecture documents (18 docs) |
| `scripts/` | `fetch-llama.sh` — pins the llama.cpp release used by CI and local builds |
| `.github/workflows/` | `android-build.yml` (APK → artifact → release), `coordinator-tests.yml` (pytest) |

## The Android app (`android/`)

Three sections in one offline app:

- **Chat** — local LLM chat via llama.cpp. Pick a preset open-weight model
  (Gemma 3 4B default — বাংলা/140+ languages; or Qwen3-0.6B with Deep
  Think), download it once in-app, then generate completely offline with
  streaming tokens.
- **Tasks** — a local task manager (SQLite, on-device only).
- **Node** — this device's profile as a NETMIND volunteer node (CPU cores,
  RAM, battery, storage, model status).

Any other GGUF file can be imported from storage or fetched from a custom URL.
The binding module (`android/lib`) is derived from the official
`examples/llama.android` binding in llama.cpp (see `NOTICE`), with
runtime CPU-variant detection (SME2 on Arm, AMX on x86) kept intact.

### Building locally

```bash
bash scripts/fetch-llama.sh android/lib/src/main/cpp/llama.cpp
cd android && ./gradlew assembleRelease
# APK: android/app/build/outputs/apk/release/app-release.apk
```

Requires JDK 17, Android SDK 36, NDK 29.0.13113456, CMake 3.31.6 — the same
set the CI workflow installs.

## Architecture (summary)

NETMIND's long-term design is documented in `docs/MASTER_ARCHITECTURE.md`,
`docs/DEVELOPMENT_PHASES.md` and `docs/ROADMAP.md`-style phase documents:
volunteer devices donate compute; a stateless coordinator matches tasks to
nodes; knowledge is stored in pgvector. This repository's Android node is
the Phase A deliverable — a standalone offline node that will later register
with the coordinator (see `docs/NETWORK_PROTOCOL.md`). The `docs` folder
carries the full Phase 0 decisions, feasibility research, risk registry, and
the three-node Alpha topology design.

## Security & privacy

- The app declares only the `INTERNET` permission (used solely for the
  user-triggered model download and custom URL fetch).
- No analytics, no telemetry, no crash reporting, no vendor APIs.
- Release APK is signed with an alpha self-signed keystore committed in-repo
  (`android/netmind-alpha.jks`) so sideload updates keep a stable signature.
  Rotate it before any production use.

## License

Apache-2.0 (see `LICENSE` and `NOTICE` for third-party credits: llama.cpp is
MIT-licensed; model weights are downloaded at runtime under their own
Apache-2.0 terms and are not redistributed here).
