---
id: EXT-008
title: Host Control CLI and Shared-FS Ingestion
status: covered
priority: high
implementation:
  - jaros/cli.py
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

### [REQ-3] Add Agent Plugins

`add-agent` installs a new agent module into the watched `plugins/` folder.

#### Acceptance Criteria
- [ ] `jaros add-agent <path-to-module.py> [--name <kind>]` copies the module into `plugins/` so the daemon can load it.
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
