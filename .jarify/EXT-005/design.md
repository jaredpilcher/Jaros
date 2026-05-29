# Design — Architectural Harness

Agents live inside the harness. They hold no ambient power; every effect is a mediated request the harness validates against architecturally-defined rules.

## Mediation

```text
   +==================== HARNESS ====================+
   |  rules (code/config) — not agent-mutable        |
   |                                                 |
   |   agent.request(action)                         |
   |        |                                        |
   |        v                                        |
   |   [ validate against rules ]                    |
   |        |               \                        |
   |     allow               deny (fail closed)      |
   |        |                    \                   |
   |        v                     v                  |
   |   perform via granted    refused + reported     |
   |   handle (queue/fs)                             |
   +=================================================+
```

## Capability scoping

```text
   harness.spawn(agent, grants = { queue: tx-q (send), fs: /outbox (write) })

   agent sees ONLY: tx-q.send, /outbox.write
   agent does NOT see: other queues, other fs paths, network, global state
   teardown ──► grants revoked
```

## Invariants

- No side effect occurs without harness mediation (default deny).
- Agents cannot mutate or bypass the rule set at runtime.
- Agents act only through explicitly granted, revocable capabilities.
