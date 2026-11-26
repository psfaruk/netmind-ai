# Worker Node Guide

> How to run a NETMIND worker: join the network as a volunteer compute node, claim tasks, execute them. Android (Termux), Linux, macOS, Windows all work — CPU only for now.

## 1. Requirements

- Python 3.11+ (Termux: `pkg install python`)
- A coordinator to talk to (`http://<host>:8000`, dev profile runs on SQLite)
- Your API key (create one via `/api/v1/auth/api-keys` — the node owner's key)
- For real inference: a `llama-server` with a GGUF model (§4); for testing: nothing at all (mock runtime)

## 2. Quick start (mock runtime — proves the pipeline, no model)

```bash
cd services/worker
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

export NETMIND_COORDINATOR_URL=http://127.0.0.1:8000
export NETMIND_API_KEY=nm_...            # node owner's key
export NETMIND_RUNTIME=mock              # honest mock — output labeled as mock
export NETMIND_STATE_DIR=~/.netmind      # keeps node identity stable across restarts

uvicorn worker.main:app --port 8090
```

The worker registers, heartbeats, claims queued tasks matching its advertised models, executes them on the mock runtime and submits results. Check:

```bash
curl http://localhost:8090/health     # node id, runtime, coordinator
curl http://localhost:8090/status      # advertised models, hardware, counters
curl -X POST http://localhost:8090/local-generate \
  -H 'content-type: application/json' -d '{"prompt":"hi"}'   # runtime sanity
```

## 3. Configuration (env, prefix `NETMIND_`)

| Variable | Default | Meaning |
|---|---|---|
| `COORDINATOR_URL` | `http://127.0.0.1:8000` | coordinator base URL |
| `API_KEY` | — (required live) | node owner's API key |
| `NODE_ID` | auto-generated, persisted | stable identity (`netmind_node_id.txt` in `STATE_DIR`) |
| `RUNTIME` | `mock` | `mock` or `llamacpp` |
| `LLAMA_SERVER_URL` | `http://127.0.0.1:8081` | llama-server base URL |
| `WORKER_MODELS` | derived | comma-separated advertised model ids (mock: full text list; llamacpp: `qwen3-0.6b-q4`) |
| `POLL_INTERVAL_SEC` | `5` | claim loop cadence |
| `HEARTBEAT_INTERVAL_SEC` | `30` | heartbeat cadence |
| `AUTO_START` | `true` | start the loop at boot (requires `API_KEY`) |

## 4. Real inference: llama.cpp (llama-server + GGUF)

ADR-005: quantized GGUF on CPU via llama.cpp. Terminal/Termux path:

```bash
# 1) get llama.cpp — Termux: pkg install llama-cli (or build from source)
# 2) download a licensed GGUF (Apache-2.0 model, ~0.5 GB):
#    e.g. Qwen3-0.6B Q4_K_M from a GGUF mirror of the official release
# 3) serve it (OpenAI-compatible):
llama-server -m Qwen3-0.6B-Q4_K_M.gguf --host 127.0.0.1 --port 8081 -c 4096

# 4) point the worker at it:
export NETMIND_RUNTIME=llamacpp
export NETMIND_LLAMA_SERVER_URL=http://127.0.0.1:8081
export NETMIND_WORKER_MODELS=qwen3-0.6b-q4
uvicorn worker.main:app --port 8090
```

Sanity first, network second:

```bash
curl -X POST http://localhost:8090/local-generate \
  -H 'content-type: application/json' \
  -d '{"prompt":"Say hello in Bengali.", "model_id":"qwen3-0.6b-q4"}'
```

`LlamaCppRuntime` speaks `/v1/chat/completions` and reports `backend:"llama.cpp"` with token accounting in every task result — results are attributable to a real backend or a labeled mock, never anything in between.

## 5. What a task looks like

Worker-side execution contract (`input` field of a claimed task):

```json
{
  "messages": [{"role": "user", "content": "Explain distributed computing in one sentence."}],
  "max_tokens": 256,
  "temperature": 0.7
}
```

Flat forms `{"prompt": "..."}` / `{"text": "..."}` are accepted too (converted to one user message). Result records carry `output`, `backend`, `model_id`, `tokens`, `duration_ms`.

## 6. Reliability behavior you should know

- **Claim TTL (120 s default):** if your worker dies mid-task, the coordinator requeues the task after the TTL; your late result is rejected with 409 (another worker may own it by then).
- **Attempts cap (3):** a task whose claims expire 3 times fails permanently with an honest error.
- **Heartbeats** keep the node `active` in listings; missing heartbeats only mark state, never kill work by themselves.
- Participation is explicit: the worker runs only as long as this process runs — no daemons, no silent background work (charter rule #5).
