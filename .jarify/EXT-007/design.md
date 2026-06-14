# Design — Jaros Runtime Daemon

The daemon is the composition root that *stays running*. It assembles every plane once, then loops: ingest work from the shared FS, run agents as threads, drive durable transitions, publish status. Nothing enters except through the shared file system.

## Boot + run loop

```text
  boot: ensure FS layout -> build Queue -> create LlmClient -> Harness(rules)
        -> AgentPool(bound) -> registry.load_builtins()
                    |
                    v
  loop (every tick, until SIGINT/SIGTERM):
        scan agents/      -> import + register any new agent modules   (REQ-3)
        scan inbox/*.json  -> for each job:                              (REQ-2)
              kind,input -> registry.resolve(kind) -> ReasoningBoundary
              run under AgentPool as a thread        (REQ-3 of EXT-003)
              Decision -> gate -> executor -> commit(state machine)      (durable)
              write result -> outbox/<id>.json via harness-granted fs    (REQ-6)
              move job -> processed/ (ok) or failed/ (error)             (REQ-5)
        write status.json + heartbeat line                              (REQ-4)
        sleep(tick)
```

## Shared-FS layout the daemon owns

```text
  <data>/
    inbox/        jobs waiting to run        (written by the CLI)
    agents/      agent modules to load      (written by the CLI)
    outbox/       per-job results            (read by the CLI)
    artifacts/    durable agent outputs
    state/        transition.log (EXT-002)
    processed/    jobs that ran ok
    failed/       jobs that errored (+ reason)
    status.json   live snapshot for watching
```

## Invariants

- The daemon runs until signaled; it never exits after a single job.
- Work and agents enter ONLY via `inbox/` and `agents/` (shared FS) — no socket, no port.
- Every job result is a validated decision applied through the deterministic executor + durable state machine.
- One job's failure is contained; the daemon and sibling jobs survive.
