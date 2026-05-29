# Implementation Tasks — Reasoning / Execution Boundary

### [TASK-1] Define the inert Decision contract

Create the immutable, serializable value that is the only thing reasoning may emit.

#### Steps
1. Create `src/core/decision.ts` exporting an immutable `Decision` interface with fields `id: string`, `source: string`, `kind: string`, `payload: JsonValue`.
2. Add a `JsonValue` type in `src/core/json.ts` that structurally forbids functions/handles.
3. Add a `createDecision(input)` factory in `src/core/decision.ts` that freezes the object and throws if any field is non-serializable.
4. Add `assertSerializable(value)` in `src/core/decision.ts` used by the factory to reject closures/handles.

#### Implements
- [REQ-1] Inert Decision Contract

### [TASK-2] Define the ReasoningBoundary interface

Funnel all reasoning through one interface whose only output is `Decision`.

#### Steps
1. Create `src/core/reasoning-boundary.ts` exporting `interface ReasoningBoundary { decide(context): Promise<Decision[]> }`.
2. Ensure `reasoning-boundary.ts` imports only from `decision.ts` (no executor/state/queue/fs imports).
3. Re-export `ReasoningBoundary` and `Decision` from a `src/core/index.ts` barrel for reasoning-side consumers.

#### Implements
- [REQ-2] Reasoning Boundary Interface

### [TASK-3] Implement the decision validation gate and executor guard

Stand a deterministic gate between decisions and the executor.

#### Steps
1. Create `src/core/decision-gate.ts` with `validateDecision(d: Decision): { ok: true, value: Decision } | { ok: false, reason: string }` that normalizes and validates.
2. Create `src/exec/executor.ts` with `apply(d: Decision)` that calls `validateDecision` first and refuses to act on `ok: false`.
3. In `executor.ts`, log rejected decisions with their reason and return without mutating state.

#### Implements
- [REQ-3] Decision Validation Gate

### [TASK-4] Add the plane-separation architecture check

Enforce the boundary structurally in CI.

#### Steps
1. Create `scripts/check-planes.ts` that scans `src/exec/**` and fails if any file imports `src/llm/**` or `src/core/reasoning-boundary.ts`.
2. Add an `npm run check:planes` script in `package.json` invoking the checker.
3. Wire `check:planes` into the `pretest`/CI script so the build fails on violation.

#### Implements
- [REQ-4] No Inline Reasoning Inside Execution
