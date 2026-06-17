---
name: jaros-schedule-agent
description: Use when scheduling a Jaros agent to run automatically on a native cron, fixed interval, or one-shot — no external scheduler. Covers the schedule JSON shape and crash-safety.
---

# Schedule a Jaros agent

Schedules make the daemon submit a job on its own — on a cron, a fixed interval,
or once at a time. There is no external scheduler; the node dispatches them
natively and they are crash-safe (a restart neither double-fires nor skips).

## Shape

One object per file in `schedules/`. Provide exactly one trigger:

| Field | Meaning |
| --- | --- |
| `id` | unique schedule id |
| `kind` | the agent kind to submit |
| `input` | JSON input passed to the job |
| `enabled` | `true`/`false` |
| `every_seconds` | interval trigger (int) |
| `cron` | 5-field cron string, e.g. `"*/5 * * * *"` |
| `at` | ISO timestamp for a one-shot run |

## Steps

1. Copy [`templates/schedule.json`](../../templates/schedule.json) into
   `<data-dir>/schedules/`.
2. Set `id`, `kind`, and `input`.
3. Choose ONE trigger: `every_seconds`, `cron`, or `at`.

## Worked examples

```json
{ "id": "word-count-hourly", "kind": "word-count",
  "input": { "path": "README.md" }, "every_seconds": 3600, "enabled": true }
```

```json
{ "id": "nightly-health", "kind": "system-health",
  "input": {}, "cron": "0 3 * * *", "enabled": true }
```

## Verify

```bash
jaros status --data-dir <dir>    # lists schedules with their next/last run
```

Or manage them from the console's **Schedules** page (create / pause / delete).
See [reference/workflow.md](../../reference/workflow.md).
