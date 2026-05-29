# Implementation Tasks — Communication Fabric (Queues + Shared File System)

### [TASK-1] Implement the rigid typed queue

Provide schema-validated message passing between agents.

#### Steps
1. Create `src/comms/queue.ts` with `Queue<T>` exposing `enqueue(msg: T)` and `dequeue(): Promise<T>` over a typed contract.
2. Validate `msg` against its schema in `enqueue` and reject contract violations with a typed error before the message is stored.
3. Document and implement the chosen delivery semantics (ordering + at-least-once) in `queue.ts`.

#### Implements
- [REQ-1] Rigid Queue Abstraction
- [REQ-4] Contract and Layout Validation

### [TASK-2] Implement the shared file system layout and access API

Expose a fixed, validated layout as the durable exchange surface.

#### Steps
1. Create `src/comms/fs.ts` defining the canonical layout constants `/state`, `/inbox`, `/outbox`, `/artifacts` (workspace-relative).
2. Implement `read(path)` / `write(path, data)` in `fs.ts` that resolve paths within the layout and refuse writes outside it.
3. Add `validateLayout()` in `fs.ts` that asserts the on-disk structure matches the canonical layout.

#### Implements
- [REQ-2] Shared File System Layout
- [REQ-4] Contract and Layout Validation

### [TASK-3] Enforce exclusive channels and forbid direct agent calls

Make queues + shared FS the only inter-agent paths, structurally.

#### Steps
1. Create `scripts/check-comms.ts` that scans agent/runtime code and fails on any direct agent-to-agent reference, RPC, or network call between agents.
2. Allow only imports of `src/comms/queue.ts` and `src/comms/fs.ts` as cross-agent dependencies in the checker's allowlist.
3. Add an `npm run check:comms` script in `package.json` and wire it into CI/pretest.

#### Implements
- [REQ-3] Exclusive Communication Channels
- [REQ-5] No Direct Agent-to-Agent Calls (Enforced)
