"""Phase 2 model routing — deterministic kind→model mapping from the registry.

Truth-in-advertising: routing picks the *planned* model per task kind; it says
nothing about whether a runtime that can serve the model is online. A task sits
queued until a worker advertising that model claims it (see /workers/claim).

The mapping mirrors docs/AI_MODEL_REGISTRY.md (small models first — CPU/phone
budget) and is expected to evolve into capability+load-aware routing in later
sub-phases of Phase 2.
"""

# kind -> registry model id (registry_seed.py ids, llama.cpp-servable text models)
ROUTE_TABLE: dict[str, str] = {
    "chat": "qwen3-0.6b-q4",
    "research": "qwen3-1.7b-q4",
    "coding": "qwen3-1.7b-q4",
    "math": "qwen3-1.7b-q4",
    "translation": "qwen3-4b-q4",
    # "vision" intentionally unmapped: no multimodal runtime exists yet;
    # vision tasks are accepted, stored and stay queued (honest no-op).
}

# Models a mock-runtime worker advertises so the CI/E2E pipeline can execute
# every routed kind end-to-end without a live GGUF runtime.
MOCK_RUNTIME_MODELS: list[str] = [
    "qwen3-0.6b-q4",
    "qwen3-1.7b-q4",
    "qwen3-4b-q4",
    "qwen3-8b-q4",
    "gpt-oss-20b-q4",
    "phi-4-14b-q4",
]


def route_task(kind: str) -> str | None:
    """Return the registry model id a task kind routes to, or None (unroutable)."""
    return ROUTE_TABLE.get(kind)
