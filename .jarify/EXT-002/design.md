# Design — Distributed State Machine

State advances only through validated transitions, each durably logged before it is observable, and the log is replicated for survival.

## Transition pipeline

```text
   event ---> [ transition(state,event) ] --valid--> [ append to durable log ]
                       |                                        |
                       | invalid (not in table)                 | replicate
                       v                                        v
                  REJECTED (no mutation)              [ apply -> new state observable ]
```

## Recovery

```text
   crash ──► restart ──► recover():
                           replay log entries 1..N in order
                           ──► reconstruct current state
                           ──► resume accepting events
```

## Replication

```text
        +---------+        +---------+        +---------+
        | Node A  |  <----> | Node B  |  <----> | Node C  |
        | log[1..N]|       | log[1..N]|       | log[1..N]|
        +---------+        +---------+        +---------+
              \________ converge on same committed sequence ________/
```

## Invariants

- Current state ∈ declared states at all times.
- A transition is observable only after it is durably logged (and replicated).
- Replay of the log is deterministic and total.
