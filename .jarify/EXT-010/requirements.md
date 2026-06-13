---
id: EXT-010
title: Administrative & Monitoring Web Console
status: covered
priority: medium
implementation:
  - console/server/index.ts
  - console/server/jarosData.ts
  - console/server/jaros_introspect.py
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
- [x] All console code lives under `console/`, never inside the `jaros/` package.
- [x] Every read and write the console performs is within the shared data
      directory (`status.json`, `inbox/`, `outbox/`, `state/`, `plugins/`,
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
- [x] Submitting `{kind, input}` writes a well-formed descriptor atomically to
      `inbox/` (temp file + rename), with invalid JSON rejected and nothing written.
- [x] The console lists `inbox/`, `processed/`, and `failed/` jobs (with failure
      reasons) and renders `outbox/` results.
- [x] Submission is reachable from the browser via the bridge's job endpoint.

### [REQ-4] Runtime Agent & Tool Management

The operator can view and install plugin agents and custom tools at runtime.

#### Acceptance Criteria
- [x] The console lists the loaded plugin agents (`plugins/`) and custom tools
      (`tools/`).
- [x] A new plugin agent or custom tool can be installed by name + source; it is
      written atomically into the watched folder and loaded on the next daemon tick.
- [x] Module names are validated to prevent path traversal outside the layout.

### [REQ-5] Reproducibility: Decision Log & Replay

The console exposes the reproducibility-by-replay property (EXT-002 / REQ-6) as a
first-class operator workflow.

#### Acceptance Criteria
- [x] The durable decision log (`state/decisions.log`) is rendered as an ordered,
      inspectable list of accepted decisions (kind, source, payload, checksum).
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
