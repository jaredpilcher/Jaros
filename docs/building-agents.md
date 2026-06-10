# Building Agents that Run on the Jaros OS

This guide shows how to write an agent that runs on Jaros, how the OS constrains it, and how to run it (locally and in a container). It is grounded in the real Python APIs — see the codebase for direct implementations of every plane.

---

## Mental Model

Think of Jaros as an **operating system for agents**:
* **The container** is the OS's machine,
* **The harness** is the OS's kernel,
* **Agents are its threads** — cheap to spawn, cheap to tear down, running concurrently.

An agent never touches the world directly. It *reasons* and emits **inert `Decision` data**; the deterministic kernel validates that data and performs every side effect on the agent's behalf, using only the capabilities the agent was granted at boot time.

> **Golden rule:** The agent decides *what* to propose. The OS decides *how* — and whether — it runs.

---

## What an Agent Is (and Is Not)

An agent **is** a class or object implementing the `ReasoningBoundary` protocol:

```python
# jaros/core/reasoning_boundary.py
from typing import Protocol, runtime_checkable
from jaros.core.decision import Decision

@runtime_checkable
class ReasoningBoundary(Protocol):
    def decide(self, context: object) -> list[Decision]:
        """Reason over context and return inert decisions only."""
        ...
```

An agent **may**:
* Consult the LLM (`LlmClient.complete(...)`) to inform its reasoning.
* Return one or more `Decision` objects (pure, serializable data).

An agent **may NOT**:
* Perform a side effect directly (write a file, mutate state, send a network request).
* Hold a raw queue / file-system / network handle.
* Call another agent.
* Drive control flow or the state machine.

Those are all the kernel's job.

---

## Step 1 — Write the Reasoning

`decide()` returns a list of inert `Decision` data. Build each decision with `create_decision()`, which deep-freezes the payload and rejects anything non-serializable (functions, handles, sets, bytes, custom classes, etc.) recursively.

```python
import os
from jaros.core.decision import create_decision, Decision
from jaros.core.reasoning_boundary import ReasoningBoundary
from jaros.llm import LlmRequest, create_llm_client, LlmClient

class GreeterAgent(ReasoningBoundary):
    def __init__(self) -> None:
        # Treats the LLM purely as an interchangeable client
        self.llm: LlmClient = create_llm_client(
            {"provider": os.getenv("JAROS_LLM_PROVIDER", "default")}
        )

    def decide(self, context: object) -> list[Decision]:
        # Reason using the pluggable LLM
        reply = self.llm.complete(LlmRequest(prompt="Plan the next step."))

        # The model is an advisor. We capture WHAT it proposes as data.
        # The events are what the deterministic state machine drives —
        # the agent does not transition state itself.
        return [
            create_decision(
                id="greeter-1",
                source="greeter",
                kind="advance",
                payload={
                    "advice": reply.text,
                    "model": reply.model,
                    "events": ["START", "COMPLETE"],
                    "artifact_path": "artifacts/greeter-result.json",
                },
            )
        ]
```

---

## Step 2 — Get Capabilities from the Harness (Sandboxing)

The OS spawner mints **only** the scoped handles you grant. The agent has no ambient access to anything else.

```python
from jaros.harness import Harness, GrantSpec
from jaros.comms.queue import Queue
from jaros.comms.fs import SharedFileSystem

# Set up the communication fabric
fs = SharedFileSystem(os.getenv("JAROS_DATA_DIR", ".jaros-data"))
fs.ensure_layout()
queue = Queue(validator=lambda msg: isinstance(msg, dict) and "note" in msg)

harness = Harness()

# Spawn the agent, granting access strictly based on its Role.
# Action permissions must be tied to roles, never ad-hoc to agents!
ctx = harness.spawn("greeter", GrantSpec(
    role="ReporterRole",
    queue=queue,
    fs=fs
))
```

Want a read-only agent? Simply spawn it under `"AnalystRole"`. Want an agent that can only enqueue work? Spawn it under `"QueueSendRole"`. Calling `harness.teardown(agent_id)` invalidates these handles immediately — capabilities are revocable.

---

## Step 3 — Run the Agent as a Lightweight Thread

Agents run under a bounded `AgentPool`. The pool drives each agent thread to completion and frees its execution slot; any thrown error is contained (the agent is marked `FAILED`, siblings and the main process survive).

