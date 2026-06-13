# Jaros

> An unbreakable, distributed state machine that orchestrates AI agents as **lightweight computing threads** — not bloated microservices.

![Jaros OS Docker Demo](docs/demo.gif)

Jaros completely decouples non-deterministic AI reasoning from deterministic system execution. The LLM is treated purely as an **interchangeable application**, governed by an unyielding architectural harness where all inter-agent communication occurs exclusively through rigid queues and a shared file system.

This is the system's [Prime Directive](.jarify/PRIME-001/intent.md). Every part of the codebase exists to serve it.

---

## Architecture

![Jaros Architecture](docs/architecture.png)

Jaros is split into two planes that never merge:

- **Reasoning Plane** (non-deterministic): agents think and propose `Decision` data. The LLM lives here as a pluggable application.
- **Execution Plane** (deterministic): the state machine and harness validate and execute decisions, persist state, and route all communication.

The only channels between an agent and the rest of the system are **rigid queues** and the **shared file system**.

### Decision–Execution Decoupling: The LLM decides *what*, not *how*

A frequent misreading is "the LLM can't make decisions." It can — that *is* the reasoning. The precise rule is:

> **The LLM decides WHAT to propose. The deterministic system decides HOW — and whether — it runs.**

An agent's reasoning may only emit an inert, serializable `Decision` (data). A deterministic validation gate stands between that data and any action. The model is an **advisor** writing recommendations on slips of paper; a deterministic **clerk** (the harness + state machine) reads each slip, checks it against the rulebook, and either executes it exactly or rejects it.

```text
  typical agent:   LLM ── tool call ──► side effect happens   (LLM drives execution)

  jaros:           LLM ── Decision (data) ──► [gate] ──► executor   (executor drives execution)
                                                 │
                                                 └─► may REJECT; LLM has no say
```

### Subsystems

| Subsystem | Spec | What it owns |
| --- | --- | --- |
| Reasoning / Execution Boundary | [EXT-001](.jarify/EXT-001/requirements.md) | Inert `Decision` contract, reasoning boundary, validation gate, executor |
| Distributed State Machine | [EXT-002](.jarify/EXT-002/requirements.md) | Explicit transition model, durable append-only log, crash recovery, replication |
| Agent Thread Runtime | [EXT-003](.jarify/EXT-003/requirements.md) | Cheap agent lifecycle, bounded pool, fault containment |
| Interchangeable LLM Adapter | [EXT-004](.jarify/EXT-004/requirements.md) | Single `LlmClient` interface, pluggable adapters, config-only swap |
| Architectural Harness | [EXT-005](.jarify/EXT-005/requirements.md) | Mediated actions, non-bypassable rules, capability-scoped handles |
| Communication Fabric | [EXT-006](.jarify/EXT-006/requirements.md) | Rigid typed queues, shared FS layout, exclusivity enforcement |
| Runtime Daemon (OS Boot) | [EXT-007](.jarify/EXT-007/requirements.md) | OS server daemon, file monitoring, atomic inbox ingestion |
| Host Control CLI | [EXT-008](.jarify/EXT-008/requirements.md) | Command-line management, atomic job submission, agent plugins installer |

The full system-wide design lives in [`.jarify/PRIME-001/design.md`](.jarify/PRIME-001/design.md).

---

## Project Layout

```text
jaros/
  core/        EXT-001  Decision, ReasoningBoundary, validation gate
  execution/   EXT-001  deterministic executor + pluggable handlers
  state/       EXT-002  state model, machine, durable log, recover, replication
  runtime/     EXT-003  AgentThread, AgentPool (lightweight threads)
  llm/         EXT-004  LlmClient interface + pluggable adapters + factory
  harness/     EXT-005  capabilities, rules, Harness (mediates all I/O)
  comms/       EXT-006  Queue, SharedFileSystem
  registry.py  EXT-007  Agent registration and plugin loading
  daemon.py    EXT-007  Runtime daemon orchestration (the OS boot engine)
  cli.py       EXT-008  Host Control CLI
scripts/                architecture checks (planes / no-server / comms)
tests/                  unit and integration test suites
.jarify/                Jarify specifications (the source of intent)
```

---

## Installation, Test & Run

### 1. Installation
Install the project in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

### 2. Run Tests
Execute the entire test suite, including all unit tests and all architecture checks:

```bash
pytest
```

### 3. Architecture Guardrails
These run automatically with `pytest` and fail the build if a structural constraint is violated:
* **Decoupled Planes**: `python scripts/check_planes.py` — enforces that no Execution-Plane module imports reasoning/LLM code.
* **No Server Footprint**: `python scripts/check_no_server.py` — asserts that no agent/runtime code spins up a listening socket or HTTP server.
* **Exclusive Channels**: `python scripts/check_comms.py` — scans for direct agent-to-agent references, RPC, or network calls (forces queues + shared FS).
* **Zero Infrastructure**: `python scripts/check_zero_infra.py` — asserts that no code imports a database driver, message broker, or external server framework (the runtime needs only files + threads).

### 4. Running the Host CLI & Daemon

Start the Jaros OS Runtime Daemon (the server):
```bash
jaros serve --data-dir .jaros-data
```

From another terminal, use the Host Control CLI to inspect status and submit jobs:
```bash
# Check OS status
jaros status --data-dir .jaros-data

# Submit a job atomically to the OS
jaros submit advance --input '{"events": ["START", "COMPLETE"]}' --data-dir .jaros-data

# Watch OS execution and outbox results in real-time
jaros watch --data-dir .jaros-data
```

