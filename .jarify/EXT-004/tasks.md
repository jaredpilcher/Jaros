# Implementation Tasks — Interchangeable LLM Adapter

### [TASK-1] Define the single provider-agnostic LLM interface

Give all callers one narrow contract that returns data only.

#### Steps
1. Create `src/llm/client.ts` exporting `interface LlmClient { complete(req: LlmRequest): Promise<LlmResponse> }` with provider-neutral `LlmRequest`/`LlmResponse` types.
2. Document in `client.ts` that `LlmResponse` carries text/structured output only — no handles and nothing that invokes a state transition.
3. Add `src/llm/index.ts` re-exporting `LlmClient` so callers never import a concrete adapter.

#### Implements
- [REQ-1] Single LLM Interface
- [REQ-3] No Control Flow Inside the LLM

### [TASK-2] Implement a concrete adapter and config-driven selection

Make the model pluggable and swappable without touching callers or the harness.

#### Steps
1. Create `src/llm/adapters/default-adapter.ts` implementing `LlmClient`.
2. Add `src/llm/factory.ts` with `createLlmClient(config)` that selects an adapter by `config.llm.provider` and returns an `LlmClient`.
3. Read provider/model from configuration in `src/llm/index.ts` and export the constructed client; verify swapping `config.llm.provider` requires no caller edits.

#### Implements
- [REQ-2] Pluggable Adapters via Configuration
- [REQ-4] Model Swap Without Code Change
