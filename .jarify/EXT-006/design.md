# Design — Communication Fabric (Queues + Shared File System)

Two channels, and only two: rigid typed queues for messages, a shared file system for durable artifacts. Agents never address each other directly.

## The only two channels

```text
   Agent A                                             Agent B
     |  enqueue(msg: Contract)                           ^
     v                                                   | dequeue
   +================= RIGID QUEUES ======================+
   |  validate(msg) ──► [ q1 ] ──► [ q2 ] ──► ...        |
   +=====================================================+
     |  write(path ∈ layout)                             ^
     v                                                   | read
   +============== SHARED FILE SYSTEM ===================+
   |   /state     /inbox     /outbox     /artifacts      |
   +=====================================================+

   A ──X──► B   (no direct in-memory / RPC / network call — build fails)
```

## Validation points

```text
   enqueue:  msg ──► [schema check] ──► accepted | REJECTED
   fs write: path ──► [layout check] ──► accepted | REJECTED
```

## Invariants

- The only inter-agent channels are queues and the shared file system.
- Every queue message is schema-validated; every fs path is layout-validated.
- No code path lets one agent call another directly; `scripts/check-comms` enforces this.
