# Design — Reasoning / Execution Boundary

The boundary is a one-way valve. Reasoning produces `Decision` values; those values cross a validation gate; only then does the deterministic executor act. No reference flows the other way.

## Flow

```text
  REASONING PLANE                 BOUNDARY                 EXECUTION PLANE
  (non-deterministic)                                       (deterministic)

  +-------------+   Decision   +----------------+  ok   +------------------+
  |   Agent     | -----------> | validateDecision| ---> |    Executor      |
  | reasoning   |  (inert data)|  (normalize)   |       | (acts on state)  |
  +-------------+              +--------+-------+        +------------------+
        ^                               |
        |                               | reject (reason logged)
        |                               v
        |                        [ discarded — no state change ]
        |
   (no handle to executor / state / queues / fs)
```

## Decision shape (illustrative)

```text
Decision {
  id:      string          # unique
  source:  string          # emitting agent id
  type:    string          # discriminator for deterministic dispatch
  payload: JSON            # inert, serializable data only
}
```

## Invariants

- A `Decision` is pure data: serialize → deserialize → identical.
- The `ReasoningBoundary` interface returns only `Decision`; it imports nothing from the Execution Plane.
- `validateDecision` is total: every input yields either a normalized `Decision` or a typed rejection.
- The architecture check (`scripts/check-planes`) is the structural enforcement of [REQ-4].
