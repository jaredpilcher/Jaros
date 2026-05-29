# Jaros

> An unbreakable, distributed state machine that orchestrates AI agents as **lightweight computing threads** — not bloated microservices.

Jaros completely decouples non-deterministic AI reasoning from deterministic system execution. The LLM is treated purely as an **interchangeable application**, governed by an unyielding architectural harness where all inter-agent communication occurs exclusively through rigid queues and a shared file system.

This is the system's [Prime Directive](.jarify/PRIME-001/intent.md). Every part of the codebase exists to serve it.

## The core idea: the LLM decides *what*, not *how*

A frequent misreading is "the LLM can't make decisions." It can — that *is* the reasoning. The precise rule is:

> **The LLM decides WHAT to propose. The deterministic system decides HOW — and whether — it runs.**

An agent's reasoning may only emit an inert, serializable `Decision` (data). A deterministic validation gate stands between that data and any action. The model is an **advisor** writing recommendations on slips of paper; a deterministic **clerk** (the harness + state machine) reads each slip, checks it against the rulebook, and either executes it exactly or rejects it.

```text
  typical agent:   LLM ── tool call ──► side effect happens   (LLM drives execution)

  jaros:           LLM ── Decision (data) ──► [gate] ──► executor   (executor drives execution)
                                                 │
                                                 └─► may REJECT; LLM has no say
```

## Architecture

Jaros is split into two planes that never merge:

- **Reasoning Plane** (non-deterministic): agents think and propose `Decision` data. The LLM lives here as a pluggable application.
- **Execution Plane** (deterministic): the state machine and harness validate and execute decisions, persist state, and route all communication.

The only channels between an agent and the rest of the system are **rigid queues** and the **shared file system**.

| Subsystem | Spec | What it owns |
| --- | --- | --- |
| Reasoning / Execution Boundary | [EXT-001](.jarify/EXT-001/requirements.md) | Inert `Decision` contract, reasoning boundary, validation gate, executor |
| Distributed State Machine | [EXT-002](.jarify/EXT-002/requirements.md) | Explicit transition model, durable append-only log, crash recovery, replication |
| Agent Thread Runtime | [EXT-003](.jarify/EXT-003/requirements.md) | Cheap agent lifecycle, bounded pool, fault containment |
| Interchangeable LLM Adapter | [EXT-004](.jarify/EXT-004/requirements.md) | Single `LlmClient` interface, pluggable adapters, config-only swap |
| Architectural Harness | [EXT-005](.jarify/EXT-005/requirements.md) | Mediated actions, non-bypassable rules, capability-scoped handles |
| Communication Fabric | [EXT-006](.jarify/EXT-006/requirements.md) | Rigid typed queues, shared FS layout, exclusivity enforcement |

The full system-wide design lives in [`.jarify/PRIME-001/design.md`](.jarify/PRIME-001/design.md).

## Project layout

```text
src/
  core/      EXT-001  Decision, ReasoningBoundary, validation gate
  exec/      EXT-001  deterministic executor
  state/     EXT-002  state model, machine, durable log, recover, replication
  runtime/   EXT-003  AgentThread, AgentPool (lightweight threads)
  llm/       EXT-004  LlmClient interface + pluggable adapters + factory
  harness/   EXT-005  capabilities, rules, Harness
  comms/     EXT-006  Queue, SharedFileSystem
  main.ts             composition root / end-to-end smoke run
scripts/              architecture checks (planes / no-server / comms)
test/integration/     Docker integration runner
.jarify/              SpecFlow/Jarify specifications (the source of intent)
```

## Build, test, run

```bash
npm install
npm run build         # tsc -> dist/
npm test              # build + architecture checks + 84 unit tests
npm start             # run the end-to-end smoke (prints JAROS_SMOKE_OK)
```

### Architecture checks (the structural guardrails)

These run as part of `npm test` and fail the build on violation:

- `npm run check:planes` — no Execution-Plane module may import the LLM/reasoning side (EXT-001/REQ-4).
- `npm run check:no-server` — no agent/runtime code may open a server/port (EXT-003/REQ-3).
- `npm run check:comms` — no direct agent-to-agent / RPC / network calls; only the queue + shared FS are allowed (EXT-006/REQ-5).

### Run on Docker (the default isolation model)

The container is the boundary for the **whole Jaros node**; agents run as threads *inside* it — never one container per agent.

```bash
docker build -t jaros .
docker run --rm jaros            # prints JAROS_SMOKE_OK and exits 0
npm run test:integration         # builds the image, runs the container, asserts success
```

## Building an agent that runs on the Jaros OS

See **[docs/building-agents.md](docs/building-agents.md)** for the full guide. The essence:

1. **Write a `ReasoningBoundary`.** Its only output is inert `Decision` data — it performs no side effects and holds no handles.
2. **Ask the harness for capabilities.** The OS hands the agent *only* the scoped handles you grant (e.g. queue-send, fs-write). It has no ambient access.
3. **Run it as a thread** under the `AgentPool`.
4. **The deterministic side acts:** the gate validates the decision, the executor applies it, the state machine durably transitions, and results are written through the granted handle.

```ts
import { createDecision, type Decision } from "./core/decision";
import type { ReasoningBoundary } from "./core/reasoning-boundary";
import { createLlmClient } from "./llm";

const llm = createLlmClient({ provider: "default" });

// An agent is just a ReasoningBoundary: data in -> Decision data out.
const myAgent: ReasoningBoundary = {
  async decide() {
    const reply = await llm.complete({ prompt: "What next?", context: {} });
    return [
      createDecision({
        id: "decision-1",
        source: "my-agent",
        kind: "advance",
        payload: { advice: reply.text, events: ["START", "COMPLETE"] }, // inert data only
      }),
    ];
  },
};
```

To **constrain** an agent, narrow its grants — that is the whole knob:

```ts
const ctx = harness.spawn("my-agent", { queueSend: queue, fs, fsWrite: true });
// This agent can send on `queue` and write files — and nothing else.
```

`src/main.ts` is a complete, runnable end-to-end example wiring all six planes.

## Specification-driven

Jaros is developed spec-first under `.jarify/`. The Prime Directive (`PRIME-001`) holds the system intent; each feature spec (`EXT-00x`) decomposes one of its tenets into requirements, design, and tasks, with code traced back to requirements via `index.json`. See the Jarify VS Code extension for the live coverage view.
