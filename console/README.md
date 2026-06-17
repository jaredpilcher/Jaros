# Jaros Console

A TypeScript + React administrative and monitoring web interface for a running
Jaros OS — everything in the Prime Directive, drivable from the browser.

> **The Jaros node stays serverless.** The console is a host-side companion (like
> the CLI or `jaros-host-runner`): a thin TypeScript bridge that reads and writes
> the **shared data directory** over the file system, plus a React SPA. It lives
> outside the `jaros/` package, so it never trips the no-server / zero-infra
> guardrails. The control plane is still just files.

## What you can do

| Page | Covers |
| --- | --- |
| **Overview** | Live machine state, processed/failed, throughput sparkline, agent pool, zero-infra profile, last result. |
| **Jobs** | Submit jobs to the inbox (atomic write); inspect inbox/processed/failed and outbox results. |
| **Agents & Tools** | List loaded agents and custom tools; install new ones into the watched folders at runtime. |
| **Reproducibility** | Browse the durable decision log; **replay** it through the deterministic executor and see it reconstruct the run to byte-identical state — no model call. |
| **State Machine** | The real state model (introspected from `jaros`) and the live durable transition log. |
| **Harness** | Capability-safety: mediation rules, role→capability bundles, and the refusal/failure audit. |

## Screenshots

Live captures from a running console (regenerate with `npm run screenshots`).

**First-run tour** — a brief wizard guides new operators through the core loop:

![First-run tour](docs/screenshots/tour.png)

**Get started** — a live checklist on the Overview shows exactly what to do next:

![Get-started checklist](docs/screenshots/get-started.png)

**Overview** — live status, throughput, agent pool, and the zero-infra profile:

![Overview](docs/screenshots/overview.png)

**Reproducibility** — browse the decision log and replay it to byte-identical state, with no model call:

![Reproducibility](docs/screenshots/reproducibility.png)

**State Machine** — the real model introspected from `jaros`, plus the live transition log:

![State Machine](docs/screenshots/state-machine.png)

**Help & Docs** — an in-app guide: every page with pictures plus a CLI quickstart:

![Help & Docs](docs/screenshots/help.png)

More under [`docs/screenshots/`](docs/screenshots/): Jobs, Agents & Tools,
Schedules, Evaluations, Harness, and a hover tooltip. A full walkthrough lives in
[docs/console.md](../docs/console.md).

## Run it

The console talks to a Jaros data directory. Point it at one and run a daemon
against the **same** directory (use a throwaway dir, never one in use):

```bash
# terminal 1 — a Jaros OS on a throwaway data dir
export JAROS_DATA_DIR=/tmp/jaros-demo
jaros serve

# terminal 2 — the console
cd console
npm install
JAROS_DATA_DIR=/tmp/jaros-demo npm run dev      # web on :5500, bridge on :7373
```

Open http://localhost:5500.

### Production build

```bash
npm run build          # type-check + bundle the SPA to dist/
JAROS_DATA_DIR=/tmp/jaros-demo npm start        # bridge serves dist/ + API on :7373
```

## Configuration

| Env var | Default | Meaning |
| --- | --- | --- |
| `JAROS_DATA_DIR` | `.jaros-data` | The shared data directory to monitor/drive. |
| `JAROS_CONSOLE_API_PORT` | `7373` | Bridge server port. |
| `JAROS_CONSOLE_WEB_PORT` | `5500` | Vite dev server port. |
| `JAROS_PYTHON` | `python` | Interpreter used to introspect `jaros` (state model, harness) and run replay. |

The bridge shells out to `jaros` (via `server/jaros_introspect.py`) for the live
state model, harness rules, and deterministic replay, so the console always
reflects the real runtime — never a hard-coded copy.