```python
from jaros.runtime.agent_pool import AgentPool
from jaros.runtime.agent_thread import AgentThread
from jaros.runtime.lifecycle import AgentState

# A bounded concurrent pool (e.g., max 4 concurrent agents)
pool = AgentPool(bound=4)

# An agent factory builds the spawned (unstarted) agent thread.
# Keep a reference so the outcome can be inspected after the pool drains.
spawned: list[AgentThread] = []

def agent_factory() -> AgentThread:
    agent_instance = GreeterAgent()

    # The thread body does the reasoning and returns the decisions
    thread = AgentThread.spawn(id="greeter", body=lambda: agent_instance.decide({}))
    spawned.append(thread)
    return thread

# Submit to the pool (enforces queueing/backpressure if bound is reached)
pool.submit(agent_factory)

# Wait for all pool threads to complete (each is torn down as it finishes)
pool.drain()

# Check outcome cleanly
agent_thread = spawned[0]
if agent_thread.state == AgentState.FAILED:
    print(f"Agent failed with error: {agent_thread.error}")
else:
    print(f"Decisions produced: {[d.id for d in agent_thread.decisions]}")
```

---

## Step 4 — Deterministic System Execution

This is the kernel's job, not the agent's. The validation gate checks the decision payload, the executor validates its kind and dispatches to registered deterministic handlers, the state machine transitions and logs durably, and results are written **through the harness-mediated handles**.

```python
import json
from jaros.core.decision_gate import validate_decision
from jaros.execution.executor import apply, register_handler
from jaros.harness import Action
from jaros.state.machine import commit
from jaros.state.log import TransitionLog
from jaros.state.model import INITIAL_STATE

# Register the deterministic handler for this decision kind (the running
# daemon registers its built-in kinds the same way at boot)
register_handler("advance", lambda decision, **collaborators: decision.payload)

# Emitted decision from the agent thread
decision = agent_thread.decisions[0]

# 1. Validation Gate (EXT-001: rejects non-serializable or malformed)
gated = validate_decision(decision)
if not gated.ok:
    raise ValueError(f"Rejected: {gated.reason}")

# 2. Pluggable Executor (EXT-001: dispatches deterministically to registered kind handler)
applied = apply(gated.value)
if not applied.applied:
    raise RuntimeError(f"Execution failed: {applied.reason}")

payload = applied.output

# 3. Distributed State Machine (EXT-002: drive durable, validated state transitions)
log = TransitionLog(fs.base_dir / "state", "transition.log")
log.ensure()
state = INITIAL_STATE

for event in payload["events"]:
    # Validates + durably logs each event atomically
    state = commit(log, state, event.lower()).state

# 4. Harness Mediation (EXT-005: write result ONLY through mediated, capability-scoped handles)
write_result = harness.request("greeter", Action(
    type="fs.write",
    path=payload["artifact_path"],
    data=json.dumps({"final_state": state}),
))

if not write_result.allowed:
    raise RuntimeError(f"Harness blocked I/O: {write_result.reason}")

# Teardown frees resources and invalidates all capabilities atomically
harness.teardown("greeter")
```

---

## Agent Constraints & Sandboxing

Security in Jaros is enforced in layers inside the Execution Plane, completely outside the LLM.

### 1. Job-Level Context Constraints (Submission Time)
You can guide and restrict agent reasoning at trigger time. Any payload passed to the Host CLI `--input` parameter is supplied directly to the `decide(self, context)` method as `context` dictionary.
```python
# Submission: jaros submit my_agent --input '{"max_depth": 3, "read_only": true}'
class MyAgent(ReasoningBoundary):
    def decide(self, context: dict):
        max_depth = context.get("max_depth", 5)
        # Reason within these bounded limits...
```

### 2. Extensible Validation Gate
Every `Decision` proposed by the Reasoning Plane is sent through a deterministic **Validation Gate** before reaching the executor. Developers can configure, modify, and extend this gate:

#### A. Built-in Structural Gate (Non-Bypassable)
The gate executes a series of hardcoded structural checks first. These **cannot be removed** by developer configuration, guaranteeing that the system remains safe at the baseline:
*   Enforces that the decision is a valid frozen `Decision` instance.
*   Enforces that `id`, `source`, and `kind` are non-empty strings.
*   Enforces that the `payload` is completely recursively JSON-serializable (rejects functions, system handles, bytes, and sets).

