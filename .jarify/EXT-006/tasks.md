# Implementation Tasks — Communication Fabric (Queues + Shared File System)

### [TASK-1] Implement the rigid typed queue

Provide schema-validated message passing between agents.

#### Steps
1. Create `jaros/comms/queue.py` with a generic `Queue` taking a `validator` callable; `enqueue(msg)` validates and raises a typed `QueueContractError` before storage on a contract violation; `dequeue()`/`peek()` over FIFO ordering.
2. Document the semantics (in-memory FIFO, at-least-once, non-durable) in the module docstring.

#### Implements
- [REQ-1] Rigid Queue Abstraction
- [REQ-4] Contract and Layout Validation

### [TASK-2] Implement the shared file system layout and access API

Expose a fixed, validated layout as the durable exchange surface.

#### Steps
1. Create `jaros/comms/fs.py` with a `SharedFileSystem(base_dir)` defining canonical layout dirs (`state`, `inbox`, `outbox`, `artifacts`, `plugins`, `processed`, `failed`); `ensure_layout()` creates them.
2. Implement `read(path)`/`write(path, data)` resolving workspace-relative paths within `base_dir` and refusing `..` traversal and absolute escapes with a typed `LayoutViolationError`; add `validate_layout()`.

#### Implements
- [REQ-2] Shared File System Layout
- [REQ-4] Contract and Layout Validation

### [TASK-3] Enforce exclusive channels and forbid direct agent calls

Make queues + shared FS the only inter-agent paths, structurally.

#### Steps
1. Create `scripts/check_comms.py` that scans `jaros/runtime/**` and agent/plugin code and fails (exit non-zero) on direct agent-to-agent imports, RPC, or network calls (`socket`, `http.client`, `urllib.request`, `requests`, `grpc`, `asyncio.open_connection`).
2. Allow only `jaros.comms.queue` and `jaros.comms.fs` as cross-agent dependencies; ensure it exits 0 on the current tree and add positive/negative tests.

#### Implements
- [REQ-3] Exclusive Communication Channels
- [REQ-5] No Direct Agent-to-Agent Calls (Enforced)