---

## Run on Docker (Containerized Isolation)

The container acts as the boundary for the **whole Jaros node**; agents run as lightweight threads *inside* it — never one container per agent.

```bash
# Build the production-ready image
docker build -t jaros .

# Run the long-running daemon container
docker run -d --name jaros_os -v ${PWD}/.jaros-data:/data jaros

# Submit work from the host using the CLI over the shared volume
jaros submit advance --input '{"events": ["START"]}' --data-dir .jaros-data
```

To run the complete automated container integration test:
```bash
python tests/integration/run_container_demo.py
```

---

## Distributed Scheduling Across Containers

Because Jaros uses a **file-system-only control plane**, scheduling is beautifully decoupled, highly scalable, and naturally adaptable to multi-container clusters:

### Pattern A: Decoupled Host-Side Cron
Because job submission is simple, standard schedulers (like Linux `cron`, Kubernetes `CronJob`, or Windows Task Scheduler) can trigger runs:
```text
0 * * * * python -m jaros.cli --data-dir /shared-data submit custom_agent --input '{"topic": "scheduled-run"}'
```

### Pattern B: Multi-Container Ingest (Automatic Load Balancing)
If you run **multiple replica containers** mounted to the same shared directory, the node architecture distributes the load out-of-the-box:
1. **Atomic Ingestion**: Jobs are written atomically using `os.replace` to `inbox/<id>.json`.
2. **Race Prevention**: The first daemon that successfully moves the file from `inbox/` to `processed/` owns and runs the job thread. Sibling nodes skip it.
3. **High Availability**: If a node crashes mid-run, outstanding jobs are safely picked up by surviving nodes.

### Pattern C: Native Python Scheduling Loop
You can run a lightweight background python loop programmatically submitting jobs:
```python
import time
from pathlib import Path
from jaros.cli import cmd_submit

while True:
    cmd_submit("custom_agent", '{"topic": "scheduled-run"}', Path(".jaros-data"))
    time.sleep(600)  # every 10 minutes
```

---

## Safe Host Command Execution (Bypassing the Seam)

If an agent needs to execute a terminal command on the host (e.g. `git status`) and capture its output, it must never invoke process execution inside the container. Instead, it utilizes a decoupled, file-system-only event loop mediated by a host runner:

1. **Agent Proposes**: The agent emits a standard `Decision` of kind `"host_command"` containing the command and arguments as pure JSON data.
2. **Validation Gate**: The Validation Gate checks the proposed command against a strict safety allowlist (e.g. `{"git", "dir", "pytest"}`) and rejects it if unsafe.
3. **Host Runner**: A lightweight background runner on the host polls the shared `.jaros-data/host_inbox/` volume, executes allowed commands locally, and writes outputs (`returncode`, `stdout`, `stderr`) atomically back to `host_outbox/`. The runner is a standalone companion project — see the [`jaros-host-runner`](https://github.com/jaredpilcher/jaros-host-runner) repository — so Jaros core ships no host-execution code and stays a pure file-system control plane.
4. **Agent Ingests**: The agent thread reads the result file from the shared volume once it appears.

See **[docs/agent-playbook.md](docs/agent-playbook.md)** (Protocol 6) for the agent playbook instructions, and **[docs/building-agents.md](docs/building-agents.md)** (Pattern C) for the developer reference.

---

## Building an Agent that Runs on Jaros OS

See **[docs/building-agents.md](docs/building-agents.md)** for the comprehensive guide. The essence:

1. **Write a `ReasoningBoundary`**: It consults the LLM and outputs only inert `Decision` data. It performs no side effects and holds no handles.
2. **Spawn via Harness**: The OS spawner grants only the capability-scoped handles you request.
3. **Run as a Thread**: Under the bounded `AgentPool` to manage concurrency.
4. **Execution Gate validation**: The OS validates, handles state transitions, and writes results.

```python
from jaros.core.decision import create_decision, Decision
from jaros.core.reasoning_boundary import ReasoningBoundary
from jaros.llm import LlmRequest, create_llm_client

# An agent is a ReasoningBoundary: data in -> Decision data out
class GreeterAgent(ReasoningBoundary):
    def __init__(self):
        self.llm = create_llm_client({"provider": "default"})

    def decide(self, context: dict) -> list[Decision]:
        reply = self.llm.complete(LlmRequest(prompt="Greet the user"))

        # Propose the decision as serializable, frozen data only
        return [
            create_decision(
                id="greet-decision",
                source="greeter",
                kind="advance",
                payload={
                    "advice": reply.text,
                    "events": ["START", "COMPLETE"],
                    "artifact_path": "artifacts/greeting.json"
                }
            )
        ]
```

To restrict the agent, simply restrict its capability grants at spawn time:
```python
from jaros.harness.capabilities import GrantSpec

# Grant ONLY the capability to write files inside the layout (and nothing else)
ctx = harness.spawn("greeter", GrantSpec(role="FsWriteRole", fs=shared_fs))
```

---

## Specification-Driven with Jarify

Jaros is developed spec-first under `.jarify/`. The Prime Directive (`PRIME-001`) holds the system intent; each feature spec (`EXT-00x`) decomposes one of its tenets into requirements, design, and tasks, with code traced back to requirements via `index.json`. 
