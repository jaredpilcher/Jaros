# Architecture

![Jaros architecture: Reasoning Plane proposes decisions; the harness validates and the deterministic Execution Plane runs them](architecture.png)

Jaros is split into two planes that never merge:

- **Reasoning Plane** (non-deterministic): agents think and propose `Decision`
  data. The LLM lives here as a pluggable application.
- **Execution Plane** (deterministic): the durable, replayable state machine and
  its harness validate and execute decisions, persist them, and route all
  communication.

The only channels between an agent and the rest of the system are **rigid queues**
and the **shared file system**. There are no direct agent-to-agent calls.

## The LLM decides *what*, not *how*

A frequent misreading is "the LLM can't make decisions." It can — that *is* the
reasoning. The precise rule is:

> **The LLM decides WHAT to propose. The deterministic system decides HOW — and
> whether — it runs.**

An agent's reasoning may only emit an inert, serializable `Decision`. A
deterministic validation gate stands between that data and any action; the executor
— never the model — drives execution.

```text
  typical agent:   LLM ── tool call ──► side effect happens   (LLM drives execution)

  jaros:           LLM ── Decision (data) ──► [gate] ──► executor   (executor drives execution)
                                                 │
                                                 └─► may REJECT; LLM has no say
```

Because the model holds no control, recording its outputs and replaying them
through the executor reproduces the run exactly — and the model itself is swappable
with zero harness changes.

## Architecture guardrails

Structural constraints are enforced by automated checks (run with `pytest`), so the
design can't silently rot:

| Check | Enforces |
| --- | --- |
| `scripts/check_planes.py` | No Execution-Plane module imports reasoning/LLM code |
| `scripts/check_no_server.py` | No agent/runtime code opens a listening socket or HTTP server |
| `scripts/check_comms.py` | No direct agent-to-agent reference, RPC, or network call |
| `scripts/check_zero_infra.py` | No import of a database driver, message broker, or external server framework |
| `scripts/check_determinism.py` | The core replay path is deterministic — replaying the same decisions agrees every time (the precondition for byte-identical replay) |

## Subsystems

| Subsystem | Spec | What it owns |
| --- | --- | --- |
| Reasoning / Execution Boundary | [EXT-001](../.jarify/EXT-001/requirements.md) | Inert `Decision` contract, reasoning boundary, validation gate, executor |
| Durable, Replayable State Machine | [EXT-002](../.jarify/EXT-002/requirements.md) | Explicit transitions, durable decision log, deterministic replay, crash recovery, bounded multi-node coordination |
| Agent Thread Runtime | [EXT-003](../.jarify/EXT-003/requirements.md) | Cheap agent lifecycle, bounded pool, fault containment |
| Interchangeable LLM Adapter | [EXT-004](../.jarify/EXT-004/requirements.md) | Single `LlmClient` interface, pluggable adapters, config-only swap |
| Architectural Harness | [EXT-005](../.jarify/EXT-005/requirements.md) | Mediated actions, default-deny rules, capability-scoped handles |
| Communication Fabric | [EXT-006](../.jarify/EXT-006/requirements.md) | Rigid typed queues, shared FS layout, exclusivity enforcement |
| Runtime Daemon (OS Boot) | [EXT-007](../.jarify/EXT-007/requirements.md) | Boot, file monitoring, atomic inbox ingestion, zero-infra boot |
| Host Control CLI | [EXT-008](../.jarify/EXT-008/requirements.md) | Command-line management, atomic job submission, agent installer |
| Dynamic Custom Tools | [EXT-009](../.jarify/EXT-009/requirements.md) | Runtime-loaded namespaced tools (`NAME`/`validate`/`execute`) |
| Admin & Monitoring Console | [EXT-010](../.jarify/EXT-010/requirements.md) | Host-side TypeScript + React console: monitor, submit, install, replay |
| Native Agent Scheduling | [EXT-011](../.jarify/EXT-011/requirements.md) | File-based cron + interval + one-shot scheduling, crash-safe, no external cron |
| Read-Only Agent Library | [EXT-012](../.jarify/EXT-012/requirements.md) | Many drop-in read-only agents + tools (health, disk, inventory, text) — run concurrently |
| Agent Evaluation Framework | [EXT-013](../.jarify/EXT-013/requirements.md) | Reproducible, declarative agent evals (`jaros eval`) — input → expected decision/result |

The full system-wide design lives in [`.jarify/PRIME-001/design.md`](../.jarify/PRIME-001/design.md).

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

## Specification-driven with Jarify

Jaros is developed spec-first under `.jarify/`. The Prime Directive (`PRIME-001`)
holds the system intent; each feature spec (`EXT-00x`) decomposes one tenet into
requirements, design, and tasks, with code traced back to requirements via
`index.json`. The directive is the target: where the code lags it, the code
changes — not the directive.
