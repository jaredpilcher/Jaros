# Implementation Tasks — Reasoning / Execution Boundary

### [TASK-1] Define the inert Decision contract

Create the immutable, serializable value that is the only thing reasoning may emit.

#### Steps
1. Create `jaros/core/json_value.py` defining a `JsonValue` type alias (str/int/float/bool/None/list/dict) and an `assert_serializable(value)` that rejects functions, classes/instances, sets, bytes, and other non-JSON values recursively.
2. Create `jaros/core/decision.py` with an immutable `Decision` (frozen `@dataclass(frozen=True)`) carrying `id: str`, `source: str`, `kind: str`, `payload: JsonValue`.
3. Add `create_decision(*, id, source, kind, payload)` in `decision.py` that calls `assert_serializable(payload)` and returns a frozen `Decision`; deep-freeze nested payload by validating it is JSON-round-trippable.

#### Implements
- [REQ-1] Inert Decision Contract

### [TASK-2] Define the ReasoningBoundary interface

Funnel all reasoning through one interface whose only output is `Decision`.

#### Steps
1. Create `jaros/core/reasoning_boundary.py` defining `ReasoningBoundary` as a `typing.Protocol` (or ABC) with `def decide(self, context) -> list[Decision]:` (sync) — its only return type is `list[Decision]`.
2. Ensure `reasoning_boundary.py` imports only from `decision.py` (no executor/state/queue/fs imports).
3. Create `jaros/core/__init__.py` re-exporting `Decision`, `create_decision`, `ReasoningBoundary`, and the JSON types.

#### Implements
- [REQ-2] Reasoning Boundary Interface

### [TASK-3] Implement the decision validation gate

Stand a deterministic gate between decisions and the executor.

#### Steps
1. Create `jaros/core/decision_gate.py` with `validate_decision(d) -> ValidationResult`, where `ValidationResult` is a small dataclass/union (`ok: bool`, `value: Decision | None`, `reason: str | None`).
2. Make it total and deterministic: validate non-empty `id`/`source`/`kind` and a serializable payload, returning a normalized frozen decision or a typed rejection reason.

#### Implements
- [REQ-3] Decision Validation Gate

### [TASK-4] Implement the executor and the plane-separation check

Refuse invalid decisions; enforce the boundary structurally.

#### Steps
1. Create `jaros/execution/executor.py` with `apply(d)` that calls `validate_decision` first and, on rejection, logs the reason and returns a result with `applied=False` and no state mutation; `executor.py` must NOT import `jaros/llm/**` or `reasoning_boundary`.
2. Create `scripts/check_planes.py` that scans `jaros/execution/**.py` and exits non-zero if any file imports `jaros.llm` or `reasoning_boundary` (covers `import`, `from ... import`, and bare imports); exit 0 on a clean tree.
3. Add unit tests under `tests/` for the gate and executor.

#### Implements
- [REQ-4] No Inline Reasoning Inside Execution

### [TASK-5] Make the validation gate extensible

Let developers add deterministic validators without editing core.

#### Steps
1. In `jaros/core/decision_gate.py`, add a `register_validator(fn)` API and run all registered validators (in registration order) after the built-in structural checks within `validate_decision`.
2. Short-circuit on the first rejection (return its reason); ensure built-in structural validation always runs first and cannot be removed.
3. Add a test registering a custom validator that rejects a specific payload, proving extension works and ordering holds; reset the registry between tests.

#### Implements
- [REQ-5] Extensible Validation Gate

### [TASK-6] Make the executor dispatch to pluggable handlers by kind

Let developers extend what the system does per decision kind.

#### Steps
1. In `jaros/execution/executor.py`, add a `register_handler(kind, fn)` registry and have `apply(d, ...)` validate via the gate, then dispatch to the handler registered for `d.kind`.
2. Refuse a decision whose `kind` has no registered handler with a clear reason and no side effect; pass handlers only the validated decision + execution-plane collaborators (never the LLM/reasoning side).
3. Add tests: a registered handler runs for its kind; an unknown kind is refused with no effect; reset the registry between tests.

#### Implements
- [REQ-6] Pluggable Executor Handlers
