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

Install a new agent module into the watched folder.

#### Steps
1. In `jaros/cli.py`, implement `cmd_add_agent(path, name, data_dir)` that validates the source `*.py` exists and reads it.
2. Copy it to `agents/.tmp-<file>` then `os.replace()` to `agents/<name-or-filename>.py` (atomic install).
3. Print the installed agent path and the kind it will register (if discoverable).

#### Implements
- [REQ-3] Add Agent Agents

### [TASK-4] Implement `status`, `watch`, and `logs`

Let the operator observe the running OS purely by reading shared-FS files.

#### Steps
1. In `jaros/cli.py`, implement `cmd_status(data_dir)` that reads `status.json` and pretty-prints it (graceful message if absent).
2. Implement `cmd_watch(data_dir, interval)` that loops printing status and newly-appeared `outbox/*.json` results until `KeyboardInterrupt`.
3. Implement `cmd_logs(data_dir)` that prints the daemon log file if present; ensure none of these open a socket or make a network call.

#### Implements
- [REQ-4] Watch and Status
- [REQ-5] Shared-FS-Only Transport

### [TASK-5] Extract reusable runtime handlers (reuse, don't duplicate)

Make the executor handlers a single shared registration so replay re-uses the
exact runtime code path, keeping byte-identity faithful.

#### Steps
1. Create `jaros/execution/handlers.py` with `register_runtime_handlers(*, harness, writer_agent, fs=None, tools_dir=None)` registering an `advance` handler that is a **pure function of `(decision, log)`** (commits each event to the `log` collaborator, returns `finalState`/`logIndices`, mutates no caller state) and an `fs.write` handler closing over `harness`/`writer_agent`; load custom tools from `tools_dir` when given.
2. In `jaros/daemon.py`, replace the inline `_advance_handler`/`_fs_write_handler` registration + `load_custom_tools` call with `register_runtime_handlers(harness=self.harness, writer_agent=_WRITER_AGENT, fs=self.fs, tools_dir=self.fs.base_dir/"tools")`, and set `self.state` from the advance result in `_run_job` (the handler no longer mutates `self.state`).

#### Implements
- [REQ-6] Deterministic Replay Command

### [TASK-6] Implement the `jaros replay` command

Reconstruct a run from the decision log into an isolated sandbox and verify it.

#### Steps
1. In `jaros/cli.py`, add `cmd_replay(data_dir, *, as_json, verbose, stream=None)` that reads `state/decisions.log` via `read_decisions` (exit `2` + friendly message when empty/missing), constructs a fresh sandbox (`tempfile.mkdtemp` with a sandbox `SharedFileSystem` + `TransitionLog`), registers the runtime handlers over the sandbox (`register_runtime_handlers`, a sandbox `Harness`+writer under `FsWriteRole`), and runs `replay(decision_log, executor.apply, log=sandbox_log)` — constructing no `LlmClient`.
2. Compare the sandbox `transitions.log` bytes to the live one and assert `recover(sandbox) == recover(live)`; print human output or, with `--json`, `{decisions, modelCalls:0, finalState, byteIdentical, ok}`; return `0` (byte-identical), `1` (divergence), or `2` (nothing). Register the `replay` subparser, dispatch it in `main()`, and add it to the module docstring.

#### Implements
- [REQ-6] Deterministic Replay Command

### [TASK-7] Test replay (unit + integration + e2e) and update the quickstart

Prove the guarantee and the safety properties, and surface replay in the docs.

#### Steps
1. Create `tests/test_cli_replay.py`: a real recorded run replays byte-identical (`recover(sandbox)==recover(live)`, exit 0); replay succeeds with `jaros.llm.create_llm_client` monkeypatched to raise (no model call); the live data dir is byte-unchanged after replay (side effects sandboxed); empty/missing log → exit 2; a non-deterministic handler → `byteIdentical:false` / exit 1; the `--json` shape.
2. Add a Docker/e2e check (`tests/integration/run_replay_demo.py`) that records a run in a container, then runs `jaros replay` on the host against the shared volume and asserts byte-identical; make `jaros replay` the quickstart's closing "wow" step in `README.md` and `docs/getting-started.md`.

#### Implements
- [REQ-6] Deterministic Replay Command

### [TASK-8] Initialize a data directory (`jaros init`)

Scaffold a ready-to-use data dir, with bundled examples that ship in the wheel.

#### Steps
1. Bundle a starter set under `jaros/_starter/{agents,tools,evals,schedules}` (a `__init__.py` package + the read-only library and swarm hive) and declare it as `package-data` in `pyproject.toml` so it ships in `pip install jaros`.
2. In `jaros/cli.py`, add `cmd_init(data_dir, *, with_examples, force, stream=None)` that creates the full layout (`INIT_DIRS`: the runtime dirs plus `tools/`, `evals/`, `schedules/`, `config/`), idempotently; with `--with-examples`, copy the bundled starter into the data dir via `importlib.resources.files("jaros._starter")` (so it works from a wheel), skipping existing files unless `--force`. Register the `init` subparser (`--with-examples`, `--force`) and dispatch it in `main()`.
3. Add tests in `tests/test_cli.py`: the full layout is created and idempotent; `--with-examples` stages the bundled agents/tools/evals/schedules; verify the wheel includes `jaros/_starter/**`.

#### Implements
- [REQ-7] Initialize a Data Directory
