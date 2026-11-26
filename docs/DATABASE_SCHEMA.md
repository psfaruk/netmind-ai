# Database Schema

> Status: **Implemented (Phase 1 subset, SQLAlchemy + create_all)** · Alembic migrations: Planned before Phase 5 (ADR-003) · future tables marked **[P]** with target phase. Dev profile runs the same schema on SQLite via aiosqlite; production on PostgreSQL 16.

## 1. Implemented Tables (Phase 1 + Phase 2 execution columns)

### users
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | citext UNIQUE NOT NULL | lowercased |
| password_hash | text NOT NULL | scrypt (N=2^15, r=8, p=1) |
| display_name | text | |
| is_admin | bool default false | registry write access |
| created_at | timestamptz | |

### api_keys
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | FK users | ON DELETE CASCADE |
| key_hash | text UNIQUE | SHA-256 of plaintext key |
| label | text | |
| revoked | bool default false | soft revoke |
| created_at / last_used_at | timestamptz | |

### nodes
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| node_id | text UNIQUE | Ed25519 public key (hex) |
| owner_user_id | FK users NULLABLE | NULL = community node |
| platform | text | android / windows / linux / macos / server |
| cpu_cores | int | advertised |
| ram_mb / gpu_mb | int | advertised |
| gpu | bool | |
| runtimes | text[] | ["llama.cpp", "onnx"] |
| region | text | coarse (country-level) |
| contribution_limits | jsonb | {max_cpu_pct, max_ram_mb, max_data_mb_day} |
| state | text | registered / active / stale / retired |
| last_heartbeat_at | timestamptz | |
| created_at | timestamptz | |

### node_heartbeats
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL PK | |
| node_id | text | indexed |
| ts | timestamptz | |
| cpu_load_pct, free_ram_mb, active_tasks | int | health snapshot |

### model_registry
| Column | Type | Notes |
|---|---|---|
| id | text PK | e.g. `qwen3-4b-q4` |
| name, version, license | text | license verified before availability |
| capabilities, languages | text[] | |
| context_length | int | |
| quantization | text | Q4_K_M default |
| memory_requirement_mb | int | measured |
| runtimes | text[] | |
| benchmark_refs | jsonb | S-05 results |
| deployment_location | text | node id / coordinator-local / none |
| availability | bool default false | runtime-verified only |

### tasks
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | returned to the user |
| user_id | FK users | |
| kind | text | chat/research/coding/math/translation/vision |
| input | jsonb | validated payload |
| priority | int 1–9 | 9 = interactive |
| status | text | **Phase 2 implemented states**: queued/claimed/completed/failed/cancelled; remaining design states (planned/dispatched/running/validating/conflicted/expired) arrive with later phases |
| model_id | text NULL | routing decision (Phase 2) — registry id the task is routed to |
| claimed_by | text NULL | node_id of the claiming worker (Phase 2) |
| claimed_at | timestamptz NULL | claim time; TTL expiry drives requeue (Phase 2) |
| attempts | int default 0 | claim-expiry count; task fails at max attempts (Phase 2) |
| result | jsonb NULL | output, backend, tokens, duration_ms — or error |
| deadline_at, created_at, updated_at | timestamptz | deadline enforced at claim time |

## 2. Planned Tables

| Table | Phase | Purpose |
|---|---|---|
| task_steps **[P2]** | 2 | decomposition: parent task → steps with own status |
| task_assignments **[P5]** | 5 | task → node dispatch records (attempts, retries, signatures) |
| task_results **[P5]** | 5 | signed node results + metrics + verification verdict |
| knowledge_documents **[P3]** | 3 | source, license, fetched_at, hash, TTL |
| knowledge_chunks **[P3]** | 3 | chunk text + pgvector embedding (or Qdrant ref) |
| agent_runs **[P4]** | 4 | agent executions, depth, budget usage |
| feedback **[P2]** | 2 | opt-in ratings + evaluation metadata |
| audit_log **[P5]** | 5 | security-relevant events (privacy-preserving) |
| evaluations / benchmarks **[P9]** | 9 | model comparison results |

## 3. Conventions

- UUID PKs for user-facing entities; BIGSERIAL for high-volume telemetry.
- `timestamptz` everywhere (UTC).
- jsonb for schema-flexible payloads that still need indexing via generated columns when needed.
- Vector columns via pgvector extension in production; SQLite dev profile stores vectors out-of-line (dev-only stub — not used for real retrieval tests).
- Indexes: `nodes.state`, `tasks.status, user_id`, `node_heartbeats.node_id, ts`, `api_keys.key_hash`.

## 4. Migration Policy

Phase 1 uses `Base.metadata.create_all()` for bootstrap (documented decision ADR-003). Alembic becomes mandatory before the first multi-process deployment (Phase 5) so coordinator replicas agree on schema. Schema changes always land with their ADR entry.
