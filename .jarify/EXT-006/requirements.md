---
id: EXT-006
title: Communication Fabric (Queues + Shared File System)
status: partial
priority: high
implementation:
  - jaros/comms/queue.py
  - jaros/comms/fs.py
  - jaros/comms/__init__.py
  - scripts/check_comms.py
---

# Communication Fabric (Queues + Shared File System)

The only sanctioned channels for inter-agent communication: rigid, typed queues and a shared file system with a fixed layout. No direct agent-to-agent calls of any kind. Realizes Prime Directive tenet [PRIME-001 / REQ-6].

### [REQ-1] Rigid Queue Abstraction

Agents exchange work through queues governed by rigid, typed message contracts.

#### Acceptance Criteria
- [ ] Define a queue abstraction with `enqueue`/`dequeue` over a typed message contract.
- [ ] Messages that violate the contract are rejected at enqueue time.
- [ ] Queue semantics (ordering, at-least-once/exactly-once) are explicitly specified.

### [REQ-2] Shared File System Layout

A shared file system with a fixed, specified layout serves as the durable exchange surface.

#### Acceptance Criteria
- [ ] Define the canonical layout (e.g., `/state`, `/inbox`, `/outbox`, `/artifacts`) and an access API.
- [ ] All file exchange uses workspace-relative paths within the defined layout.
- [ ] The layout is documented and validated; writes outside it are refused.

### [REQ-3] Exclusive Communication Channels

Inter-agent communication occurs ONLY through queues and the shared file system. No other channel is permitted.

#### Acceptance Criteria
- [ ] Agents have no API to address or call another agent directly.
- [ ] All cross-agent data flow is observable as queue messages or file system artifacts.
- [ ] Direct in-memory, RPC, or network agent-to-agent paths are absent.

### [REQ-4] Contract and Layout Validation

Queue message contracts and the file system layout are rigidly specified and validated.

#### Acceptance Criteria
- [ ] Queue messages are validated against a schema before delivery.
- [ ] File system structure is validated against the canonical layout.
- [ ] Contract/layout violations fail loudly with a typed error.

### [REQ-5] No Direct Agent-to-Agent Calls (Enforced)

The absence of direct agent-to-agent communication is enforced structurally, not by convention.

#### Acceptance Criteria
- [ ] An automated architecture check fails the build on any direct agent-to-agent call path.
- [ ] The check covers in-memory references, RPC, and network calls between agents.
- [ ] The only inter-agent dependencies that pass the check are the queue and file system APIs.

### [REQ-6] No External Broker Dependency

The communication fabric is the in-process queue and the shared file system —
nothing else. It introduces **no message broker, queue service, or network
transport** to run, making it the comms-layer half of the zero-infrastructure
tenet ([PRIME-001 / P3]; see EXT-007 / REQ-6).

#### Acceptance Criteria
- [ ] The `Queue` is an in-process structure and the shared FS is local/mounted
      files; neither requires nor contacts an external broker or queue service.
- [ ] No module under `jaros/comms/**` imports a broker/queue-service or network
      client (e.g. `redis`, `pika`, `kafka`, `confluent_kafka`, `nats`,
      `socket`, `http.client`).
- [ ] `scripts/check_zero_infra.py` (EXT-007 / REQ-6) covers `jaros/comms/**` and
      passes on the current tree.
