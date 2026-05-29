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
from jaros.llm import create_llm_client, LlmClient

class GreeterAgent(ReasoningBoundary):
    def __init__(self) -> None:
        # Treats the LLM purely as an interchangeable client
        self.llm: LlmClient = create_llm_client(
            provider=os.getenv("JAROS_LLM_PROVIDER", "default")
        )

    async def decide(self, context: object) -> list[Decision]:
        # Reason using the pluggable LLM
        reply = await self.llm.complete(prompt="Plan the next step.", context={})

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
from jaros.harness.harness import Harness
from jaros.comms.queue import Queue
from jaros.comms.fs import SharedFileSystem

# Set up the communication fabric
fs = SharedFileSystem(os.getenv("JAROS_DATA_DIR", ".jaros-data")).ensure_layout()
queue = Queue(
    validator=lambda msg: isinstance(msg, dict) and "note" in msg,
    name="work-queue"
)

harness = Harness()

# Spawn the agent, granting ONLY what it needs.
# Narrowing the grant narrows the agent.
ctx = harness.spawn("greeter", {
    "queue_send": queue,
    "fs": fs,
    "fs_write": True
})
```

Want a read-only agent? Simply omit `"fs_write": True`. Want an agent that can only enqueue work? Grant only `"queue_send"`. Calling `harness.teardown(agent_id)` invalidates these handles immediately — capabilities are revocable.

---

## Step 3 — Run the Agent as a Lightweight Thread

Agents run under a bounded `AgentPool`. The pool drives each agent thread to completion and frees its execution slot; any thrown error is contained (the agent is marked `FAILED`, siblings and the main process survive).

```python
from jaros.runtime.agent_pool import AgentPool
from jaros.runtime.agent_thread import AgentThread
from jaros.runtime.lifecycle import AgentState

# A bounded concurrent pool (e.g., max 4 concurrent agents)
pool = AgentPool(bound=4)

# Create an agent factory callable that returns the spawned agent thread
def agent_factory() -> AgentThread:
    agent_instance = GreeterAgent()
    
    # The thread body does the reasoning and returns the decisions
    def run_agent():
        # Run the sync/async decide function
        return asyncio.run(agent_instance.decide({}))
        
    return AgentThread.spawn(
        id="greeter",
        body=run_agent
    )

# Submit to the pool (enforces queueing/backpressure if bound is reached)
agent_thread = pool.submit(agent_factory)

# Wait for all pool threads to complete
pool.drain()

# Check outcome cleanly
if agent_thread.state == AgentState.FAILED:
    print(f"Agent failed with error: {agent_thread.error}")
elif agent_thread.state == AgentState.TORNDOWN:
    print(f"Decisions produced: {[d.id for d in agent_thread.decisions]}")
```

---

## Step 4 — Deterministic System Execution

This is the kernel's job, not the agent's. The validation gate checks the decision payload, the executor validates its kind and dispatches to registered deterministic handlers, the state machine transitions and logs durably, and results are written **through the harness-mediated handles**.

```python
from jaros.core.decision_gate import validate_decision
from jaros.execution.executor import Executor, apply
from jaros.state.machine import commit
from jaros.state.log import TransitionLog
from jaros.state.model import INITIAL_STATE

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

payload = applied.decision.payload

# 3. Distributed State Machine (EXT-002: drive durable, validated state transitions)
log = TransitionLog(f"{fs.base_dir}/state", "transition.log").ensure()
state = INITIAL_STATE

for event in payload["events"]:
    state = commit(log, state, event).state  # Validates + durably logs each event atomically

# 4. Harness Mediation (EXT-005: write result ONLY through mediated, capability-scoped handles)
write_result = harness.request("greeter", {
    "type": "fs.write",
    "args": {
        "path": payload["artifact_path"],
        "data": json.dumps({"final_state": state.name})
    }
})

if not write_result.ok:
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
Developers can register validation policies at the gate that enforce architectural constraints. If an agent attempts to propose a disallowed decision, the gate rejects it immediately before execution occurs.
```python
from jaros.core.decision_gate import register_validator, ValidationResult

def limit_validator(decision) -> ValidationResult:
    if "admin" in str(decision.payload):
        return ValidationResult(ok=False, reason="Admin scope is forbidden")
    return ValidationResult(ok=True, value=decision)

register_validator(limit_validator)
```

### 3. Harness Capability Grants
The agent can only perform mediated requests (`harness.request`) if it possesses a corresponding Capability grant inside its `Grants` bundle. The Harness enforces rules (`DEFAULT_RULES`) mapping action types to required Capabilities in a strict, **default-deny** manner.

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

---

## Checklist: Does My Agent Honor the Prime Directive?

Use this checklist to ensure your agent complies with the decoupling seam. The automated architecture checks (`check_planes.py`, `check_no_server.py`, `check_comms.py`) enforce these constraints:

- [ ] **Data-Only Seam**: The agent is a `ReasoningBoundary` whose `decide()` returns only inert `Decision` data.
- [ ] **No Direct Side Effects**: It performs no I/O or state mutation itself — only the harness/executor does on its behalf.
- [ ] **Strict Sandboxing**: It uses only the capability-scoped handles granted by the harness; no raw or ambient file system, queue, or socket access.
- [ ] **Decoupled Comms**: It never references or imports another agent directly (all communication occurs through `Queue` or `SharedFileSystem` layout).
- [ ] **Zero Footprint**: It does not open any listening socket, HTTP server, or process port.
- [ ] **Decoupled LLM**: Its model use is restricted to `LlmClient` interface wrappers, and the LLM has no control over system logic or execution.
