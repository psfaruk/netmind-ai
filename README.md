# NETMIND AI

**A distributed AI network powered by volunteer devices — and an Android app that runs 100% on your own phone.**

[![Build APK](https://github.com/psfaruk/netmind-ai/actions/workflows/android-build.yml/badge.svg)](https://github.com/psfaruk/netmind-ai/actions/workflows/android-build.yml)
[![Coordinator tests](https://github.com/psfaruk/netmind-ai/actions/workflows/coordinator-tests.yml/badge.svg)](https://github.com/psfaruk/netmind-ai/actions/workflows/coordinator-tests.yml)

> **Core policy:** no vendor model API. No OpenAI, Anthropic, Google or any
> other company's inference service is contacted. All inference runs locally
> with [llama.cpp](https://github.com/ggml-org/llama.cpp) on open-weight
> GGUF models (Apache-2.0). The app works fully offline after the one-time
> model download.

---

## Install on your Android phone / ফোনে ইনস্টল

**English**

1. Go to [Releases](https://github.com/psfaruk/netmind-ai/releases) and download the latest `NETMIND-Node-v*.apk`.
2. Open it on your phone and allow "install from unknown sources" when asked.
3. Open **NETMIND AI** → *Chat* tab → **Prepare model** → the default open-weight model (~400 MB) downloads once.
4. Chat, manage local tasks, and inspect your device's node profile — all offline.

**বাংলা**

1. [Releases](https://github.com/psfaruk/netmind-ai/releases) পেজ থেকে সর্বশেষ `NETMIND-Node-v*.apk` ডাউনলোড করুন।
2. ফোনে খুলে "unknown sources" অনুমতি দিন — ইনস্টল হবে।
3. **NETMIND AI** অ্যাপ খুলুন → *Chat* ট্যাব → **Prepare model** → ডিফল্ট ওপেন-ওয়েট মডেল (~400 MB) একবার ডাউনলোড হবে।
4. এরপর সম্পূর্ণ অফলাইন: চ্যাট, লোকাল টাস্ক ম্যানেজমেন্ট, নোড প্রোফাইল — কোনো সার্ভার বা কোম্পানির মডেল ছাড়াই।

Requirements: Android 9+ (API 28), arm64 phone (or x86_64 emulator), ~2 GB free RAM.

Every push to `main` is built by GitHub Actions; tagged versions (`v*`) are published as GitHub Releases automatically.

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
  (Qwen3-0.6B Q4_K_M default, or Qwen2.5-0.5B-Instruct), download it once
  in-app, then generate completely offline with streaming tokens.
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
