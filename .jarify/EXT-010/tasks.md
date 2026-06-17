# Implementation Tasks — Administrative & Monitoring Web Console

### [TASK-1] Scaffold the host-side console package

Stand up a TypeScript + React project under `console/`, outside the `jaros/`
package, so the node stays serverless and the guardrails are unaffected.

#### Steps
1. Create `console/package.json` (type: module) with React + Vite + tsx + concurrently and scripts `dev`/`build`/`start`/`typecheck`; add `console/tsconfig.json`, `console/vite.config.ts` (proxy `/api` → bridge port), `console/index.html`, and `console/.gitignore` (ignore `node_modules/`, `dist/`).
2. Add `console/README.md` documenting that the console is a host-side companion talking to the shared data dir, with run instructions and env vars (`JAROS_DATA_DIR`, `JAROS_CONSOLE_API_PORT`, `JAROS_PYTHON`).

#### Implements
- [REQ-1] Host-Side Console; Serverless Node Preserved

### [TASK-2] Implement the shared-FS data access layer

Provide a file-system-only access layer the bridge uses to read and write the
shared data directory.

#### Steps
1. Create `console/server/jarosData.ts` with `resolveDataDir()` (from `--data-dir=`/`JAROS_DATA_DIR`/default) and safe readers: `getStatus()`, `getDecisions()`/`getTransitions()` (newline-delimited JSON, torn-trailing tolerant), `getJobs()` (inbox/processed/failed + `.reason`), `getOutbox()`, `getAgents()`/`getTools()`.
2. Add atomic writers: `submitJob(kind, input)` (temp file + `renameSync` into `inbox/`) and `installModule(area, name, source)` with a name guard rejecting `/`, `\\`, and leading `.` to prevent traversal.

#### Implements
- [REQ-1] Host-Side Console; Serverless Node Preserved
- [REQ-3] Job Submission & Inspection
- [REQ-4] Runtime Agent & Tool Management

### [TASK-3] Implement the bridge HTTP server with live SSE

Expose a small REST + server-sent-events API over the data dir and serve the SPA.

#### Steps
1. Create `console/server/index.ts` (Node built-in `http`) routing `/api/health`, `/api/snapshot`, `/api/status`, `/api/jobs` (GET/POST), `/api/outbox`, `/api/decisions`, `/api/transitions`, `/api/agents` (GET/POST), `/api/tools` (POST); POST `/api/jobs` parses + validates the JSON `input` before `submitJob`.
2. Add an `/api/events` SSE endpoint that pushes a `snapshot()` (status + counts) every second to connected clients, plus static `dist/` serving with SPA fallback.

#### Implements
- [REQ-2] Live Monitoring & Status
- [REQ-3] Job Submission & Inspection

### [TASK-4] Implement the jaros introspection + replay helper

Keep `jaros` the single source of truth for the model, harness, and replay.

#### Steps
1. Create `console/server/jaros_introspect.py` with `model` (dump `STATES`/`EVENTS`/`INITIAL_STATE`/transitions) and `harness` (dump `DEFAULT_RULES` action→capability and `BUILTIN_ROLES`) commands emitting JSON.
2. Add a `replay <data_dir>` command that registers the deterministic `advance`/`fs.write` handlers, loads custom tools, replays `state/decisions.log` through `jaros.execution.executor.apply` into a fresh `TransitionLog`, and returns `{decisions, applied, finalState, byteIdentical, modelCalls: 0, ok}`.
3. In `console/server/index.ts`, add `/api/model`, `/api/harness` (cached), and POST `/api/replay` routes that `execFile` the helper via `JAROS_PYTHON` and return its JSON.

#### Implements
- [REQ-5] Reproducibility: Decision Log & Replay
- [REQ-6] Runtime Introspection: State Machine & Harness

### [TASK-5] Build the SPA shell, design system, and API client

Create the app frame, the dark NOC design system, and the typed client + live hook.

#### Steps
1. Create `console/src/theme.css` (CSS-variable design system: deep-slate dark theme, terminal-green semantics, monospace data, cards/pills/tables), `console/src/main.tsx` (router root), and `console/src/components/ui.tsx` (`Card`, `Stat`, `Pill`, `Sparkline`, `Json`, `StateBadge`).
2. Create `console/src/api.ts` (typed `api.*` fetch wrappers + `useLiveSnapshot()` EventSource hook), `console/src/components/Layout.tsx` (sidebar nav with live counts + topbar connection pills), and `console/src/App.tsx` (routes to each page).

