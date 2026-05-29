---
id: EXT-002
title: Distributed State Machine
status: covered
priority: high
implementation:
  - src/state/model.ts
  - src/state/machine.ts
  - src/state/log.ts
  - src/state/recover.ts
  - src/state/replication.ts
---

# Distributed State Machine

The unbreakable backbone of Jaros: an explicitly-modeled, durable, distributed state machine. All system progress is a sequence of validated transitions. Realizes Prime Directive tenet [PRIME-001 / REQ-2].

### [REQ-1] Explicit State and Transition Model

The set of states and the set of allowed transitions are declared explicitly in one place — never implied by scattered application logic.

#### Acceptance Criteria
- [ ] Define an enumerated set of states and an explicit transition table mapping `(state, event) -> nextState`.
- [ ] The model is the single source of truth; no component infers transitions independently.
- [ ] The model is introspectable (can be dumped/visualized).

### [REQ-2] Transition Enforcement

Only transitions present in the model are permitted. Any undefined transition is rejected; the machine can never enter an undefined state.

#### Acceptance Criteria
- [ ] `transition(state, event)` returns the next state only if the pair exists in the table.
- [ ] Undefined `(state, event)` pairs are rejected with a typed error and cause no mutation.
- [ ] The current state is always one of the declared states (invariant checked).

### [REQ-3] Durable Append-Only Transition Log

Every accepted transition is persisted to a durable, append-only log before it is considered committed.

#### Acceptance Criteria
- [ ] Each accepted transition is appended to durable storage prior to being observable.
- [ ] The log is append-only; existing entries are never mutated or deleted in normal operation.
- [ ] A commit is atomic: either the transition is logged and applied, or neither.

### [REQ-4] Crash Recovery from Log

Current state is fully reconstructable by replaying the durable log after a process or node crash.

#### Acceptance Criteria
- [ ] `recover()` rebuilds current state deterministically by replaying the log.
- [ ] Recovery after an interrupted commit yields a consistent state (no torn writes).
- [ ] Post-recovery state equals the state immediately before the crash.

### [REQ-5] Distribution and Replication

State is distributed/replicated so the machine survives the loss of any single node.

#### Acceptance Criteria
- [ ] The transition log is replicated to more than one node.
- [ ] Loss of a single node does not lose committed transitions.
- [ ] Replicas converge to the same committed transition sequence.
