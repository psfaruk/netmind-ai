# Knowledge Engine

> Status: **Design Implemented (Phase 0)** · implementation Planned (Phase 3). Nothing described here runs yet — this is the binding build specification.

## 1. Purpose

NETMIND keeps its own knowledge infrastructure: it collects, indexes, organizes, retrieves and validates information from authorized sources so answers can cite evidence instead of guessing. RAG is the mechanism; citation and freshness are the contract.

## 2. Authorized Sources

| # | Source class | Examples | Trust tier |
|---|---|---|---|
| 1 | Open educational datasets | open courseware, public corpora | B |
| 2 | Public scientific publications | open-access papers | A |
| 3 | Licensed books/documents | owner-licensed material | A |
| 4 | Government portals | statistics, laws, gazettes | A |
| 5 | Public APIs | weather, reference data | B |
| 6 | Authorized web resources | allow-listed domains | C |
| 7 | User-provided documents | explicit permission only | private |
| 8 | Community-contributed verified info | review queue before acceptance | C→B on review |
| 9 | Internal technical documentation | NETMIND's own docs | A |
| 10 | Previously approved records | validated outputs | B |

Every chunk stores: source URL, license/rights note, fetched timestamp, content hash, and a reliability score derived from the trust tier plus source history.

## 3. Pipeline

```
fetch/ingest → extract text (PDF/HTML/docx) → clean → chunk (semantic, ~512 tok)
  → embed (bge-m3, multilingual — Bengali included) → index (pgvector first; Qdrant at scale)
  → full-text index (PostgreSQL tsvector) → graph entities (knowledge graph, Phase 3 late)
```

- **Duplicate detection:** content hash + near-duplicate embedding similarity (≥0.98 ⇒ merge, keep earliest authoritative source).
- **Freshness tracking:** `fetched_at`, `source_modified_at`, TTL per source class; time-sensitive queries must respect TTL (stale ⇒ research agent refresh).
- **Versioning:** dataset snapshots versioned; ingestion is idempotent and replayable.

## 4. Retrieval & Generation (RAG)

1. UKR decides what is already known vs. missing (`TASK_EXECUTION_FLOW.md` step 5).
2. Hybrid retrieval: vector similarity + full-text + (later) graph expansion, merged with reciprocal rank fusion.
3. Answer composition happens on a registry model; every external fact carries a citation; the verifier rejects uncited external claims.
4. Answer classes are explicit: **known** (from KB) / **retrieved** (fresh external fetch) / **inferred** (model reasoning) / **unverified** (flagged as such) / **time-sensitive** (timestamp shown). Never present unverified as verified; never fabricate references.

## 5. Storage

- PostgreSQL: document/chunk metadata, rights, TTL, sources (tables `knowledge_documents`, `knowledge_chunks` — `DATABASE_SCHEMA.md`, planned).
- pgvector for vectors at Alpha scale; Qdrant swap-in documented (ADR-007) when >10M chunks.
- Object storage (MinIO/S3 later; filesystem at first): originals, per-source manifests.

## 6. Privacy Rules (non-negotiable)

- User documents are private by default; they are searchable **only** for the owner's own requests, and are never used for training, never shared to nodes as general knowledge, and deleted on request.
- No training on any user content without explicit permission (charter rule: master prompt §8).
- Ingestion of personal data from public sources is out of scope by policy.

## 7. Acceptance (Phase 3 gate)

- 1,000+ document corpus ingested with dedup + freshness working.
- Cited RAG answers with source attribution on a test set (Bengali + English).
- Retrieval quality: ≥0.75 recall@5 on the internal eval set before Phase 4 starts.
