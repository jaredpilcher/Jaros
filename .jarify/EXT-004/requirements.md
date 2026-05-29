---
id: EXT-004
title: Interchangeable LLM Adapter
status: uncovered
priority: high
implementation: []
---

# Interchangeable LLM Adapter

Treats the LLM as a pluggable, interchangeable application behind a single interface — never the system's foundation or a source of control flow. Realizes Prime Directive tenet [PRIME-001 / REQ-4].

### [REQ-1] Single LLM Interface

All model access goes through one narrow interface that any conforming model/provider can satisfy.

#### Acceptance Criteria
- [ ] Define an `LlmClient` interface with a single primary entry point (e.g., `complete(request) -> response`).
- [ ] The interface is provider-agnostic (no provider-specific types leak into callers).
- [ ] All callers depend only on `LlmClient`, never on a concrete provider.

### [REQ-2] Pluggable Adapters via Configuration

Concrete model adapters are selected through configuration; adding or switching an adapter requires no change to the harness or callers.

#### Acceptance Criteria
- [ ] At least one concrete adapter implements `LlmClient`.
- [ ] The active adapter is chosen via configuration at startup.
- [ ] Adding a new adapter requires implementing the interface only — no caller edits.

### [REQ-3] No Control Flow Inside the LLM

The model produces outputs only. System state transitions and control flow decisions are never delegated to the LLM.

#### Acceptance Criteria
- [ ] The `LlmClient` boundary returns data (text/structured output) and nothing that directly drives state transitions.
- [ ] Control flow is decided by deterministic components consuming validated `Decision`s (see EXT-001), not by the model.
- [ ] No state-machine transition is invoked from within an adapter.

### [REQ-4] Model Swap Without Code Change

Swapping the underlying model or provider is a configuration change, not a code change.

#### Acceptance Criteria
- [ ] Changing provider/model is achievable by editing configuration alone.
- [ ] Harness and state machine require zero modification to swap models.
- [ ] A swap is verifiable by running the same flow against two configured adapters.
