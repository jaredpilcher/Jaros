---
id: EXT-010
title: Administrative & Monitoring Web Console
status: covered
priority: medium
implementation:
  - console/server/index.ts
  - console/server/jarosData.ts
  - console/server/jaros_introspect.py
  - jaros_console/server.py
  - jaros_console/data.py
  - console/src/api.ts
  - console/src/App.tsx
  - console/src/components/Layout.tsx
  - console/src/components/ui.tsx
  - console/src/pages/Overview.tsx
  - console/src/pages/Jobs.tsx
  - console/src/pages/Agents.tsx
  - console/src/pages/Replay.tsx
  - console/src/pages/StateMachine.tsx
  - console/src/pages/Harness.tsx
---

# Administrative & Monitoring Web Console

A TypeScript + React administrative and monitoring interface for a running Jaros
OS. Everything an operator needs — submit work, install agents/tools, watch live
status, browse the durable decision log, replay it, and inspect the state machine
and harness — is drivable from the browser. Like the Host Control CLI (EXT-008),
this is a **host-side companion**: it communicates with the OS only through the
shared file system. The Jaros node itself stays serverless, so this spec serves
the Prime Directive's zero-infrastructure tenet [PRIME-001 / P3] without
weakening it.

### [REQ-1] Host-Side Console; Serverless Node Preserved

The console is a host-side companion, not part of the Jaros node. It lives
outside the `jaros/` package and reaches the OS exclusively through the shared
data directory, exactly as the CLI does. It may open a localhost port to serve
its own UI (an operator tool), but it adds no server, database, or broker to the
runtime, and the architecture guardrails over `jaros/**` continue to pass.

#### Acceptance Criteria
- [x] All console code lives outside the `jaros/` package — the TypeScript app
      under `console/` and the bundled Python twin under `jaros_console/` (a
      sibling package) — never inside `jaros/`.
- [x] Every read and write the console performs is within the shared data
      directory (`status.json`, `inbox/`, `outbox/`, `state/`, `agents/`,
      `tools/`); it opens no socket to the daemon (there is none).
- [x] `scripts/check_no_server.py`, `check_comms.py`, and `check_zero_infra.py`
      (which scan `jaros/**`) still pass — the node remains serverless.

### [REQ-2] Live Monitoring & Status

The console renders the running OS's live status and streams updates as they
happen.

#### Acceptance Criteria
- [x] An Overview surfaces machine state, processed/failed counts, agent-pool
      snapshot, uptime/tick, and the last result, read from `status.json`.
- [x] Updates stream live (server-sent events) so the operator sees changes
      without manual refresh; the UI degrades gracefully if the data dir is absent.
- [x] A throughput view shows processed-job progress over recent ticks.

### [REQ-3] Job Submission & Inspection

The operator can submit jobs and inspect every stage of their lifecycle, purely
over the shared FS.

#### Acceptance Criteria
- [x] Submitting `{agent, input}` writes a well-formed descriptor atomically to
      `inbox/` (temp file + rename), with invalid JSON rejected and nothing written.
- [x] The console lists `inbox/`, `processed/`, and `failed/` jobs (with failure
      reasons) and renders `outbox/` results.
- [x] Submission is reachable from the browser via the bridge's job endpoint.

### [REQ-4] Runtime Agent & Tool Management

The operator can view and install agents and custom tools at runtime.

#### Acceptance Criteria
- [x] The console lists the loaded agents (`agents/`) and custom tools
      (`tools/`).
- [x] A new agent or custom tool can be installed by name + source; it is
      written atomically into the watched folder and loaded on the next daemon tick.
- [x] Module names are validated to prevent path traversal outside the layout.

### [REQ-5] Reproducibility: Decision Log & Replay

The console exposes the reproducibility-by-replay property (EXT-002 / REQ-6) as a
first-class operator workflow.

#### Acceptance Criteria
- [x] The durable decision log (`state/decisions.log`) is rendered as an ordered,
      inspectable list of accepted decisions (type, source, payload, checksum).
- [x] A one-click action replays the recorded decisions through the deterministic
      executor — with no model call — and reports the reconstructed final state.
