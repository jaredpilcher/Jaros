---
id: EXT-003
title: Agent Thread Runtime
status: covered
priority: high
implementation:
  - src/runtime/agent-thread.ts
  - src/runtime/agent-pool.ts
  - src/runtime/lifecycle.ts
  - scripts/check-no-server.ts
---

# Agent Thread Runtime

Runs AI agents as lightweight computing threads — cheap to spawn, cheap to tear down, many at once — explicitly NOT as bloated microservices. Realizes Prime Directive tenet [PRIME-001 / REQ-3].

### [REQ-1] Lightweight Agent Lifecycle

An agent is a lightweight unit of execution with a cheap spawn/run/teardown lifecycle. Creating an agent must not require provisioning infrastructure.

#### Acceptance Criteria
- [ ] Spawning an agent allocates only an in-process lightweight thread/task — no network service, container, or port.
- [ ] Agent teardown releases all its resources deterministically.
- [ ] Spawn and teardown are fast enough to be performed routinely at runtime.

### [REQ-2] Concurrent Agent Pool

The runtime manages many agents running concurrently under a bounded, observable pool.

#### Acceptance Criteria
- [ ] The runtime can host many concurrent agents up to a configurable bound.
- [ ] Active agents and their states are enumerable for observability.
- [ ] Backpressure or queuing applies when the bound is reached, rather than unbounded growth.

### [REQ-3] No Per-Agent Service Footprint

Agents MUST NOT carry their own service deployment, HTTP server, or per-agent infrastructure.

#### Acceptance Criteria
- [ ] No agent opens its own listening socket or HTTP server.
- [ ] No agent requires a separate deployment unit to run.
- [ ] An architecture check fails the build if agent code starts a server/listener.

### [REQ-4] Agent Isolation and Fault Containment

A single agent failure must not crash the runtime or sibling agents.

#### Acceptance Criteria
- [ ] An unhandled error in one agent is contained and does not terminate the process.
- [ ] A failed agent is torn down cleanly and reported to the harness.
- [ ] Sibling agents continue running unaffected after a peer fails.
