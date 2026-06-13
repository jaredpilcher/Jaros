# Implementation Tasks — Native Agent Scheduling

### [TASK-1] Implement the pure-stdlib cron matcher

Provide a side-effect-free 5-field cron evaluator.

#### Steps
1. Create `jaros/scheduling/cron.py` with `cron_due(expr: str, dt: datetime) -> bool` parsing five fields (minute, hour, day-of-month, month, day-of-week) supporting `*`, lists (`1,2`), ranges (`1-5`), and steps (`*/15`, `0-30/10`).
2. Add `_match_field(spec, value, lo, hi)` helpers and validate field count/ranges, raising a typed `CronError` for malformed expressions; import only `datetime`/stdlib.

#### Implements
- [REQ-2] Interval & Cron Triggers

### [TASK-2] Implement the Schedule model and loader

Model a schedule and load the operator's definitions from the shared FS.

#### Steps
1. Create `jaros/scheduling/scheduler.py` with a frozen `Schedule` dataclass (`id`, `kind`, `input`, `enabled`, and one of `every_seconds`/`cron`/`at`) and `load_schedules(schedules_dir) -> list[Schedule]` reading `*.json`, skipping malformed files with a logged reason.
2. Add `Schedule.from_dict()` validation (exactly one trigger; known fields) and `next_run(now, last_run)` for interval/cron used by observability.

#### Implements
- [REQ-1] File-Based Schedule Definitions
- [REQ-5] Enable/Disable & One-Shot Schedules

### [TASK-3] Implement the durable, crash-safe Scheduler

Track last-fire state and decide which schedules are due, surviving restarts.

#### Steps
1. In `jaros/scheduling/scheduler.py`, add a `Scheduler(state_path)` that loads `state/schedules.state.json` on construction and exposes `due(schedules, now) -> list[Schedule]` deciding per-trigger (interval window, cron minute, one-shot) using the loaded last-fire state.
2. Add `mark_fired(schedule, now)` plus atomic `_persist()` (temp + `os.replace`); prune state for schedules no longer present; `describe(schedules, now)` returns `{id, trigger, enabled, lastRun, nextRun}` for status.

#### Implements
- [REQ-3] Durable, Crash-Safe Scheduler State
- [REQ-5] Enable/Disable & One-Shot Schedules
- [REQ-6] Schedule Observability

### [TASK-4] Integrate scheduling into the daemon tick

Evaluate schedules each tick and dispatch due jobs to the inbox, contained.

#### Steps
1. In `jaros/daemon.py`, construct a `Scheduler` over the data dir at boot; add `_dispatch_schedules()` that calls `load_schedules` + `scheduler.due(now)` and, per due schedule, writes an atomic `inbox/<id>.json` `{id, kind, input}` and calls `mark_fired`.
2. Call `_dispatch_schedules()` from `tick()` inside a try/except so one bad schedule never stops the loop; track a `scheduled` count and include `scheduler.describe(...)` in `_write_status()` as `schedules`.

#### Implements
- [REQ-4] Daemon-Integrated Dispatch
- [REQ-6] Schedule Observability

### [TASK-5] Test the scheduler end-to-end

Unit-test the cron matcher and scheduler logic; integration-test daemon dispatch.

#### Steps
1. Create `tests/test_cron.py` (matching/non-matching for `*`, lists, ranges, steps, dow/dom; malformed raises) and `tests/test_scheduler.py` (interval window fires once; cron fires on the minute; one-shot fires once; `enabled:false` suppresses; state persists + prunes across reload).
2. Create `tests/test_daemon_scheduling.py` that boots a `Daemon` on a tmp dir with an `every_seconds` schedule, ticks, and asserts a job was dispatched to inbox and `status.json.schedules` reflects it.

#### Implements
- [REQ-1] File-Based Schedule Definitions
- [REQ-3] Durable, Crash-Safe Scheduler State
- [REQ-4] Daemon-Integrated Dispatch
