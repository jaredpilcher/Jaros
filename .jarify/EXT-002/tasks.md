# Implementation Tasks — Distributed State Machine

### [TASK-1] Declare the explicit state and transition model

Make states and transitions a single, introspectable source of truth.

#### Steps
1. Create `src/state/model.ts` exporting a `States` union and a `TRANSITIONS` table typed as `Record<State, Partial<Record<Event, State>>>`.
2. Add `listTransitions()` in `model.ts` returning a flat array of `(from, event, to)` for visualization/audit.
3. Add a unit test `src/state/model.test.ts` asserting the table contains no transition to an undeclared state.

#### Implements
- [REQ-1] Explicit State and Transition Model

### [TASK-2] Implement transition enforcement

Permit only transitions present in the model; reject everything else.

#### Steps
1. Create `src/state/machine.ts` with `transition(state, event)` that looks up `TRANSITIONS[state][event]` and returns the next state or a typed `UndefinedTransitionError`.
2. Add an `assertValidState(state)` invariant check used on entry and exit of `transition`.
3. Ensure a rejected transition performs no mutation and surfaces the error to the caller.

#### Implements
- [REQ-2] Transition Enforcement

### [TASK-3] Implement the durable append-only transition log

Persist each accepted transition atomically before it becomes observable.

#### Steps
1. Create `src/state/log.ts` with `append(entry)` writing to a durable append-only store and `read()` streaming entries in order.
2. Implement atomic commit in `src/state/machine.ts`: append the transition, then apply it; on append failure, do not apply.
3. Guard against mutation/deletion of existing entries in `log.ts` (append-only API surface only).

#### Implements
- [REQ-3] Durable Append-Only Transition Log

### [TASK-4] Implement crash recovery by log replay

Rebuild current state deterministically after a crash.

#### Steps
1. Create `src/state/recover.ts` with `recover()` that replays `log.read()` from entry 1..N to reconstruct current state.
2. Handle an interrupted final commit by discarding any partial/torn trailing entry during replay.
3. Add `src/state/recover.test.ts` asserting post-recovery state equals pre-crash state for a simulated interruption.

#### Implements
- [REQ-4] Crash Recovery from Log

### [TASK-5] Implement log replication across nodes

Survive the loss of any single node.

#### Steps
1. Create `src/state/replication.ts` that mirrors each appended log entry to peer nodes before the entry is acknowledged.
2. Implement convergence logic so replicas agree on the committed entry sequence (e.g., index + checksum reconciliation).
3. Add `src/state/replication.test.ts` simulating single-node loss and asserting no committed transition is lost.

#### Implements
- [REQ-5] Distribution and Replication
