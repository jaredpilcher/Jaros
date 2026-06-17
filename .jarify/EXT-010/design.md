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
                            |  status.json   /inbox   /outbox   /state   /agents /tools |
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
  inbox/outbox/failed areas, and the agents/tools folders; performs atomic
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
    ├── Agents & Tools    list + install agents and custom tools
    ├── Reproducibility   decision log table + one-click replay result
    ├── State Machine     introspected model + live transition log
    └── Harness           mediation rules + roles + refusal audit
```

## Bundled Python console (zero-Node, for pip installs)

The TypeScript bridge needs Node + a `console/` checkout. For a plain
`pip install jaros`, a **pure-stdlib Python twin** ships in the wheel as the
sibling `jaros_console` package — the same routes and response shapes, the same
prebuilt React bundle, served on a single localhost port. It stays *outside*
`jaros/` for the same reason the TS bridge does: `jaros/**` must import no server
framework (`check_zero_infra` forbids `http.server`), so the server cannot live
inside the node's package.

```text
   Browser (same prebuilt React SPA)
   +------------------+   HTTP/SSE on one port (default 5500)
   |  /  +  /api/*    |  <───────────────────────────────┐
   +------------------+                                   │
                                                          v
                         +───────────────────────────────────────────+
                         |  jaros_console  (sibling pkg, in the wheel) |
                         |   server.py   http.server: SPA + /api       |
                         |   data.py     shared-FS reads/writes +      |
                         |               in-process jaros introspection|
                         |   _dist/      prebuilt SPA (package-data)   |
                         +───────────────────┬───────────────────────-+
                                             |  fs read/write only
                                             v
                         +──────── SHARED FILE SYSTEM ────────+
                         |  status.json /inbox /outbox /state |
                         +────────────────────────────────────+

   jaros serve  ──launches──>  jaros_console.serve_console(background=True)
   jaros console ──runs standalone──>  serve_console(...)   (--console-port)
```

`jaros/cli.py` imports `jaros_console` only lazily, at launch time, so the
`jaros` package itself still imports no server framework and the guardrails over
`jaros/**` keep passing. If Node *is* present and a `console/` checkout exists,
the TS dev bridge remains available for console development; the bundled Python
server is what makes `pip install` self-sufficient.

## Prime Directive consistency

- The console adds **no** server/database/broker to the *node*; it is a host-side
  tool (EXT-008-class), whether served by the Node bridge or the bundled Python
  twin. [PRIME-001 / P3]
- It uses only the shared FS as transport to the OS — no agent-to-agent or
  node-to-console socket. [PRIME-001 / REQ-6]
- It surfaces, rather than re-implements, reproducibility-by-replay and
  capability-safety, reading them live from `jaros`. [PRIME-001 / P1, P2]