- [x] The result indicates whether replay reproduced the run to byte-identical
      state and that zero model calls occurred.

### [REQ-6] Runtime Introspection: State Machine & Harness

The console reflects the *real* runtime model by introspecting `jaros` directly,
never a hard-coded copy.

#### Acceptance Criteria
- [x] The state model (states, events, transitions, initial) is read live from
      `jaros.state.model` and rendered alongside the durable transition log.
- [x] The harness mediation rules (action → required capability) and role →
      capability bundles are read live from `jaros.harness` and rendered.
- [x] The capability-safety framing is shown as structural least-privilege (not an
      adversarial sandbox), with the contained-failure/refusal audit surfaced.

### [REQ-7] Schedule Management

The console exposes native scheduling (EXT-011) as an operator workflow — view,
create, pause/enable, and delete schedules without touching the file system by
hand.

#### Acceptance Criteria
- [x] The console lists the operator schedules (`schedules/*.json`) with their
      trigger, enabled state, and live last/next run (merged from `status.json`).
- [x] An operator can create a schedule (interval / cron / one-shot) that is
      written atomically to `schedules/`, and pause/enable or delete an existing one.
- [x] Schedule names are validated against path traversal; all changes are plain
      shared-FS writes the daemon picks up on its next tick.

### [REQ-8] Run Agent Evaluations

The console runs the agent eval suite (EXT-013) and shows the results, so an
operator can test agents from the browser.

#### Acceptance Criteria
- [x] A one-click action runs `evals/*.json` against the data dir's built-in +
      agents and loaded tools, reporting total/passed/failed and per-case
      checks.
- [x] Each case is expandable to its individual checks (name, ok, detail) and any
      error; the suite status is shown green/failing.
- [x] The run assembles a deterministic environment and surfaces it read-only —
      no model-grading, reproducible results.

### [REQ-9] Guided Onboarding & In-App Documentation

A first-time operator must be able to tell where to start and what to do next
without leaving the console. The console provides a brief first-run tour, a live
get-started checklist, contextual tooltips and per-page intros, and an in-app
help page with pictures and step-by-step CLI instructions.

#### Acceptance Criteria
- [x] On first open, a brief dismissible wizard introduces the core loop (submit
      a job → extend at runtime → replay); it is re-openable from the top bar and
      remembers completion via local storage.
- [x] The Overview shows a live, status-driven "get started" checklist that marks
      each step done as it is completed and links to the relevant page.
- [x] Each page carries a one-line intro explaining its purpose and a "Learn
      more" link into the in-app guide; key controls have hover tooltips.
- [x] An in-app Help page documents every page with screenshots and provides a
      copy-pasteable CLI quickstart, plus links to the full Markdown docs.

### [REQ-10] Bundled, Zero-Node Console for pip Installs

A plain `pip install jaros` — with no Node toolchain and no repo checkout — must
ship a working console. A pure-stdlib Python server, shipped as the sibling
`jaros_console` package (outside `jaros/`), serves the **prebuilt** SPA and the
same REST + SSE API over the shared data directory. It launches from
`jaros serve` by default and from a dedicated `jaros console` command, on an
operator-settable port. Because the server lives outside `jaros/`, the
zero-infrastructure guarantee over `jaros/**` is preserved.

#### Acceptance Criteria
- [x] A `pip install jaros` ships the prebuilt SPA assets and a stdlib server in
      the `jaros_console` package; running the console needs no npm and no
      `console/` checkout.
- [x] The Python server exposes the same routes and response shapes as the
      TypeScript bridge (health, snapshot, status, jobs GET/POST, outbox,
      decisions, transitions, agents/tools GET/POST, schedules GET/POST/DELETE,
      model, harness, replay, evals, and the events SSE stream) and serves the
      SPA with single-port SPA fallback.
- [x] `jaros serve` launches the console by default and `jaros console` runs it
      standalone; both accept `--console-port` (default 5500), and `--no-console`
      (or a missing bundle) degrades gracefully without failing the node.
- [x] The `jaros` package imports no server framework; `check_zero_infra.py` and
      `check_no_server.py` still pass because the server lives in `jaros_console/`.
