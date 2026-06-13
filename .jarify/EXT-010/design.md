# Design — Administrative & Monitoring Web Console

The console is a **host-side companion**, in the same category as the Host
Control CLI (EXT-008): it drives and observes a running Jaros OS through the
shared file system only. It is two parts — a thin TypeScript **bridge** and a
React **SPA** — and lives entirely under `console/`, outside the `jaros/`
package. The Jaros node remains serverless: the bridge is an operator tool, not a
component of the node, and the `jaros/**` architecture guardrails are unaffected.

## Topology

```text
   Browser (React SPA)                       Host
   +------------------+   HTTP/SSE   +-----------------------+
   |  Overview · Jobs |  <-------->  |  Bridge (Node + TS)   |
   |  Agents · Replay |   /api/*     |  console/server/*.ts  |
   |  State · Harness |              +-----------+-----------+
   +------------------+                          |  fs read/write only
                                                 v
                            +-------------------- SHARED FILE SYSTEM --------------------+
                            |  status.json   /inbox   /outbox   /state   /plugins /tools |
                            +-----------------------------------------------------------+
                                                 ^
                                                 |  fs read/write only (no socket between them)
                                       +---------+----------+
                                       |  Jaros daemon       |
                                       |  (serverless node)  |
                                       +--------------------+
```

The bridge and the daemon never talk directly — they meet only on the shared
volume, exactly as the CLI and daemon do. The Jaros node opens no socket.

## Bridge responsibilities

- **`jarosData.ts`** — the file-system access layer. Resolves the data dir,
  reads `status.json`, the newline-delimited decision/transition logs, the
  inbox/outbox/failed areas, and the plugins/tools folders; performs atomic
  job submission and module installation (temp file + rename).
- **`index.ts`** — a minimal Node HTTP server (built-ins only) exposing a small
  REST API, a server-sent-events stream for live snapshots, and (in production)
  static SPA serving. It shells out to `jaros` for the parts that must reflect
  the real runtime.

## Keeping `jaros` the single source of truth

The state model, the harness rules, and replay are not re-implemented in
TypeScript. The bridge invokes `jaros` through a small Python helper:

```text
   /api/model   --> python jaros_introspect.py model    --> jaros.state.model
   /api/harness --> python jaros_introspect.py harness   --> jaros.harness.*
   /api/replay  --> python jaros_introspect.py replay D  --> jaros.state.replay
                                                            (executor, no model call)
```

Replay re-registers the deterministic handlers a daemon would have, feeds the
recorded decisions through the executor into a fresh transition log, and reports
the reconstructed state plus a byte-identical comparison against the original
durable log — the EXT-002 / REQ-6 property, made visible to an operator.

## SPA structure

```text
   App (router)
    ├── Layout            sidebar + topbar, live connection pill (SSE snapshot)
    ├── Overview          status, throughput sparkline, pool, zero-infra profile
    ├── Jobs              submit (atomic inbox) · inbox/processed/failed · outbox
    ├── Agents & Tools    list + install plugin agents and custom tools
    ├── Reproducibility   decision log table + one-click replay result
    ├── State Machine     introspected model + live transition log
    └── Harness           mediation rules + roles + refusal audit
```

## Prime Directive consistency

- The console adds **no** server/database/broker to the *node*; it is a host-side
  tool (EXT-008-class). [PRIME-001 / P3]
- It uses only the shared FS as transport to the OS — no agent-to-agent or
  node-to-console socket. [PRIME-001 / REQ-6]
- It surfaces, rather than re-implements, reproducibility-by-replay and
  capability-safety, reading them live from `jaros`. [PRIME-001 / P1, P2]