#### Implements
- [REQ-2] Live Monitoring & Status

### [TASK-6] Implement Overview and Jobs pages

The live dashboard and the job lifecycle workflow.

#### Steps
1. Create `console/src/pages/Overview.tsx` rendering machine state, processed/failed/decisions stats, a throughput `Sparkline` accumulated from live snapshots, the agent-pool panel, the zero-infra profile, and the last result.
2. Create `console/src/pages/Jobs.tsx` with a submit form (kind + JSON input, with `advance`/`echo`/`greeter` presets) posting to `/api/jobs`, plus inbox/processed/failed lists and an outbox result viewer.

#### Implements
- [REQ-2] Live Monitoring & Status
- [REQ-3] Job Submission & Inspection

### [TASK-7] Implement Agents & Tools, Reproducibility, State Machine, and Harness pages

The runtime-extension, reproducibility, and introspection surfaces.

#### Steps
1. Create `console/src/pages/Agents.tsx` (list loaded agents/tools; install an agent or tool by name + source via `/api/agents`/`/api/tools`, with templates) and `console/src/pages/Replay.tsx` (decision-log table with expandable payloads + a Replay button rendering the `/api/replay` result: decisions, reconstructed state, byte-identical, model calls).
2. Create `console/src/pages/StateMachine.tsx` (introspected states/transitions + live transition log) and `console/src/pages/Harness.tsx` (mediation rules, role→capability bundles, and the refusal/failure audit).

#### Implements
- [REQ-4] Runtime Agent & Tool Management
- [REQ-5] Reproducibility: Decision Log & Replay
- [REQ-6] Runtime Introspection: State Machine & Harness

### [TASK-8] Add an end-to-end console smoke test

Prove the whole console stack drives a live Jaros over the shared FS.

#### Steps
1. Create `console/smoke.mjs` that boots a daemon + the bridge on a throwaway data dir (staging the example agents), submits `advance`/`echo`/`greeter` through `/api/jobs`, and asserts processed counts, decision-log contents, model/harness introspection, and a successful replay (`finalState == DONE`, `modelCalls == 0`).
2. Verify `npm run typecheck` and `npm run build` pass and the smoke prints PASS; tear down the daemon, bridge, and temp dir.

#### Implements
- [REQ-1] Host-Side Console; Serverless Node Preserved
- [REQ-5] Reproducibility: Decision Log & Replay

### [TASK-9] Ship a bundled, zero-Node Python console

Make `pip install jaros` self-sufficient: a pure-stdlib server, shipped beside
the `jaros` package, that serves the prebuilt SPA and the same API with no Node.

#### Steps
1. Create the sibling `jaros_console` package: `data.py` (port of
   `jarosData.ts` — `resolve_data_dir`, safe JSON/NDJSON readers, `get_status`/
   `get_jobs`/`get_outbox`/`get_decisions`/`get_transitions`/`get_agents`/
   `get_tools`/`get_schedules`/`snapshot`, atomic `submit_job`/`install_module`/
   `write_schedule`/`delete_schedule` with a path-traversal name guard, plus the
   in-process `do_model`/`do_harness`/`do_replay`/`do_evals` from
   `jaros_introspect.py`) and `server.py` (a `ThreadingHTTPServer` whose handler
   mirrors every `console/server/index.ts` route and serves `_dist/` with SPA
   fallback and an `/api/events` SSE loop).
2. Bundle the prebuilt SPA into `jaros_console/_dist/` and declare it as
   package-data in `pyproject.toml` so it ships in the wheel; add
   `scripts/sync_console_dist.py` to rebuild + refresh it from `console/dist/`.
3. Wire `jaros/cli.py`: lazily import `jaros_console` to launch the server on a
   daemon thread from `jaros serve` (default-on, `--console-port`, `--no-console`),
   and add a `jaros console` subcommand that runs it standalone against the
   resolved data dir; degrade gracefully when the bundle/port is unavailable.
4. Add `tests/test_console_server.py` exercising the stdlib server end to end
   (health, snapshot, submit→inbox, static SPA fallback) on an ephemeral port.

#### Implements
- [REQ-10] Bundled, Zero-Node Console for pip Installs
- [REQ-1] Host-Side Console; Serverless Node Preserved
