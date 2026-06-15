# Jaros

> A zero-infrastructure runtime that makes agent systems **reproducible, testable, and capability-safe by construction** — a durable, replayable state machine that orchestrates AI agents as **lightweight computing threads**, not bloated microservices.

![Jaros OS demo: boot, run a built-in agent + two agents + a custom tool, zero infra](docs/demo.gif)

Jaros is the runtime you reach for **the day your agent leaves the demo** — when non-determinism has made it impossible to reproduce, and ambient power has made it unsafe to ship. It delivers that without a server, a database, or a broker: just **files and threads**.

It works by decoupling non-deterministic AI reasoning from deterministic system execution. The LLM is an **interchangeable application** that may only *propose* inert, serializable `Decision` data; a deterministic execution plane decides whether and how each decision runs — and may reject it. This is the system's [Prime Directive](.jarify/PRIME-001/intent.md); every part of the codebase exists to serve it.

---

## What sets Jaros apart

Most agent frameworks let the model drive: a tool call *is* a side effect. That's fine for a demo and a liability in production. Jaros inverts it — the model writes recommendations on slips of paper; a deterministic clerk decides what actually happens. These properties fall out of that design, and they're the whole point:

### 🐝 Reproducible & accountable swarms

The field is moving from one super-agent to **swarms of many small, specialized agents** — and at that scale two failures dominate: you can't **reproduce** what the swarm did, and you can't say **which agent caused it**. Jaros solves both by construction. Every accepted `Decision` is recorded — in one ordered, **hash-chained** log, **tagged with its source agent** — so replaying the log re-executes the *whole hive* to **byte-identical state with zero model calls**, and any failure is **attributed to the exact agent and decision** that produced it. A single agent is just the swarm of one.

![A swarm replay: reconstruct the whole hive byte-identically with no model call, and attribute the bad handoff to the exact agent](docs/swarm-replay.png)

One command replays a hive and names the culprit; the console shows the same per-agent breakdown and attribution beside the durable decision log:

![The console Reproducibility page replaying a swarm — per-agent provenance and the failure attributed to the exact agent/decision](console/docs/screenshots/swarm-reproducibility.png)

Run it yourself: [`examples/swarm/`](examples/swarm/) (a support-triage hive with a seeded bad handoff) and `python tests/integration/run_swarm_replay_demo.py` (the same, end-to-end in Docker). Realized by [EXT-015](.jarify/EXT-015/requirements.md).

### 🔁 Reproducible by replay

The only non-determinism in a run is the model's output, captured as inert `Decision` data and recorded to a durable log **before** any effect is observable. Replaying that log through the deterministic executor reconstructs the run to **byte-identical state — with no model call.** Crash recovery is just a special case of replay.

That means a misbehaving agent run is debuggable like any other software: **pin the decision log, replay, reproduce, fix, re-run identically.** No "it only happens sometimes."

The guarantee rests on one precondition — **executor handlers must be deterministic** functions of the decision and state — and Jaros doesn't just assume it: replay runs twice into isolated state and **flags any non-deterministic handler** (the console shows `deterministic` next to `byte-identical`; `jaros.execution.replays_agree` checks it in CI). Non-determinism that belongs in a run — a clock read, a random choice, external I/O — goes *outside* the handler or is captured as a decision, which is itself recorded and replayed.

![Reproducibility by replay: re-execute recorded decisions to byte-identical state, no model call](docs/replay.gif)

In the [web console](console/) it's one click — browse the durable decision log and replay it, with the reconstructed state, the model-call count, and a byte-identical check shown inline:

