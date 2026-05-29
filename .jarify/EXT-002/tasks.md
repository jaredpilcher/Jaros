# Implementation Tasks — Distributed State Machine

### [TASK-1] Declare the explicit state and transition model

Make states and transitions a single, introspectable source of truth.

#### Steps
1. Create `jaros/state/model.py` with `STATES` and `EVENTS` tuples, `INITIAL_STATE`, and a `TRANSITIONS: dict[str, dict[str, str]]` table.
2. Add `list_transitions() -> list[tuple[str,str,str]]` returning `(from,event,to)` triples in deterministic order, plus `is_state`/`is_event` guards.

#### Implements
- [REQ-1] Explicit State and Transition Model

### [TASK-2] Implement transition enforcement

Permit only transitions present in the model; reject everything else.

#### Steps
1. Create `jaros/state/machine.py` with `transition(state, event) -> str` that returns the next state or raises a typed `UndefinedTransitionError`.
2. Add `assert_valid_state(state)` invariant used on entry/exit; ensure a rejected transition performs no mutation.

#### Implements
- [REQ-2] Transition Enforcement

### [TASK-3] Implement the durable append-only transition log

Persist each accepted transition atomically before it becomes observable.

#### Steps
1. Create `jaros/state/log.py` with a `TransitionLog(dir, filename)` writing newline-delimited JSON; `append(entry)` flushes + `os.fsync`s; `read()` yields entries in order and tolerates a torn trailing line; append-only API (no update/delete).
2. In `jaros/state/machine.py` add `commit(log, state, event)` that validates, appends to the log, THEN applies — on append failure it does not apply (atomic).

#### Implements
- [REQ-3] Durable Append-Only Transition Log

### [TASK-4] Implement crash recovery by log replay

Rebuild current state deterministically after a crash.

#### Steps
1. Create `jaros/state/recover.py` with `recover(log) -> str` replaying entries 1..N to reconstruct current state.
2. Validate index continuity + checksum and discard a torn/corrupt trailing entry during replay; add a test simulating an interrupted commit.

#### Implements
- [REQ-4] Crash Recovery from Log

### [TASK-5] Implement log replication across nodes

Survive the loss of any single node.

#### Steps
1. Create `jaros/state/replication.py` with a `ReplicatedLog` that mirrors each appended entry to registered replica sinks before acknowledging.
2. Add convergence by index+checksum (`converged_prefix`/`has_converged`/`reconcile`); document it as a single-node, file-backed stand-in for true multi-node deploy; add a test for single-replica loss losing nothing.

#### Implements
- [REQ-5] Distribution and Replication
