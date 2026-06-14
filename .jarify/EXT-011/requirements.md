---
id: EXT-011
title: Native Agent Scheduling
status: covered
priority: high
implementation:
  - jaros/scheduling/cron.py
  - jaros/scheduling/scheduler.py
  - jaros/scheduling/__init__.py
  - jaros/daemon.py
---

# Native Agent Scheduling

Jaros runs agents on a schedule natively — recurring or one-shot — without a
external cron daemon, broker, or service. Schedules are plain files in the shared
data directory; the runtime daemon evaluates them each tick and submits jobs to
the inbox when they are due, exactly as a host operator would. Scheduler progress
is durable, so a restart neither double-fires nor silently skips a due run. This
realizes regular, unattended operation while preserving the Prime Directive's
zero-infrastructure [PRIME-001 / P3] and single-node-first [PRIME-001 / P4]
tenets.

### [REQ-1] File-Based Schedule Definitions

Schedules are declared as JSON files in the shared-FS `schedules/` folder. Each
defines the agent job to run and when, and is owned by the operator (added,
edited, or removed by dropping/removing files) — never by agents at runtime.

#### Acceptance Criteria
- [x] A schedule file `schedules/<name>.json` defines `{id, kind, input, enabled}`
      plus exactly one trigger (`every_seconds`, `cron`, or `at`).
- [x] Malformed or unparseable schedule files are skipped with a logged reason and
      never crash the daemon.
- [x] New/edited/removed schedule files are picked up on the next tick without a
      daemon restart.

### [REQ-2] Interval & Cron Triggers

A schedule fires either on a fixed interval or on a standard 5-field cron
expression, evaluated with the standard library only (no external cron).

#### Acceptance Criteria
- [x] `every_seconds: N` fires at most once per N-second window since the last run.
- [x] `cron: "m h dom mon dow"` supports `*`, lists (`1,2`), ranges (`1-5`), and
      steps (`*/15`), matched at minute granularity.
- [x] Trigger evaluation is a pure function of the schedule and the current time;
      it performs no I/O and imports only the standard library.

### [REQ-3] Durable, Crash-Safe Scheduler State

The scheduler persists each schedule's last fire so progress survives a restart:
a due run is not fired twice, and a window already satisfied is not re-fired after
a crash.

#### Acceptance Criteria
- [x] Last-fire timestamps are persisted atomically to
      `state/schedules.state.json` (temp file + replace) after each dispatch.
- [x] On boot the scheduler loads prior state; schedules already satisfied for the
      current window do not immediately re-fire.
- [x] State for a removed schedule is pruned; a renamed/added schedule starts fresh.

### [REQ-4] Daemon-Integrated Dispatch

The runtime daemon drives scheduling inside its existing tick loop, submitting due
jobs to the inbox atomically — the same entry point the CLI and console use.

#### Acceptance Criteria
- [x] Each tick, the daemon asks the scheduler for due schedules and writes one
      `inbox/<job-id>.json` per due schedule (atomic temp + rename).
- [x] A dispatched job carries the schedule's `kind` and `input`, and is processed
      by the normal pipeline (gate → executor → durable log).
- [x] A failure while evaluating or dispatching one schedule is contained and does
      not affect other schedules or stop the daemon.

### [REQ-5] Enable/Disable & One-Shot Schedules

Schedules can be paused without deletion, and one-shot schedules fire exactly once.

#### Acceptance Criteria
- [x] `enabled: false` suppresses dispatch while retaining the definition and state.
- [x] An `at: <iso-timestamp>` schedule fires once when its time has passed and
      never again (recorded as fired in durable state).
- [x] Re-enabling a recurring schedule resumes on its normal cadence.

### [REQ-6] Schedule Observability

A running operator can see the configured schedules and their timing.

#### Acceptance Criteria
- [x] `status.json` includes a `schedules` array with each schedule's `id`,
      trigger, `enabled`, `lastRun`, and (for interval/cron) `nextRun`.
- [x] Schedule dispatches increment an observable counter and are visible as
      ordinary inbox jobs/outbox results.
- [x] The data is readable purely from the shared FS (no daemon network endpoint).
