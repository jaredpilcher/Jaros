# Implementation Tasks — Durable, Replayable State Machine

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

### [TASK-5] Implement log replication across nodes — SUPERSEDED

> **SUPERSEDED by [TASK-6].** Implemented `jaros/state/replication.py`
> (`ReplicatedLog`) against the now-deprecated [REQ-5]. Retained for history; the
> code it produced is retired by [TASK-6]. Do not extend this task.

Survive the loss of any single node.

#### Steps
1. Create `jaros/state/replication.py` with a `ReplicatedLog` that mirrors each appended entry to registered replica sinks before acknowledging.
2. Add convergence by index+checksum (`converged_prefix`/`has_converged`/`reconcile`); document it as a single-node, file-backed stand-in for true multi-node deploy; add a test for single-replica loss losing nothing.

#### Implements
- [REQ-5] Distribution and Replication

### [TASK-6] Retire the cluster-scale replication module

Remove the deprecated multi-node replication machinery that violates the
zero-infrastructure (P3) and single-node-first (P4) scope. This is the
deprecation task for [REQ-5].

#### Steps
1. Delete `jaros/state/replication.py` (the `ReplicatedLog`/`ReplicationError` `#EXT-002-REQ-5` block) and remove its entry from the `implementation:` list in `requirements.md`.
2. In `jaros/state/__init__.py`, remove the `from jaros.state.replication import ReplicatedLog, ReplicationError` import and drop `"ReplicatedLog"`/`"ReplicationError"` from `__all__`; update the module docstring to stop describing replication.
3. Delete the replication unit tests under `tests/` (e.g. `tests/test_replication.py` / any `ReplicatedLog` cases) and remove the `REQ-5` key from `.jarify/EXT-002/index.json`.
4. Run `pytest` and the architecture checks to confirm nothing else imported `jaros.state.replication`.

#### Implements
- [REQ-5] Distribution and Replication

### [TASK-7] Record accepted decisions in the durable log

Extend the durable log from `(event, state)` transitions to the accepted
`Decision` payloads required for deterministic re-execution.

#### Steps
1. In `jaros/state/log.py`, extend `LogEntry` with a `decision: dict` field (the accepted `Decision` serialized via its JSON payload — `id`, `source`, `type`, `payload`) and include it in `compute_checksum`, `to_json`, and `read()` parsing; keep `index`/`event`/`state` for backward-compatible recovery.
2. Add a `commit_decision(log, state, machine_event, decision)` path (in `jaros/state/machine.py`) that appends the decision-bearing entry durably *before* the executor applies it, preserving the append-before-observable invariant.
3. Update the `#EXT-002-REQ-3` comment block bounds and `.jarify/EXT-002/index.json`; add a test asserting a committed entry round-trips its decision payload.

#### Implements
- [REQ-6] Deterministic Decision-Log Replay

### [TASK-8] Implement deterministic replay and express recovery as replay

Make a recorded run re-executable to byte-identical state with no model call.

#### Steps
1. Create `replay(log, executor) -> str` in `jaros/state/recover.py` that reads recorded decisions in order, feeds each through the deterministic executor (`jaros.execution.executor.apply`) — never the LLM — and returns the reconstructed final state.
2. Re-express `recover(log)` as `replay(log)` truncated at the last valid recorded decision, reusing the existing torn/corrupt-trailing-entry handling; keep `RecoveryError` semantics for corruption before the trailing entry.
3. Wrap the new code in `#EXT-002-REQ-6` Start/End comments, update `.jarify/EXT-002/index.json`, and add tests: (a) replay of a recorded log yields byte-identical state to the original run, (b) recovery and full replay agree, (c) replay performs no model call.

#### Implements
- [REQ-6] Deterministic Decision-Log Replay

### [TASK-9] Coordinate multi-node work over the shared file system

Replace the retired replication contract with single-node-first, file-based
coordination — no consensus service, broker, or network client.

#### Steps
1. Add `jaros/state/coordination.py` (wrapped in `#EXT-002-REQ-7` comments) with a file-based claim/hand-off helper over the shared layout (e.g. atomic claim files under `state/claims/`), defaulting to a zero-overhead no-op in the single-node configuration.
2. Register it in `jaros/state/__init__.py` exports; document that coordination is over the shared FS only and introduces no external infrastructure.
3. Add `.jarify/EXT-002/index.json` entries for `REQ-7` and tests covering a single-node no-op path and a two-"node" (two-dir) claim hand-off over the shared FS.

#### Implements
- [REQ-7] Bounded Multi-Node Coordination over the Shared File System

### [TASK-10] Purge "unbreakable" / unqualified "distributed" from state-machine docstrings

Align module language with the directive's claim discipline (durable,
crash-recoverable, deterministically replayable; single-node-first).

#### Steps
1. In `jaros/state/__init__.py`, rewrite the module docstring header from "Distributed State Machine" to "Durable, Replayable State Machine (EXT-002)" and replace "distributed … replicated to survive node loss" with the replay/bounded-coordination framing.
2. In `jaros/state/model.py`, remove "unbreakable"/unqualified "distributed" wording from comments/docstrings, substituting "durable, crash-recoverable, deterministically replayable".
3. Grep `jaros/state/**` for `unbreakable` and `distributed` and confirm no occurrences remain.

#### Implements
- [REQ-6] Deterministic Decision-Log Replay
- [REQ-7] Bounded Multi-Node Coordination over the Shared File System
