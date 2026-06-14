# Design — Durable, Replayable State Machine

State advances only through validated transitions, each durably logged before it
is observable. The log records the accepted `Decision` data (not only the
resulting transition), so the run can be **re-executed deterministically** to
byte-identical state. Recovery is a special case of replay. Distribution is
single-node-first, with bounded coordination over the shared file system — no
cluster-scale replication, consensus service, or broker.

## Transition pipeline

```text
   decision ──► [ validate (gate) ] ──accepted──► [ append Decision to durable log ]
                       |                                        |
                       | rejected                               | (durable, before effects)
                       v                                        v
                  REJECTED (no mutation)        [ executor applies ──► new state observable ]
```

## Record and replay

The only non-determinism in a run is the model's output, captured as inert
`Decision` data. Recording those decisions and replaying them through the
deterministic executor reconstructs the run exactly — no model call on replay.

```text
   record:  reasoning ─► Decision(data) ─► [gate] ─► executor ─► state
                              │
                              └─► append to durable decision log

   replay:  decision log ─────────────────► executor ─► identical state
            (no model call; recorded decisions are the inputs)
```

## Recovery is replay

```text
   crash ──► restart ──► recover() == replay(log up to last recorded decision)
                           feed recorded decisions through executor in order
                           ──► reconstruct current state (byte-identical)
                           ──► resume accepting work
```

## Bounded multi-node coordination (single-node-first)

Coordination across nodes — when there is more than one — happens over the
shared file system, not a network protocol. There is no replica process, no
consensus service, and no broker. The single-node configuration runs with zero
coordination overhead.

```text
        +-------------------- SHARED FILE SYSTEM --------------------+
        |   /state   (durable decision log, append-only)             |
        |   /inbox   /outbox   /artifacts                            |
        +-----------------------------------------------------------+
              ^                         ^
              | claim / hand off via    | claim / hand off via
              | files (single-node-     | files (bounded multi-node)
              | first)                  |
          Node A                     Node B
```

## Invariants

- Current state ∈ declared states at all times.
- A transition is observable only after its decision is durably logged.
- The durable log records accepted `Decision` data, sufficient to re-execute the
  run to byte-identical state.
- Replay of the log is deterministic and total; recovery is a special case of
  replay.
- No cluster-scale replication, consensus service, or broker is introduced; any
  multi-node coordination is over the shared file system (single-node-first).