#### B. Adding Custom Validation Gates (Policies)
You can register any number of custom, deterministic validation gates. A custom gate is a **pure function** of the `Decision` returning a `ValidationResult`. It must not perform side effects so that the gate remains deterministic.

You can register them programmatically or use the `@register_validator` decorator:

```python
from jaros.core.decision_gate import register_validator, ValidationResult

# Option 1: Decorator registration
@register_validator
def read_only_gate(decision) -> ValidationResult:
    payload = decision.payload if isinstance(decision.payload, dict) else {}
    command = str(payload.get("query", "")).lower()
    
    # Reject mutating database queries at the validation gate
    for mutation in ["drop", "delete", "truncate", "update"]:
        if mutation in command:
            return ValidationResult.reject(f"Mutating command '{mutation}' is blocked!")
            
    return ValidationResult.accept(decision)

# Option 2: Programmatic registration
def allowlist_gate(decision) -> ValidationResult:
    allowed_sources = {"custom_agent", "greeter"}
    if decision.source not in allowed_sources:
        return ValidationResult.reject(f"Source '{decision.source}' is not allowed!")
    return ValidationResult.accept(decision)

register_validator(allowlist_gate)
```

#### C. Short-Circuiting and Decision Normalization
*   **Short-Circuiting**: Custom validators run in registration order. The first validator to return a rejection (`ValidationResult.reject(reason)`) immediately aborts the pipeline; subsequent gates are skipped, and the executor refuses to act on the decision.
*   **Normalization**: A gate can return a normalized or enriched version of the decision by returning `ValidationResult.accept(normalized_decision)`. Subsequent gates and the executor will consume this normalized version.

### 3. Harness Capability Grants
The agent can only perform mediated requests (`harness.request`) if it possesses a corresponding Capability grant inside its `Grants` bundle. The Harness enforces rules (`DEFAULT_RULES`) mapping action types to required Capabilities in a strict, **default-deny** manner.

### 4. Bounded Agent Roles & Configurable Permissions
You group multiple capabilities into logical **Agent Roles** entirely on the host side using [**`config/permissions.json`**](../config/permissions.json) to enforce the principle of least privilege:
*   **Role Configuration**: Define logical roles and their allowed action string keys (e.g. `AnalystRole` allowed `"fs.read"` and `"db.query"`).
*   **Agent-Role Assignments**: Map agent kind registration keys directly to logical roles (e.g., `"custom_agent"` bound to `"AnalystRole"`).
*   **Decoupled & Dynamic Enforcement**:
    The daemon automatically looks up the role from the config assignments at trigger time, spawns the agent context under that role inside the Harness, validates actions dynamically, and safely tears down the context upon job completion.
*   **Zero-Restart Cached Reloading**:
    A high-performance `PolicyManager` monitors file modification times on the host, refreshing the policy memory cache instantly when `permissions.json` changes without requiring a daemon restart.
*   **Layered Local Overrides**:
    To allow local customization without affecting Git history or repository-wide defaults, operators can create a `config/permissions.local.json` file (ignored by Git). The `PolicyManager` automatically detects this file and deep-merges it with `permissions.json` at runtime.

```python
# 1. Spawn-teardown lifecycle automatically driven by the Daemon:
# (Automatically resolves 'ReporterRole' from config assignments)
from jaros.harness import GrantSpec

# 2. Spawner binds the agent to its assigned role
harness.spawn("custom_agent", GrantSpec(role="ReporterRole", fs=fs, queue=queue))

# 3. Teardown clears the grants upon completion
harness.teardown("custom_agent")
```
If the agent attempts to propose a decision for an action not permitted by its assigned role in `permissions.json`, the validation gate immediately blocks it (fails-closed).

---

## Decoupled Agent Communication & Cascading Workflows

To comply with the decoupling boundary, direct agent-to-agent references and RPC are completely blocked. Instead, cascading workflows are created cleanly using two event-driven patterns:

### Pattern A: Inbox-Driven Cascading
An agent triggers the next step in a pipeline by proposing a decision to write a new job descriptor atomically into the monitored `inbox/` directory.

```python
class ResearchAgent(ReasoningBoundary):
    async def decide(self, context):
        llm_response = "Raw data to compile..."
        return [
            create_decision(
                id="trigger-summarizer",
                source="researcher",
                kind="advance",
                payload={
                    "events": ["START"],
                    "artifact_path": "inbox/job_summarizer.json",
                    "data": {
                        "id": "job_summarizer",
                        "kind": "summarizer", # Triggers the summarizer agent kind!
                        "input": {"text": llm_response}
                    }
                }
            )
        ]
```
The Daemon detects this file, resolves `summarizer`, and boots `SummarizerAgent` to continue the pipeline.

