---
id: EXT-007
title: Jaros Runtime Daemon
status: partial
priority: high
implementation:
  - jaros/registry.py
  - jaros/daemon.py
  - scripts/check_zero_infra.py
---

# Jaros Runtime Daemon

The long-running process that boots the Jaros OS and keeps it running: it assembles every plane, ingests work and agents from the shared file system, runs agents as threads, drives durable state transitions, and exposes observable status — until cleanly shut down. Realizes Prime Directive tenets [PRIME-001 / REQ-2, REQ-3, REQ-5, REQ-6].

### [REQ-1] Boot and Continuous Run

The daemon boots all planes (shared FS, queue, LLM client, harness, state machine, agent pool) and runs continuously until it receives a shutdown signal, then shuts down cleanly.

#### Acceptance Criteria
- [ ] On start, the daemon initializes the shared FS layout, harness, state machine, and bounded agent pool, then enters a run loop.
- [ ] The daemon runs indefinitely (does not exit after one unit of work).
- [ ] On `SIGINT`/`SIGTERM`, it stops accepting new work, tears down active agents, and exits 0.

### [REQ-2] Inbox Job Ingestion

The daemon watches the shared-FS `inbox/` for job descriptors and processes each one by spawning the matching agent as a thread; processed jobs are moved aside so they are handled exactly once.

#### Acceptance Criteria
- [ ] New job files appearing in `inbox/` are detected by the run loop (polling, cross-platform — no OS-specific file events).
- [ ] Each job names an agent `kind` + inert input; the daemon resolves the kind via the registry and runs it under the agent pool.
- [ ] A processed job is moved to a `processed/` (or `failed/`) area so it is never run twice.

### [REQ-3] Runtime Agent Registry and Plugin Loading

Built-in agent kinds are registered at boot; new agent modules placed in the shared-FS `plugins/` folder are imported and registered at runtime without restarting the OS.

#### Acceptance Criteria
- [ ] A registry maps an agent `kind` to a factory producing a `ReasoningBoundary`.
- [ ] At least one built-in agent kind is registered at boot.
- [ ] A new `*.py` agent module dropped into `plugins/` is imported, its declared kind registered, and becomes usable — no daemon restart required.

### [REQ-4] Observable Status and Heartbeat

The daemon continuously publishes its state so an operator can watch it.

#### Acceptance Criteria
- [ ] A periodic heartbeat line is written to stdout (visible via `docker logs`).
- [ ] A `status.json` file is written to the shared FS with: current machine state, agent-pool snapshot (active/pending), processed/failed counts, and the last result.
- [ ] `status.json` is updated on every tick and after every processed job.

### [REQ-5] Runtime Fault Isolation

A failing job or agent is contained and recorded; the daemon keeps running.

#### Acceptance Criteria
- [ ] An exception while running a job is caught, the job is recorded as failed (moved to `failed/` with a reason), and the loop continues.
- [ ] One failed job/agent never terminates the daemon or affects sibling work.
- [ ] Failure counts and the last error are reflected in `status.json`.

### [REQ-6] Zero-Infrastructure Boot

The daemon boots and runs the whole OS with **no external server, database, or
message broker** — only the local/shared file system and in-process threads.
This makes the zero-infrastructure purpose tenet ([PRIME-001 / P3]) a structural
guarantee, not a convention, and is enforced by an architecture check shared with
the communication and state layers (EXT-006 / REQ-6, EXT-002 / REQ-7).

#### Acceptance Criteria
- [ ] The daemon starts and processes a job with only a data directory present —
      no database, broker, or external service is required or contacted.
- [ ] `scripts/check_zero_infra.py` scans `jaros/**` and fails the build if
      runtime code imports a database driver, message broker, or external server
      framework (e.g. `sqlite3` as a store, `psycopg`, `redis`, `pika`,
      `kafka`, `flask`/`fastapi`/`http.server` as a listener), complementing the
      existing `check_no_server.py` (no listening socket) and `check_comms.py`
      (no agent-to-agent RPC/network).
- [ ] The check runs as part of `pytest` and exits 0 on the current tree.
