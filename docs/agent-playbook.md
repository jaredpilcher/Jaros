# Jaros AI Agent Playbook: Integration & Operations Manual

Welcome, Agent. This document is your technical blueprint and operational playbook for interacting with the **Jaros Agent Operating System**. 

Use the protocols, command schemas, and Python templates below to verify system health, boot the OS, develop new agents, trigger jobs, and drive cascading workflows.

---

## 1. Core Architectural Constraints: The Seam

Before executing any commands, you must understand the **Prime Directive** governing this system:

```text
  Reasoning Plane (Non-Deterministic) ──[ Inert Decision JSON ]──► Execution Plane (Deterministic)
  (LLMs / Pluggable Agents)                                         (Harness / State Machine / I/O)
```

1.  **Strict Decoupling**: You (the reasoning entity) propose *what* to do by emitting a list of inert, JSON-serializable `Decision` objects. You have **zero ambient power** to write files, run network requests, or mutate states directly.
2.  **Mediation**: The deterministic Execution Plane (the Harness and Validation Gate) validates your proposed decisions and executes the safe side effects on your behalf.
3.  **No Direct Comms**: You must never call another agent directly. All inter-agent cascading is event-driven via queues or shared filesystem inbox files.

---

## 2. Protocol 1: Verify & Boot Jaros OS (Host System)

If you are running in another repository or context on the host machine, execute these checks in sequence to ensure the Jaros container is running:

### Step A: Check if Docker is available
```bash
docker --version
```

### Step B: Check if the Jaros container is running
```bash
docker ps -f name=jaros_os
```

### Step C: Boot Jaros in Docker (if not running)
If the container does not appear in the active process list, boot it in the background. You **must** bind-mount a host folder to `/data` so that you can communicate with the daemon via the shared filesystem control plane:

```bash
# 1. Create the host directory if it does not exist
mkdir -p .jaros-data

# 2. Boot the daemon in the background (inheriting the host .env file if present)
docker run -d \
  --name jaros_os \
  --env-file .env \
  --mount type=bind,source="$(pwd)"/.jaros-data,target=/data \
  jaros
```

---

## 3. Protocol 2: Develop and Install a New Agent

To create and register a new agent kind inside Jaros, you must write a Python script conforming to the `ReasoningBoundary` plugin structure.

### Step A: Create the Agent Plugin Script (`custom_agent.py`)
Write your agent reasoning code exactly like this template. Keep it standard-library-only.

```python
import json
from jaros.core import create_decision

# 1. Define the unique kind registration key
KIND = "custom_agent"

# 2. Implement the builder function
def build(llm):
    class CustomAgent:
        def decide(self, context: dict) -> list:
            """Reason over the context and return a list of decisions only."""
            # Use 'context' payload passed from the trigger job to construct your prompts
            prompt_input = context.get("task", "Plan next step")
            
            # Consult the interchangeable LLM client
            reply = llm.complete(prompt=prompt_input)
            
            # Propose the final outcome as inert, frozen JSON data only
            return [
                create_decision(
                    id="dec-1",
                    source=KIND,
                    kind="advance",
                    payload={
                        "events": ["start", "complete"],
                        "note": reply.text,
                        "artifact_path": "artifacts/custom_agent_result.json"
                    }
                )
            ]
    return CustomAgent()
```

### Step B: Install the Agent atomically via the Host CLI
Execute the `add-agent` subcommand from the host. This copies the script into the watched `plugins/` directory atomically:

```bash
python -m jaros.cli --data-dir .jaros-data add-agent path/to/custom_agent.py --name custom_agent
```
The running Docker container daemon will instantly detect the file, load it, and make `custom_agent` available for execution.

---

## 4. Protocol 3: Trigger an Agent & Pass Prompt Context

To execute an installed agent, you submit a job descriptor atomically into the shared filesystem. The daemon will ingest it, run your agent thread, validate its gate, transition state, and write the output.

### Step A: Submitting via the Host CLI (Recommended)
Pass prompt contexts or goal arguments directly inside the `--input` JSON option:

```bash
python -m jaros.cli --data-dir .jaros-data submit custom_agent --input '{"task": "Evaluate user security parameters"}'
```

### Step B: Submitting via Direct File Write (Decoupled/Cron)
If the CLI is not available in your execution environment, you can trigger the job by writing the JSON descriptor file atomically directly to the shared inbox volume:

```python
import json
import os
import uuid
from pathlib import Path

# Resolve data directory
data_dir = Path(".jaros-data")
job_id = uuid.uuid4().hex

# Define job descriptor
job = {
    "id": job_id,
    "kind": "custom_agent",  # The agent plugin kind to trigger
    "input": {"task": "Verify transaction logs"}  # Prompt context
}

# Atomic write: write to temp file first, then os.replace() to prevent daemon partial-read races
temp_file = data_dir / f"inbox/.tmp-{job_id}"
target_file = data_dir / f"inbox/{job_id}.json"

with open(temp_file, "w", encoding="utf-8") as f:
    json.dump(job, f)

os.replace(temp_file, target_file)
print(f"Triggered job {job_id}")
```

---

## 5. Protocol 4: Designing Cascading Event-Driven Workflows

Under Jaros, agents create pipelines by **passing messages** rather than invoking other agents directly. You can create a cascading workflow using two patterns:

### Pattern A: Inbox-Driven Cascade (Event Pipelines)
Write your agent's proposed decision payload to output a job descriptor file directly into the `inbox/` layout folder.

```python
# Inside Agent A's decide() method:
return [
    create_decision(
        id="trigger-agent-b",
        source="agent_a",
        kind="advance",
        payload={
            "events": ["START"],
            # Harness will safely write this file on behalf of Agent A
            "artifact_path": "inbox/job_agent_b_123.json",
            "data": {
                "id": "job_agent_b_123",
                "kind": "agent_b",  # Triggers Agent B!
                "input": {"data_from_a": "Data content..."}
            }
        }
    )
]
```

### Pattern B: Queue-Driven Cascade (Structured Fabrics)
Propose enqueuing a structured, schema-validated message to a named queue that Agent B is listening to:

```python
# Inside Agent A's decide() method:
return [
    create_decision(
        id="send-to-queue",
        source="agent_a",
        kind="advance",
        payload={
            "events": ["START"],
            "action": "queue.send",
            "queue_name": "agent-b-tasks",
            "message": {"task_id": "task_abc", "content": "Payload..."}
        }
    )
]
```

---

## 6. Protocol 5: Monitoring Status and Outbox Results

To monitor execution progress and read final outbox results cleanly:

### Step A: Read status metadata
Query the overall running state, processed counts, and active pool threads:
```bash
python -m jaros.cli --data-dir .jaros-data status
```
Or read `status.json` directly from the shared volume:
```python
import json
status = json.loads(open(".jaros-data/status.json").read())
print(f"Processed: {status['processed']}, State: {status['state']}")
```

### Step B: Watch job outputs
Loop-read the `outbox/` layout directory for results:
```bash
python -m jaros.cli --data-dir .jaros-data watch
```
Or check the specific job result file:
```python
result = json.loads(open(".jaros-data/outbox/a7780878b7464b72a7ad8ec7978cac5b.json").read())
print(result["result"])
```
