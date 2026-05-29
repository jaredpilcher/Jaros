# Implementation Tasks — Interchangeable LLM Adapter

### [TASK-1] Define the single provider-agnostic LLM interface

Give all callers one narrow contract that returns data only.

#### Steps
1. Create `jaros/llm/client.py` defining `LlmRequest`/`LlmResponse` dataclasses (provider-neutral; response carries `text`/`structured`/`model` data only) and an `LlmClient` Protocol with `def complete(self, req: LlmRequest) -> LlmResponse:`.
2. Document in `client.py` that `LlmResponse` carries no handles and nothing that invokes a state transition.
3. Create `jaros/llm/__init__.py` re-exporting `LlmClient`, the request/response types, and the factory.

#### Implements
- [REQ-1] Single LLM Interface
- [REQ-3] No Control Flow Inside the LLM

### [TASK-2] Implement adapters and config-driven selection

Make the model pluggable and swappable without touching callers or the harness.

#### Steps
1. Create `jaros/llm/adapters/default_adapter.py` (deterministic echo stub) and `jaros/llm/adapters/uppercase_adapter.py`, both implementing `LlmClient`.
2. Create `jaros/llm/factory.py` with `create_llm_client(config)` selecting an adapter by `config["provider"]` (or a `LlmConfig` dataclass), raising a clear error listing known providers on unknown input.
3. Add tests proving each provider works, unknown provider raises, and swapping `provider` changes output at the same `LlmClient` call site with no caller changes.

#### Implements
- [REQ-2] Pluggable Adapters via Configuration
- [REQ-4] Model Swap Without Code Change
