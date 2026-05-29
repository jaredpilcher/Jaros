# Implementation Tasks — Agent Thread Runtime

### [TASK-1] Implement the lightweight agent thread lifecycle

Make an agent a cheap in-process unit with deterministic teardown.

#### Steps
1. Create `jaros/runtime/lifecycle.py` defining `AgentState` (`spawned`/`running`/`done`/`failed`/`torndown`) and a structural `RunnableAgent` Protocol (`id`, `state`, `run()`, `teardown()`).
2. Create `jaros/runtime/agent_thread.py` with `AgentThread` backed by `threading.Thread` (NO socket/port/server); `spawn(...)` builds it, `run()` executes the agent body once, `teardown()` joins and releases handles (idempotent). Wrap the body so an unhandled exception is contained: set state `failed`, record the error, fire `on_failed`, never propagate to crash the process.

#### Implements
- [REQ-1] Lightweight Agent Lifecycle
- [REQ-4] Agent Isolation and Fault Containment

### [TASK-2] Implement the bounded concurrent agent pool

Host many agents under an observable, bounded pool.

#### Steps
1. Create `jaros/runtime/agent_pool.py` with `AgentPool(bound, on_agent_failed=None)` exposing `submit(factory)`, `active()`, `pending`, `snapshot()` (id+state), and `drain()`.
2. Apply backpressure: queue spawns once `len(active()) == bound`; admit queued work as slots free; report contained failures via `on_agent_failed` while siblings keep running.

#### Implements
- [REQ-2] Concurrent Agent Pool
- [REQ-4] Agent Isolation and Fault Containment

### [TASK-3] Add the no-server architecture check

Forbid per-agent service footprints structurally.

#### Steps
1. Create `scripts/check_no_server.py` that scans `jaros/runtime/**.py` and agent code and fails (exit non-zero) on server/listener patterns (`socket.socket`, `.bind(`, `.listen(`, `HTTPServer`, `socketserver`, `asyncio.start_server`).
2. Ensure it exits 0 on the current tree and handles the no-files case gracefully; add a unit test covering a positive and negative case.

#### Implements
- [REQ-3] No Per-Agent Service Footprint
