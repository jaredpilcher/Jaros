# Design — Native Agent Scheduling

Scheduling is "just files and time." Operators drop schedule JSON into the shared
`schedules/` folder; the runtime daemon evaluates them on its existing tick and
submits due jobs to the inbox. There is no external cron daemon, broker, or
service — the scheduler is pure standard library, single-node-first, and its
progress is durable so a restart is safe. It plugs into the same job pipeline
everything else uses (EXT-007/EXT-008).

## Placement

```text
   jaros/scheduling/
     cron.py        pure 5-field cron matcher (*, lists, ranges, steps)
     scheduler.py   Schedule model, load from schedules/, due() + durable state
     __init__.py    exports
```

`jaros/scheduling/**` imports only the standard library (datetime, json,
pathlib), so the no-server / comms / zero-infra guardrails over `jaros/**` stay
green: scheduling adds no infrastructure.

## Flow (inside the daemon tick)

```text
   tick:
     load schedules/*.json  ──►  Scheduler.due(now)
                                     │  (compares trigger to last-fire state)
                                     ▼
                          [ schedules due to fire ]
                                     │  submit one job each (atomic inbox write)
                                     ▼
                    inbox/<job-id>.json  ──► normal pipeline (gate → executor → log)
                                     │
                                     ▼
                   persist last-fire to state/schedules.state.json (atomic)
```

The daemon already ingests `inbox/`, so a scheduled dispatch is indistinguishable
from a CLI/console submission downstream — it flows through the gate, the
executor, and the durable decision log like any other job.

## Triggers

```text
   every_seconds: 60     fire once per 60s window since lastRun
   cron: "*/15 * * * *"  fire when the current minute matches (m h dom mon dow)
   at:  "2026-06-13T18:00:00"  fire once after the timestamp, then never again
```

Cron matching is a pure function `cron_due(expr, dt)` evaluated at minute
granularity; the scheduler only fires a cron schedule once per matching minute by
recording the last-fired minute in durable state.

## Durability & crash-safety

```text
   state/schedules.state.json   { "<id>": { "lastRun": <epoch>, "lastMinute": "..." } }
```

Written atomically (temp + os.replace) after each dispatch. On boot the scheduler
loads it, so:

- an interval window already satisfied does not immediately re-fire;
- a cron minute already fired is not re-fired after a restart within that minute;
- a one-shot already fired stays fired.

State for schedules no longer present is pruned; a new schedule starts fresh.

## Prime Directive consistency

- No external cron/broker/service — files + the daemon's own loop. [P3]
- Single-node-first; multi-node coordination (if any) is the existing shared-FS
  claim mechanism (EXT-002 / REQ-7), not a scheduling service. [P4]
- Dispatch is an ordinary inert job submission; agents still only propose
  `Decision` data and cannot schedule themselves. [REQ-1, P2]
