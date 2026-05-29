# Implementation Tasks — Agent Thread Runtime

### [TASK-1] Implement the lightweight agent thread lifecycle

Make an agent a cheap in-process unit with deterministic teardown.

#### Steps
1. Create `src/runtime/agent-thread.ts` exporting `AgentThread` with `spawn()`, `run()`, and `teardown()` backed by a worker thread / lightweight task — no socket or port.
2. Ensure `teardown()` releases all handles and joins the underlying thread deterministically.
3. Add `src/runtime/agent-thread.test.ts` measuring that spawn+teardown completes within a tight time bound.

#### Implements
- [REQ-1] Lightweight Agent Lifecycle

### [TASK-2] Implement the bounded concurrent agent pool

Host many agents under an observable, bounded pool.

#### Steps
1. Create `src/runtime/agent-pool.ts` with `AgentPool(bound)` exposing `submit(agentFactory)` and `active()`.
2. Apply backpressure in `submit` by queueing spawns once `active().length === bound`.
3. Expose `snapshot()` returning each active agent's id and state for observability.

#### Implements
- [REQ-2] Concurrent Agent Pool

### [TASK-3] Add the no-server architecture check

Forbid per-agent service footprints structurally.

#### Steps
1. Create `scripts/check-no-server.ts` that scans `src/runtime/**` and agent code for `http.createServer`/`listen(`/socket bindings and fails on any match.
2. Add an `npm run check:no-server` script in `package.json`.
3. Wire `check:no-server` into the CI/pretest script.

#### Implements
- [REQ-3] No Per-Agent Service Footprint

### [TASK-4] Implement fault containment for agents

Contain a single agent's failure without harming the runtime or peers.

#### Steps
1. In `src/runtime/agent-thread.ts`, wrap agent execution so an unhandled error is caught, marks the agent `failed`, and triggers `teardown()`.
2. In `src/runtime/agent-pool.ts`, report failed agents via a `onAgentFailed` callback to the harness and keep sibling agents running.
3. Add `src/runtime/agent-pool.test.ts` asserting a thrown error in one agent leaves siblings and the process alive.

#### Implements
- [REQ-4] Agent Isolation and Fault Containment
