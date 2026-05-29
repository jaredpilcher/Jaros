# Design — Agent Thread Runtime

Agents are threads, not services. The runtime owns a bounded pool, spawns agents on demand, contains their faults, and reaps them.

## Pool model

```text
        +------------------ Agent Thread Runtime -------------------+
        |  bound = N (configurable)                                 |
        |                                                           |
        |   [Agent t1]  [Agent t2]  [Agent t3]  ...  [Agent tk]     |
        |      run         run         run             run         |
        |       |           |           X (fault)        |         |
        |       |           |           |  contained     |         |
        |       v           v           v                v         |
        |   teardown     teardown    reaped + reported  teardown   |
        +-----------------------------------------------------------+
                         ^
                         | spawn requests (queued when k == N)
```

## Lifecycle

```text
   spawn ──► running ──► (done | failed) ──► teardown ──► resources released
                              |
                          failed ──► fault contained ──► reported to harness
```

## Invariants

- An agent is an in-process lightweight thread/task: no socket, no port, no deployment.
- Concurrent agents never exceed the configured bound; excess spawns wait.
- One agent's failure is contained; the process and siblings survive.
