---
id: EXT-008
title: Host Control CLI and Shared-FS Ingestion
status: covered
priority: high
implementation:
  - jaros/cli.py
  - jaros/execution/handlers.py
---

# Host Control CLI and Shared-FS Ingestion

A cross-platform command-line interface for driving a running Jaros OS from the host, communicating only through the shared file system. Realizes Prime Directive tenet [PRIME-001 / REQ-6] for the host↔OS control plane.

### [REQ-1] Cross-Platform, Filesystem-Only CLI

The CLI runs identically on Windows, macOS, and Linux and uses only the shared file system to reach the OS — no network, no platform-specific APIs.

#### Acceptance Criteria
- [ ] The CLI is pure Python standard library and uses `pathlib` for all paths (no shell-outs, no `os.sep` assumptions).
- [ ] It targets a shared data directory resolved from `--data-dir`, `JAROS_DATA_DIR`, or a default — the same dir the daemon uses (a mounted volume under Docker).
- [ ] It opens no sockets and makes no network calls.

### [REQ-2] Submit Jobs

`submit` writes a well-formed job descriptor into the daemon's `inbox/`.

#### Acceptance Criteria
- [ ] `jaros submit <kind> [--input <json>]` writes `inbox/<generated-id>.json` containing `{id, kind, input}`.
- [ ] The job id is unique; the file is written atomically so the daemon never reads a partial job.
- [ ] Invalid input (e.g. malformed JSON) is rejected with a clear error and writes nothing.

### [REQ-3] Add Agent Agents

`add-agent` installs a new agent module into the watched `agents/` folder.

#### Acceptance Criteria
- [ ] `jaros add-agent <path-to-module.py> [--name <kind>]` copies the module into `agents/` so the daemon can load it.
- [ ] The installed module is placed atomically (no partial file visible to the daemon).
- [ ] A missing/invalid source path is rejected with a clear error.

### [REQ-4] Watch and Status

The CLI lets an operator observe the running OS via the shared FS.

#### Acceptance Criteria
- [ ] `jaros status` reads and prints `status.json` (current state, pool, processed/failed counts, last result).
- [ ] `jaros watch` repeatedly renders status and surfaces new `outbox/` results until interrupted.
- [ ] Both work with no daemon network endpoint — purely by reading shared-FS files.

### [REQ-5] Shared-FS-Only Transport

The CLI uses exclusively the shared file system as its transport to the OS.

#### Acceptance Criteria
- [ ] Every command's effect is a read or write within the shared data directory.
- [ ] No command depends on the daemon being reachable over a network.
- [ ] The `check:comms` architecture check (EXT-006) passes for the CLI (no network/RPC).

### [REQ-6] Deterministic Replay Command

`jaros replay` reconstructs an entire run from the recorded decision log in one
command — without a running daemon — and verifies the differentiator: the same
recorded decisions reproduce **byte-identical state with zero model calls**. This
exposes EXT-002 / REQ-6 (deterministic decision-log replay) on the host control
plane, and reuses the runtime's own executor handlers so the guarantee is real,
not a re-implementation.

#### Acceptance Criteria
- [ ] `jaros replay [--data-dir D] [--json]` resolves the data dir like every
      other command and re-applies `state/decisions.log` through the deterministic
      executor — constructing **no** `LlmClient` and making zero model calls.
- [ ] Replay reconstructs into a **fresh, isolated sandbox** (a temp dir with its
      own `TransitionLog` + sandbox `SharedFileSystem`); it writes nothing to the
      live data dir, so re-running it is safe and idempotent.
- [ ] It reuses the runtime's handlers (a single shared `register_runtime_handlers`
      / collaborator-`log` `advance` handler) — not a duplicated copy — so
      byte-identity is faithful as handlers evolve.
- [ ] It compares the sandbox `transitions.log` to the live one and asserts
      `recover(sandbox) == recover(live)`; final state is `recover(sandbox)`.
- [ ] Exit codes: `0` reproducible (byte-identical), `1` divergence detected,
      `2` nothing to replay (empty/missing decision log, with a friendly message).
- [ ] `--json` emits `{decisions, modelCalls, finalState, byteIdentical, ok}` for
      the console/CI; the default output is human-readable.

### [REQ-7] Initialize a Data Directory

`jaros init` scaffolds a ready-to-use shared data directory in one command, so a
new user (or the console) is never staring at an empty workspace. It creates the
full directory layout the host and daemon expect — including the `tools/`,
`evals/`, and `schedules/` folders the runtime layout omits — and, with
`--with-examples`, stages the bundled example agents and tools so the console's
Agents & Tools view is populated immediately and jobs can be submitted at once.

#### Acceptance Criteria
- [ ] `jaros init [--data-dir D]` resolves the data dir like every other command
      and creates the complete layout (`state/`, `inbox/`, `outbox/`, `processed/`,
      `failed/`, `artifacts/`, `agents/`, `tools/`, `evals/`, `schedules/`,
      `config/`). It is idempotent: re-running it never errors or clobbers content.
- [ ] `--with-examples` copies the bundled example agents/tools (and example
      evals/schedules) into the new layout so the console shows installed agents and
      `jaros submit`/`jaros eval` work right away; existing files are left intact
      unless `--force` is given.
- [ ] It writes only under the data directory (no socket, no network — consistent
      with REQ-5), prints what it created/staged and a clear next step, and returns
      `0` on success.
- [ ] When the bundled examples cannot be located (e.g. a packaged install without
      them), `--with-examples` still creates the layout and reports that examples
      were unavailable rather than failing.
