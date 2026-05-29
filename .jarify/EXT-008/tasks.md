# Implementation Tasks — Host Control CLI and Shared-FS Ingestion

### [TASK-1] Implement the cross-platform CLI skeleton and data-dir resolution

Provide the command dispatcher and shared-FS targeting.

#### Steps
1. Create `jaros/cli.py` with an `argparse` parser exposing subcommands `serve`, `submit`, `add-agent`, `status`, `watch`, `logs`, and a global `--data-dir`.
2. Implement `resolve_data_dir(args)` using `pathlib.Path` that prefers `--data-dir`, then `JAROS_DATA_DIR`, then `./.jaros-data`; never use platform-specific separators.
3. Wire a `main(argv=None)` entry point and register a console-script `jaros = jaros.cli:main` in `pyproject.toml`. `serve` calls `jaros.daemon.Daemon(...).run()`.

#### Implements
- [REQ-1] Cross-Platform, Filesystem-Only CLI
- [REQ-5] Shared-FS-Only Transport

### [TASK-2] Implement `submit`

Write a job descriptor into the daemon inbox atomically.

#### Steps
1. In `jaros/cli.py`, implement `cmd_submit(kind, input_json, data_dir)` that builds `{id, kind, input}` with a unique id (`uuid4`), validating that `--input` parses as JSON (clear error otherwise).
2. Write to `inbox/.tmp-<id>` then `os.replace()` to `inbox/<id>.json` for atomicity.
3. Print the created job id and path.

#### Implements
- [REQ-2] Submit Jobs

### [TASK-3] Implement `add-agent`

Install a new agent plugin module into the watched folder.

#### Steps
1. In `jaros/cli.py`, implement `cmd_add_agent(path, name, data_dir)` that validates the source `*.py` exists and reads it.
2. Copy it to `plugins/.tmp-<file>` then `os.replace()` to `plugins/<name-or-filename>.py` (atomic install).
3. Print the installed plugin path and the kind it will register (if discoverable).

#### Implements
- [REQ-3] Add Agent Plugins

### [TASK-4] Implement `status`, `watch`, and `logs`

Let the operator observe the running OS purely by reading shared-FS files.

#### Steps
1. In `jaros/cli.py`, implement `cmd_status(data_dir)` that reads `status.json` and pretty-prints it (graceful message if absent).
2. Implement `cmd_watch(data_dir, interval)` that loops printing status and newly-appeared `outbox/*.json` results until `KeyboardInterrupt`.
3. Implement `cmd_logs(data_dir)` that prints the daemon log file if present; ensure none of these open a socket or make a network call.

#### Implements
- [REQ-4] Watch and Status
- [REQ-5] Shared-FS-Only Transport
