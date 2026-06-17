---
id: EXT-001
title: Reasoning / Execution Boundary
status: partial
priority: high
implementation:
  - jaros/core/json_value.py
  - jaros/core/decision.py
  - jaros/core/reasoning_boundary.py
  - jaros/core/__init__.py
  - jaros/core/decision_gate.py
  - jaros/execution/__init__.py
  - jaros/execution/executor.py
  - scripts/check_planes.py
---

# Reasoning / Execution Boundary

Establishes the hard seam between the non-deterministic Reasoning Plane and the deterministic Execution Plane. Reasoning emits only inert `Decision` data; the deterministic side validates and acts. This spec realizes Prime Directive tenet [PRIME-001 / REQ-1] (decouple reasoning from execution) and supports [REQ-4] (LLM is an interchangeable application).

### [REQ-1] Inert Decision Contract

Reasoning components communicate with the rest of the system exclusively via an immutable, serializable `Decision` value. A `Decision` carries data and intent only — it MUST NOT contain callbacks, closures, handles, or any directly executable side effect.

#### Acceptance Criteria
- [ ] Define an immutable `Decision` type that is fully JSON-serializable.
- [ ] Reject (at construction/validation) any `Decision` carrying functions, handles, or non-serializable fields.
- [ ] Every `Decision` records the agent/source and a discriminated `type` so the executor can dispatch deterministically.

### [REQ-2] Reasoning Boundary Interface

All reasoning is funnelled through a single boundary interface whose only output type is `Decision`. Nothing on the reasoning side can reach into execution directly.

#### Acceptance Criteria
- [ ] Define a `ReasoningBoundary` interface whose methods return only `Decision` (or collections of `Decision`).
- [ ] The boundary has no reference to executor, state store, queue, or file system handles.
- [ ] All agent reasoning entry points are typed against `ReasoningBoundary`.

### [REQ-3] Decision Validation Gate

Every `Decision` passes a deterministic validation/normalization gate before any executor acts on it. Invalid decisions are rejected and never reach the Execution Plane.

#### Acceptance Criteria
- [ ] Implement `validateDecision(decision)` that returns a normalized decision or a typed rejection.
- [ ] The executor refuses to act on any decision that did not pass the gate.
- [ ] Rejected decisions are logged with a reason and do not mutate system state.

### [REQ-4] No Inline Reasoning Inside Execution

Deterministic execution modules MUST NOT invoke the LLM or otherwise branch on non-deterministic input. The boundary is enforced structurally, not by convention.

#### Acceptance Criteria
- [ ] Execution-plane modules contain zero imports of the LLM client/adapter.
- [ ] An automated architecture check fails the build if an execution module imports reasoning/LLM code.
- [ ] Given identical inputs, an execution path produces identical outputs (deterministic).

### [REQ-5] Extensible Validation Gate

Developers can extend the validation gate with additional deterministic validators/policies without modifying core code. The gate remains total and deterministic; every registered validator runs before a decision is accepted.

#### Acceptance Criteria
- [ ] The gate exposes a registration API (e.g. `register_validator(fn)`) for additional deterministic validators that each return accept or a typed rejection reason.
- [ ] All registered validators run in a defined, stable order; the first rejection short-circuits with its reason and no decision is accepted.
- [ ] Built-in structural validation (serializable payload, required fields) always runs first and cannot be removed by a developer extension.
- [ ] A validator must be a pure function of the decision (it performs no side effects); this keeps the gate deterministic.

### [REQ-6] Pluggable Executor Handlers

The executor dispatches an accepted decision to a handler registered for its `type`, so developers can extend what the system *does* without changing the boundary or the gate. Unknown types are refused, not guessed.

#### Acceptance Criteria
- [ ] The executor exposes a registration API (e.g. `register_handler(decision_type, fn)`) mapping a decision `type` to a deterministic handler.
- [ ] `apply` validates via the gate, then dispatches to the handler for the decision's `type`; a decision whose `type` has no registered handler is refused with a clear reason and causes no side effect.
- [ ] Handlers are invoked only with the validated decision and execution-plane collaborators (state machine, granted handles) — never the LLM/reasoning side.

### [REQ-7] Decision Is the Sole Replayable Non-Deterministic Input

The accepted `Decision` is the *only* non-deterministic input to a run, and it
is captured as inert, fully-serializable data. The executor must therefore be
re-runnable from recorded decisions alone — given the same accepted decisions in
order, it produces identical effects with no model call. This is the EXT-001
half of reproducibility-by-replay ([PRIME-001 / P1]); the durable recording and
replay driver live in EXT-002 ([REQ-6]).

#### Acceptance Criteria
- [ ] An accepted `Decision` carries everything the executor needs to act — no
      out-of-band reasoning state, no handles, nothing non-serializable (already
      guaranteed by [REQ-1]); replay never re-consults the model.
- [ ] `apply` is a deterministic function of the validated decision plus
      execution-plane collaborators: identical decisions yield identical results
      and effects.
- [ ] The executor exposes a hook (or returns the accepted decision) so the
      durable log (EXT-002 / REQ-6) can record each accepted `Decision` in commit
      order before its effects are observable.
- [ ] Handler determinism — the precondition for byte-identical replay — is
      checkable, not assumed: `jaros.execution.replays_agree` confirms that
      replaying the same recorded decisions into isolated state agrees, and
      divergence flags a non-deterministic handler (surfaced as replay's
      `deterministic` result).