### Pattern B: Queue-Driven Cascading
An agent enqueues a validated contract message to a named queue (`jaros.comms.queue`) that a sibling agent dequeues and processes.
```python
class ResearchAgent(ReasoningBoundary):
    async def decide(self, context):
        return [
            create_decision(
                id="enqueue-summary",
                source="researcher",
                kind="advance",
                payload={
                    "events": ["START"],
                    "action": "queue.send",
                    "queue_name": "summarizer-tasks",
                    "message": {"job_id": "job_123", "text": "Content..."}
                }
            )
        ]
```

### Pattern C: Safe Host Command Execution (Decoupled Seam)
If an agent needs to execute a terminal command on the host (e.g. `git status`) and retrieve the stdout, it must never run a process locally inside the container. Instead, it leverages a decoupled event loop via the shared filesystem:
1. **Agent Proposes**: Emits a `Decision` of kind `"host_command"`, detailing the binary and arguments as pure JSON data.
2. **Validation Gate**: Validates the command against an allowlist (e.g. `{"git", "dir", "pytest"}`) at the gate.
3. **Host Runner**: A lightweight runner on the host — the standalone [`jaros-host-runner`](https://github.com/jaredpilcher/jaros-host-runner) companion project — polls `host_inbox/`, safely runs the command against its configured allowlist, and writes the captured results (`returncode`, `stdout`, `stderr`) atomically to `host_outbox/`.
4. **Agent Ingests**: The agent checks the shared folder `host_outbox/` for the result using `fs_read` capability.

### Pattern D: Safe Database (PostgreSQL) Queries
If an agent needs to query a database like PostgreSQL, it must never open direct connection sockets or handle credentials in the Reasoning Plane. Instead, it leverages the pluggable executor dispatch:
1. **Agent Proposes**: Emits a `Decision` of kind `"db_query"`, declaring the query string and parameterized variables as pure JSON data.
2. **Validation Gate**: Checks the query structurally at the gate, blocking mutating queries (`DROP`, `DELETE`) and enforcing strict parameterized safety.
3. **Pluggable Executor**: The Execution Plane dispatches the query to a registered handler which connects securely to PostgreSQL using environment-hidden credentials and returns the serialized JSON results.

### Pattern E: Safe Dynamic Host Tools (Custom Extensions)
If an operator or agent needs a specialized action (e.g. `"db.accounts.read"`), they define a custom Python class dropped into the `.jaros-data/tools/` directory on the host:
1. **Tool Class Signature**: Conforms to the custom tool signature (`NAME`, `validate(decision) -> ValidationResult`, `execute(decision) -> Any`).
2. **Dynamic Ingestion**: The daemon re-scans the `tools/` folder dynamically on tick heartbeats, dynamically loading and registering new tools at runtime without restarts.
3. **Validation & Role Permission**: The tool's `validate()` gate and the role permission check are automatically wired into the Validation Gate, fail-closing immediately if the agent's assigned role is not permitted to call that action namespace inside `permissions.json`.
4. **Deterministic Execution**: The `execute()` method runs on the host-side Execution Plane to execute side-effects and return the serialized output back.

---

## Checklist: Does My Agent Honor the Prime Directive?

Use this checklist to ensure your agent complies with the decoupling seam. The automated architecture checks (`check_planes.py`, `check_no_server.py`, `check_comms.py`) enforce these constraints:

- [ ] **Data-Only Seam**: The agent is a `ReasoningBoundary` whose `decide()` returns only inert `Decision` data.
- [ ] **No Direct Side Effects**: It performs no I/O or state mutation itself — only the harness/executor does on its behalf.
- [ ] **Strict Sandboxing**: It uses only the capability-scoped handles granted by the harness; no raw or ambient file system, queue, or socket access.
- [ ] **Decoupled Comms**: It never references or imports another agent directly (all communication occurs through `Queue` or `SharedFileSystem` layout).
- [ ] **Zero Footprint**: It does not open any listening socket, HTTP server, or process port.
- [ ] **Decoupled LLM**: Its model use is restricted to `LlmClient` interface wrappers, and the LLM has no control over system logic or execution.
