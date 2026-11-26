# Android Node & Android-First Development

> Status: **Design Implemented (Phase 0)** · Termux worker prototype: Planned Phase 5 · native app: Planned Phase 6. The two Android roles below are independent and separately permissioned.

## 1. Two Roles, One App (never conflated)

| Role | What it does | Default |
|---|---|---|
| **A — AI Client** | chat, research, knowledge browsing, dashboards | on from install; no compute contribution implied |
| **B — Compute Contributor** | voluntarily runs authorized lightweight workloads | **OFF by default; requires explicit opt-in screen** |

Compute participation is never required to use NETMIND (master prompt §11).

## 2. Contributor Requirements (all mandatory before Phase 6 acceptance)

- Explicit opt-in flow with a plain-language summary of what will run.
- Live contribution dashboard: current task (yes/no), CPU %, RAM MB, network data consumed.
- **Pause** and **Stop immediately** controls always visible while contributing.
- Resource limits settable by the user: max CPU %, max RAM, max data/day.
- Battery/thermal policy: contribute only while charging (configurable), stop on thermal warning, respect low-battery threshold.
- Data policy: prefer unmetered connections when configured; never touch personal files (permission model denies storage access to the worker by default).
- OS-legit execution: foreground service with persistent notification while tasks run; WorkManager for deferrable work; **no silent background execution**, no Doze-fighting tricks.

## 3. Realistic Workload Envelope (from research)

Benchmarks and community practice for llama.cpp on Android via Termux ([Termux guides](https://jonathansblog.co.uk/running-local-llms-on-android-with-llama-cpp-in-termux); [llama.cpp android docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md)) support:

- **Embeddings** (bge-m3): feasible on most phones.
- **Document processing / chunking / classification**: feasible.
- **Small-model inference** (Qwen3 0.6B–4B, Q4): feasible when charging + unmetered; speed varies by device.
- **NOT feasible / not attempted:** hosting slices of large models (70B+ layer distribution), long-running GPU work.

This honesty constraint feeds the scheduler: Android nodes only receive task kinds they advertised.

## 4. App Architecture (Phase 6)

- **Stack:** Kotlin, Jetpack Compose, WorkManager, foreground service for active task execution, llama.cpp via JNI bindings (or a bound Termux bridge during Phase 5 prototyping — see ADR-008).
- **Modules:** Identity (keypair in Android Keystore) · Discovery/Connection (outbound WSS to coordinator) · Task Receiver/Executor (sandboxed scratch dir) · Result Publisher · Resource Monitor (battery/thermal/data) · Contribution UI (dashboard + stop switch) · Health Monitor (heartbeat).
- **UI (client role):** Home · AI Chat · Explore · Knowledge · Compute Network · Profile & Settings (master prompt §12); compute dashboard shows connected nodes, types, resources, current tasks, latency, contribution, error rates — public fields only.

## 5. Development From an Android Phone (the owner's primary workflow)

1. **Termux (local):** `pkg install python git` → clone repo → `pytest -q` runs the coordinator's whole test suite on the phone; `uvicorn` serves locally for API testing.
2. **GitHub via phone browser:** commits, PRs, Issues; CI (GitHub Actions) runs lint+tests remotely.
3. **Cloud fallback:** GitHub Codespaces or a small VPS via Termux `ssh` — same env-driven config (`NETMIND_*`), same `docker-compose.yml`.
4. **Browser-accessible admin:** the coordinator's `/docs` (OpenAPI) + a minimal admin route set serve as the first administration interface; the full web interface is Phase 5+.

Commands stay short/copyable by policy (master prompt §11).

## 6. Phase 6 Acceptance (summary)

Register → connect → advertise → receive authorized task → execute → return → dashboard shows usage; pause/stop works instantly; thermal & battery gates demonstrable; **no task runs without the foreground indicator**. Full criteria in `DEVELOPMENT_PHASES.md`.