![The console's Reproducibility page — the decision log and a replay reconstructing DONE with 0 model calls, byte-identical](console/docs/screenshots/reproducibility.png)

### 🔒 Capability-safe by construction

Agents hold only the scoped handles the harness grants them — no ambient access to the file system, queues, or network. A bug or a bad decision **cannot reach what it was never given**, and every mediated action leaves an auditable record. This is structural least-privilege for blast-radius control (host-level isolation against hostile code stays the host's job — process, container, VPC).

The console makes that legible — the mediation rules, the role→capability bundles, and the refusal/failure audit, all in one view:

![The console's Harness page — mediation rules, role capability bundles, and the refusal audit](console/docs/screenshots/harness.png)

### 📦 Zero-infrastructure

No server, no database, no broker. The whole control plane is the local/shared file system; agents are threads in one process. It runs anywhere files work, and a `check_zero_infra` guardrail fails the build if any code so much as imports a database driver or message broker.

### 🎓 The graduation layer

Jaros sits between a prototype (LangGraph, CrewAI) and heavyweight durable-execution infrastructure (Temporal, Dapr):

| | Prototype frameworks | **Jaros** | Durable-execution infra |
| --- | --- | --- | --- |
| Stand-up cost | none | **none** — files + threads | servers, brokers, databases |
| Reproducibility | best-effort | **record-and-replay to byte-identical state** | workflow replay (heavy) |
| Safety model | ambient tool access | **capability-scoped, default-deny** | varies |
| Model coupling | often hard-wired | **one interface, config swap** | varies |
| Distribution | single process | **single-node-first, bounded multi-node over the FS** | cluster-scale |
| Reach for it… | the first ten lines | **the day you ship** | large orgs at cluster scale |

It is deliberately **not**: a hardened security sandbox, a cluster-scale distributed system, an agent-authorization/governance gateway, a hello-world prototyping framework, or "unbreakable." It claims only what the architecture delivers — durable, crash-recoverable, replayable, and capability-bounded. (See the [Prime Directive](.jarify/PRIME-001/intent.md) for the full "is / is not.")

---

## Why agent builders use it

- **Ship runs you can reproduce.** The decision log turns a flaky prod incident into a deterministic replay you can step through.
- **Contain the blast radius.** Least-privilege handles mean a misbehaving agent touches only what you granted it — and you can audit every action.
- **Stand up nothing.** No infra to provision; `pip install` and run, or one Docker container per node.
- **Swap models freely.** The LLM lives behind one `LlmClient` interface; change provider/model by config, with zero harness changes.
- **Extend at runtime.** Drop an agent into `agents/` or a custom tool into `tools/` and the daemon loads it on the next tick — no restart, no core edits.

---

## Quickstart

For the full day-one-to-production path (first agent → schedule → eval → replay →
console → distributed Docker), see **[docs/getting-started.md](docs/getting-started.md)**.

The whole loop from the CLI — submit work, check status, replay it byte-identically, and run the eval suite (real output, nothing faked):

![A real Jaros CLI session: submit jobs, status, replay --json (0 model calls, byte-identical), and a green eval suite](docs/cli.png)

```bash
pip install -e ".[dev]"
```

Stand up the OS on a data directory, then drive it from another shell — work enters **only** through the shared file system:

```bash
# stage the example agents into the shared volume (see examples/)
mkdir -p .jaros-data/agents .jaros-data/tools
cp examples/agents/*.py .jaros-data/agents/
cp examples/tools/*.py   .jaros-data/tools/

# boot the long-running daemon (the OS)
jaros serve --data-dir .jaros-data
```

```bash
# from another terminal: submit work + watch results, all over the shared FS
jaros submit advance --input '{}'                  --data-dir .jaros-data
jaros submit echo    --input '{"msg": "hello"}'    --data-dir .jaros-data
jaros submit greeter --input '{"name": "Jaros"}'   --data-dir .jaros-data
jaros watch  --data-dir .jaros-data
```

Then the payoff — reconstruct the entire run from the recorded decisions, with **no model call**:

```bash
jaros replay --data-dir .jaros-data
#   replayed 3 recorded decisions (3 applied) - model calls: 0
#     reconstructed state : DONE
#     byte-identical      : yes
#   reproducible: the recorded decisions reconstruct the run exactly, with no model call.
```

Each accepted decision is recorded to `.jaros-data/state/decisions.log`, so the whole run is reproducible by replay. See **[`examples/`](examples/)** for the agents used above, and run the end-to-end smoke tests:

```bash
python tests/integration/run_local_demo.py       # local stand-up (no Docker)
python tests/integration/run_container_demo.py    # full Docker container run
```

---

## Web console

A TypeScript + React administrative and monitoring interface for a running Jaros
OS lives in **[`console/`](console/)** — submit jobs, install agents and
custom tools, watch live status, browse the durable decision log, and **replay
it to byte-identical state** from the browser. It's a host-side companion (a thin
file-system bridge + SPA); the Jaros node itself stays serverless.

The **Overview** is a glanceable NOC view — live machine state, throughput, the agent pool, and the no-server/database/broker profile, all streamed over the file system:

![Jaros Console — Overview](console/docs/screenshots/overview.png)

It reflects the *real* runtime, not a hard-coded copy: the **State Machine** view introspects the model straight from `jaros` and renders the live durable transition log beside it.

![Jaros Console — State Machine: the introspected model and the live transition log](console/docs/screenshots/state-machine.png)

```bash
cd console && npm install
JAROS_DATA_DIR=/tmp/jaros-demo npm run dev        # then open http://localhost:5500
```

A brief first-run tour, a live get-started checklist, per-page intros, hover
tooltips, and an in-app **Help & Docs** page (pictures + a copy-pasteable CLI
quickstart) make it easy to know where to start and what to do next:

![Jaros Console — the first-run tour that guides new operators through the core loop](console/docs/screenshots/tour.png)

The **Overview** greets a new operator with a live get-started checklist that lights up each step as it's done, and every screen documents itself with intros and hover tooltips:

![The get-started checklist on the Overview — step 1 done, "submit your first job" highlighted as the next action](console/docs/screenshots/get-started.png)

The full page gallery and a walkthrough of every page (with pictures) live in
**[docs/console.md](docs/console.md)** and the [console README](console/README.md#screenshots).

---

## How it works

![Jaros architecture: Reasoning Plane proposes decisions; the harness validates and the deterministic Execution Plane runs them](docs/architecture.png)

Jaros is split into two planes that never merge:

- **Reasoning Plane** (non-deterministic): agents think and propose `Decision` data. The LLM lives here as a pluggable application.
- **Execution Plane** (deterministic): the durable, replayable state machine and its harness validate and execute decisions, persist them, and route all communication.

The only channels between an agent and the rest of the system are **rigid queues** and the **shared file system**. There are no direct agent-to-agent calls.

### The LLM decides *what*, not *how*

A frequent misreading is "the LLM can't make decisions." It can — that *is* the reasoning. The precise rule is:

> **The LLM decides WHAT to propose. The deterministic system decides HOW — and whether — it runs.**

An agent's reasoning may only emit an inert, serializable `Decision`. A deterministic validation gate stands between that data and any action; the executor — never the model — drives execution.

```text
  typical agent:   LLM ── tool call ──► side effect happens   (LLM drives execution)

  jaros:           LLM ── Decision (data) ──► [gate] ──► executor   (executor drives execution)
                                                 │
                                                 └─► may REJECT; LLM has no say
```

Because the model holds no control, recording its outputs and replaying them through the executor reproduces the run exactly — and the model itself is swappable with zero harness changes.

---

## Build an agent

An agent is a `ReasoningBoundary`: **data in → `Decision` data out**, no side effects, no handles. Drop the module into the shared-FS `agents/` folder and the daemon registers it at runtime.

```python
import uuid
from jaros.core import create_decision

KIND = "greeter"  # the agent kind the daemon registers

class GreeterBoundary:
    def __init__(self, llm):
        self._llm = llm

    def decide(self, context) -> list:
        name = context.get("name", "world") if isinstance(context, dict) else "world"
        # Propose an inert decision; the executor (not the agent) acts on it.
        return [create_decision(
            id=f"greet-{uuid.uuid4().hex}",
            source="greeter",
            kind="advance",                       # built-in handler drives the state machine
            payload={"events": ["start", "complete"], "note": f"hello {name}"},
        )]

def build(llm):                                   # agent factory the daemon calls
    return GreeterBoundary(llm)
```

To bound an agent, restrict its capability grant at spawn time — a *role* is just a named bundle of capabilities:

```python
from jaros.harness.capabilities import GrantSpec

# Grant ONLY file-write inside the layout; the agent can reach nothing else.
ctx = harness.spawn("greeter", GrantSpec(role="FsWriteRole", fs=shared_fs))
```

A *custom tool* extends what the system can *do*: drop a class exposing `NAME`, `validate()`, and `execute()` into `tools/`, and an agent proposes a decision of that `kind`. See **[`examples/tools/greet_tool.py`](examples/tools/greet_tool.py)** and the full guide in **[docs/building-agents.md](docs/building-agents.md)**.

### Building with an AI agent

Jaros is made to be extended by coding agents. Point any AI coding agent at **[`AGENTS.md`](AGENTS.md)** → **[`agent-kit/`](agent-kit/)** and it has the whole project in one folder: the mental model, a skill for each artifact (agent, tool, eval, schedule), accurate API reference, and runnable templates that pass `jaros eval` unmodified. It can author new Jaros agents and tools and verify them on its own.

---

## Run on Docker

The container is the boundary for the **whole Jaros node**; agents run as threads *inside* it — never one container per agent.

```bash
docker build -t jaros .

# one long-running daemon = one node; work arrives over the mounted volume
docker run -d --name jaros_os -v ${PWD}/.jaros-data:/data jaros

# submit from the host, purely over the shared FS
jaros submit advance --input '{}' --data-dir .jaros-data
```

### Scheduling across containers (single-node-first)

Because the control plane is files only, scheduling is decoupled and needs no broker:

- **Host-side cron** — any scheduler (`cron`, Kubernetes `CronJob`, Task Scheduler) can `jaros submit`.
- **Multi-container ingest** — run several daemons on the same shared dir; they coordinate over the file system. Each job is claimed by an atomic `inbox/<id>.json → claimed/<id>.json` rename: **exactly-once in the happy path** (one node processes it, siblings skip it). The claim is a **lease** the owner heartbeats; if a node crashes, its lease expires and a live sibling reclaims the job to the inbox — so under failure the contract is **at-least-once** (agents are idempotent — the read-only ones trivially so). Bounded multi-node, no broker or consensus service.

---

## Architecture guardrails

Structural constraints are enforced by automated checks (run with `pytest`), so the design can't silently rot:

| Check | Enforces |
| --- | --- |
| `scripts/check_planes.py` | No Execution-Plane module imports reasoning/LLM code |
| `scripts/check_no_server.py` | No agent/runtime code opens a listening socket or HTTP server |
| `scripts/check_comms.py` | No direct agent-to-agent reference, RPC, or network call |
| `scripts/check_zero_infra.py` | No import of a database driver, message broker, or external server framework |
| `scripts/check_determinism.py` | The core replay path is deterministic — replaying the same decisions agrees every time (the precondition for byte-identical replay) |

---

## Subsystems

| Subsystem | Spec | What it owns |
| --- | --- | --- |
| Reasoning / Execution Boundary | [EXT-001](.jarify/EXT-001/requirements.md) | Inert `Decision` contract, reasoning boundary, validation gate, executor |
| Durable, Replayable State Machine | [EXT-002](.jarify/EXT-002/requirements.md) | Explicit transitions, durable decision log, deterministic replay, crash recovery, bounded multi-node coordination |
| Agent Thread Runtime | [EXT-003](.jarify/EXT-003/requirements.md) | Cheap agent lifecycle, bounded pool, fault containment |
| Interchangeable LLM Adapter | [EXT-004](.jarify/EXT-004/requirements.md) | Single `LlmClient` interface, pluggable adapters, config-only swap |
| Architectural Harness | [EXT-005](.jarify/EXT-005/requirements.md) | Mediated actions, default-deny rules, capability-scoped handles |
| Communication Fabric | [EXT-006](.jarify/EXT-006/requirements.md) | Rigid typed queues, shared FS layout, exclusivity enforcement |
| Runtime Daemon (OS Boot) | [EXT-007](.jarify/EXT-007/requirements.md) | Boot, file monitoring, atomic inbox ingestion, zero-infra boot |
| Host Control CLI | [EXT-008](.jarify/EXT-008/requirements.md) | Command-line management, atomic job submission, agent installer |
| Dynamic Custom Tools | [EXT-009](.jarify/EXT-009/requirements.md) | Runtime-loaded namespaced tools (`NAME`/`validate`/`execute`) |
| Admin & Monitoring Console | [EXT-010](.jarify/EXT-010/requirements.md) | Host-side TypeScript + React console: monitor, submit, install, replay |
| Native Agent Scheduling | [EXT-011](.jarify/EXT-011/requirements.md) | File-based cron + interval + one-shot scheduling, crash-safe, no external cron |
| Read-Only Agent Library | [EXT-012](.jarify/EXT-012/requirements.md) | Many drop-in read-only agents + tools (health, disk, inventory, text) — run concurrently |
| Agent Evaluation Framework | [EXT-013](.jarify/EXT-013/requirements.md) | Reproducible, declarative agent evals (`jaros eval`) — input → expected decision/result |

The full system-wide design lives in [`.jarify/PRIME-001/design.md`](.jarify/PRIME-001/design.md).

---

## Project layout

```text
jaros/
  core/        EXT-001  Decision, ReasoningBoundary, validation gate
  execution/   EXT-001  deterministic executor + pluggable handlers; custom tools (EXT-009)
  state/       EXT-002  model, machine, durable transition log, decision log + replay, recover, coordination
  runtime/     EXT-003  AgentThread, AgentPool (lightweight threads)
  llm/         EXT-004  LlmClient interface + pluggable adapters + factory
  harness/     EXT-005  capabilities, rules, Harness (mediates all I/O)
  comms/       EXT-006  Queue, SharedFileSystem
  registry.py  EXT-007  agent registration + agent loading
  daemon.py    EXT-007  runtime daemon (the OS boot engine)
  cli.py       EXT-008  Host Control CLI
examples/               drop-in example agents + a custom tool
scripts/                architecture checks (planes / no-server / comms / zero-infra)
tests/                  unit + integration test suites
.jarify/                Jarify specifications (the source of intent)
```

---

## Specification-driven with Jarify

Jaros is developed spec-first under `.jarify/`. The Prime Directive (`PRIME-001`) holds the system intent; each feature spec (`EXT-00x`) decomposes one tenet into requirements, design, and tasks, with code traced back to requirements via `index.json`. The directive is the target: where the code lags it, the code changes — not the directive.
