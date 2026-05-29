# Implementation Tasks — Jaros Runtime Daemon

### [TASK-1] Implement the agent registry with plugin loading

Map agent kinds to factories; load built-ins and runtime plugins.

#### Steps
1. Create `jaros/registry.py` with an `AgentRegistry` class: `register(kind, factory)`, `resolve(kind) -> ReasoningBoundary`, `kinds()`.
2. Register at least one built-in kind (e.g. `"advance"`) in `register_builtins(registry, llm)` returning a `ReasoningBoundary` that consults the `LlmClient` and emits an `advance` `Decision`.
3. Implement `load_plugins(registry, plugins_dir)` that imports each `*.py` in the dir via `importlib.util`, reads its module-level `KIND` and `build(llm)` factory, and registers it; track already-loaded files so re-scans are idempotent.

#### Implements
- [REQ-3] Runtime Agent Registry and Plugin Loading

### [TASK-2] Implement the daemon boot and continuous run loop

Boot every plane and loop until signaled.

#### Steps
1. Create `jaros/daemon.py` with a `Daemon` class whose `__init__` builds the `SharedFileSystem` (+`ensure_layout`), `Queue`, `LlmClient` (via factory), `Harness`, `AgentPool`, and `AgentRegistry`.
2. Implement `run()` that installs `signal` handlers for `SIGINT`/`SIGTERM` to set a stop flag, then loops on a configurable tick (`JAROS_TICK_MS`) until stopped, and on exit tears down active agents and the pool.
3. Ensure the loop body calls plugin-scan, inbox-scan, and status-write helpers (TASK-1/3/4) each tick.

#### Implements
- [REQ-1] Boot and Continuous Run

### [TASK-3] Implement inbox job ingestion and fault isolation

Turn inbox job files into validated, durable transitions; isolate failures.

#### Steps
1. In `jaros/daemon.py`, add `_process_inbox()` that lists `inbox/*.json`, parses `{id, kind, input}`, resolves the kind, and runs the agent under the `AgentPool`.
2. Pipe the emitted `Decision` through `validate_decision` then `executor.apply`, then drive `commit(log, state, event)` transitions and write `outbox/<id>.json` via a harness-granted `fs.write`.
3. Wrap each job in try/except: on success move the job file to `processed/`; on error move it to `failed/` with a `.reason` and increment the failure count — never let the loop die.

#### Implements
- [REQ-2] Inbox Job Ingestion
- [REQ-5] Runtime Fault Isolation

### [TASK-4] Implement observable status and heartbeat

Publish live state for watching.

#### Steps
1. In `jaros/daemon.py`, add `_write_status()` that serializes `{state, pool: snapshot, processed, failed, lastResult, tick, uptimeSec}` to `<data>/status.json` atomically (write temp + replace).
2. Print a one-line heartbeat to stdout each tick (e.g. `JAROS_HEARTBEAT tick=… state=… active=… processed=… failed=…`).
3. Call `_write_status()` on every tick and immediately after each processed/failed job.

#### Implements
- [REQ-4] Observable Status and Heartbeat
