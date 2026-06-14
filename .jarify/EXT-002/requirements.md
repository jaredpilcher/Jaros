---
id: EXT-002
title: Durable, Replayable State Machine
status: partial
priority: high
implementation:
  - jaros/state/model.py
  - jaros/state/machine.py
  - jaros/state/log.py
  - jaros/state/recover.py
  - jaros/state/__init__.py
---

# Durable, Replayable State Machine

The deterministic backbone of Jaros: an explicitly-modeled, durable, crash-recoverable, deterministically *replayable* state machine. All system progress is a sequence of validated transitions; the durable decision log records enough to **re-execute a run to byte-identical state**, not merely to recover the last state. Distribution is **single-node-first with bounded multi-node coordination over the shared file system** — never cluster-scale replication machinery. Realizes Prime Directive tenets [PRIME-001 / REQ-2] (durable, replayable state) and purpose tenet [PRIME-001 / P1] (reproducibility by replay), within the scope boundary [PRIME-001 / P4].

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

### [REQ-5] Distribution and Replication — DEPRECATED

> **DEPRECATED (PRIME-001 revision — scope honesty, P3/P4).** This requirement
> asserted cluster-scale, multi-node log replication ("survives the loss of any
> single node," "replicated to more than one node," "replicas converge"). The
> revised Prime Directive scopes Jaros as **zero-infrastructure** (P3) and
> **single-node-first with bounded multi-node coordination over the shared file
> system** (P4) — it explicitly does *not* aim to replace Temporal/Dapr at
> cluster scale, and specs must not add cluster-scale machinery (consensus
> services, brokers, remote replication). Superseded by **[REQ-7] Bounded
> Multi-Node Coordination over the Shared File System**. The `ReplicatedLog`
> implementation in `jaros/state/replication.py` is to be deprecated/retired by
> the tasks linked below. Retained here only as the deprecation anchor.

State is distributed/replicated so the machine survives the loss of any single node.

#### Acceptance Criteria
- [ ] The transition log is replicated to more than one node.
- [ ] Loss of a single node does not lose committed transitions.
- [ ] Replicas converge to the same committed transition sequence.

### [REQ-6] Deterministic Decision-Log Replay

The durable log must capture enough to **re-execute a run deterministically**,
not merely to recover the last state. Every accepted `Decision` (the model's
output — the sole non-deterministic input, per EXT-001) is recorded as inert
data, in order, *before* its effects are observable; replaying the recorded
decisions through the deterministic executor must reconstruct the run to
byte-identical state. Crash recovery becomes a *special case* of replay.

#### Acceptance Criteria
- [ ] The durable log records each accepted `Decision` payload (not only the
      resulting `(event, state)` transition), in commit order, before its effects
      are observable.
- [ ] A `replay(log)` reconstructs final state by feeding the recorded decisions
      through the deterministic executor — with **no model call** — and yields
      byte-identical state to the original run.
- [ ] `recover()` is expressed as replay (recovery is replay to the last recorded
      decision); recovery and a full from-scratch replay agree.
- [ ] Replay is deterministic and total: identical logs always produce identical
      final state, and a torn/corrupt trailing record is discarded exactly as in
      recovery.

### [REQ-7] Bounded Multi-Node Coordination over the Shared File System

Where more than one node participates, coordination happens **over the shared
file system, single-node-first** — no consensus service, broker, or network
replication layer. The machine introduces no external infrastructure dependency
to run (see EXT-007 / REQ-6). This requirement supersedes the deprecated
[REQ-5].

#### Acceptance Criteria
- [ ] Multi-node coordination (claiming/handing off work, agreeing on committed
      order) is performed via files in the shared layout, not a network protocol.
- [ ] The single-node configuration runs with zero coordination overhead and no
      replica processes.
- [ ] No module under `jaros/state/**` imports a consensus library, message
      broker, or network client; this is asserted by an architecture check
      (see EXT-007 / REQ-6, `scripts/check_zero_infra.py`).
