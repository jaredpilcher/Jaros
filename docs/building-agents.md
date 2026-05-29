# Building Agents that Run on the Jaros OS

This guide shows how to write an agent that runs on Jaros, how the OS constrains it, and how to run it (locally and in the Docker container). It is grounded in the real APIs — see [`src/main.ts`](../src/main.ts) for a complete, runnable example that wires every plane.

## Mental model

Think of Jaros as an **operating system for agents**:

- the **container** is the OS's machine,
- the **harness** is the OS's kernel,
- **agents are its threads** — cheap to spawn, cheap to tear down, many at once.

An agent never touches the world directly. It *reasons* and emits **inert `Decision` data**; the deterministic kernel validates that data and performs every effect on the agent's behalf, only through the capabilities the agent was granted.

> **Golden rule:** an agent decides *what* to propose. The OS decides *how* — and whether — it runs.

## What an agent is (and is not)

An agent **is** a `ReasoningBoundary`:

```ts
// src/core/reasoning-boundary.ts
export interface ReasoningBoundary {
  decide(context: unknown): Promise<Decision[]>;
}
```

An agent **may**:
- consult the LLM (`LlmClient.complete(...)`) to inform its reasoning;
- return one or more `Decision` objects (pure, serializable data).

An agent **may NOT**:
- perform a side effect directly (write a file, mutate state, send a network request);
- hold a raw queue / file-system / network handle;
- call another agent;
- drive control flow or the state machine.

Those are all the kernel's job.

## Step 1 — Write the reasoning

`decide()` returns inert `Decision` data. Build each decision with `createDecision`, which deep-freezes the value and rejects anything non-serializable (functions, handles, class instances, etc.).

```ts
import { createDecision, type Decision } from "../src/core/decision";
import type { ReasoningBoundary } from "../src/core/reasoning-boundary";
import { createLlmClient, type LlmClient } from "../src/llm";

const llm: LlmClient = createLlmClient({ provider: process.env.JAROS_LLM_PROVIDER ?? "default" });

export const greeterAgent: ReasoningBoundary = {
  async decide(): Promise<Decision[]> {
    const reply = await llm.complete({ prompt: "Plan the next step.", context: {} });

    // The model is an advisor. We capture WHAT it proposes as data.
    // The `events` are what the deterministic executor will drive — the agent
    // does not transition state itself.
    return [
      createDecision({
        id: "greeter-1",
        source: "greeter",
        kind: "advance",
        payload: {
          advice: reply.text,      // model text is data only; it drives nothing
          model: reply.model,
          events: ["START", "COMPLETE"],
          artifactPath: "artifacts/greeter-result.json",
        },
      }),
    ];
  },
};
```

## Step 2 — Get capabilities from the harness (this is how you constrain it)

The OS mints **only** the scoped handles you grant. The agent has no ambient access to anything else.

```ts
import { Harness } from "../src/harness/harness";
import { Queue } from "../src/comms/queue";
import { SharedFileSystem } from "../src/comms/fs";

const fs = new SharedFileSystem(process.env.JAROS_DATA_DIR ?? ".jaros-data").ensureLayout();
const queue = new Queue<{ note: string }>(
  (v): v is { note: string } => typeof (v as any)?.note === "string",
  "work-queue"
);

const harness = new Harness();

// Grant ONLY what this agent needs. Narrowing the grant narrows the agent.
const ctx = harness.spawn("greeter", {
  queueSend: queue as unknown as Queue<unknown>,
  fs,
  fsWrite: true,
});
```

Want a read-only agent? Drop `fsWrite`. Want one that can only enqueue work? Grant only `queueSend`. Revoking the grant (on `harness.teardown(id)`) makes every handle throw — capabilities are revocable.

## Step 3 — Run the agent as a lightweight thread

Agents run under a bounded `AgentPool`. The pool drives the thread to completion and frees its slot; a thrown error is contained (the agent is marked `failed`, siblings and the process survive).

```ts
import { AgentPool } from "../src/runtime/agent-pool";
import { AgentThread, type AgentRunContext } from "../src/runtime/agent-thread";
import type { Decision } from "../src/core/decision";

const emitted: Decision[] = [];
const pool = new AgentPool(4); // bound = max concurrent agents

const thread = await pool.submit(() =>
  AgentThread.spawn({
    id: "greeter",
    boundary: greeterAgent,
    grants: ctx.grants,
    body: async (run: AgentRunContext) => {
      const produced = await run.boundary.decide(undefined);
      emitted.push(...produced);
      return produced;
    },
  })
);

await pool.drain();
if (thread.state === "failed") throw thread.error;
```

## Step 4 — Let the deterministic side execute the decision

This is the kernel's job, not the agent's. The gate validates, the executor accepts, the state machine durably transitions, and the result is written **through the harness-mediated handle**.

```ts
import { validateDecision } from "../src/core/decision-gate";
import { apply } from "../src/exec/executor";
import { commit } from "../src/state/machine";
import { TransitionLog } from "../src/state/log";
import { INITIAL_STATE, type Event, type State } from "../src/state/model";

const decision = emitted[0];

const gated = validateDecision(decision);          // EXT-001: may REJECT
if (!gated.ok) throw new Error(gated.reason);

const applied = apply(gated.value);                // EXT-001: deterministic dispatch
if (!applied.applied) throw new Error(applied.reason);

const payload = applied.decision.payload as { events: Event[]; artifactPath: string };

// EXT-002: drive the durable, validated state machine
const log = new TransitionLog(`${fs.baseDir}/state`, "transition.log").ensure();
let state: State = INITIAL_STATE;
for (const event of payload.events) {
  state = commit(log, state, event).state;         // validates + durably logs each step
}

// EXT-005/006: write the result ONLY through the granted, harness-mediated handle
const write = await harness.request("greeter", {
  type: "fs.write",
  args: { path: payload.artifactPath, data: JSON.stringify({ finalState: state }) },
});
if (!write.ok) throw new Error(write.reason);

harness.teardown("greeter"); // cheap lifecycle; revokes the grants
```

## Running on the OS

### Locally

```bash
npm run build
node dist/src/main.js          # or: npm start
```

Point the composition root at your agent (or add it to a registry) and it runs as a thread under the pool.

### In the container (default isolation)

The container is the boundary for the whole Jaros node; your agent runs as a thread inside it.

```bash
docker build -t jaros .
docker run --rm jaros
# multiple containers = multiple nodes; the state machine replicates across them (EXT-002)
```

Configuration is environment-driven, so nothing about the agent changes between local and container runs:

| Env var | Purpose | Default |
| --- | --- | --- |
| `JAROS_DATA_DIR` | base dir for the shared FS + durable log | `.jaros-data` (container: `/data`) |
| `JAROS_LLM_PROVIDER` | which `LlmClient` adapter to use | `default` |

## Checklist: does my agent honor the Prime Directive?

- [ ] It is a `ReasoningBoundary` whose `decide()` returns only `Decision` data.
- [ ] It performs no side effects itself — the executor/harness do.
- [ ] It holds only the capabilities the harness granted; no ambient queue/fs/network.
- [ ] It never calls another agent (communicate via the queue or shared FS).
- [ ] It does not open a server or port (it's a thread, not a service).
- [ ] Its LLM use is via `LlmClient` only, and the model drives no control flow.

If all six hold, `npm test` (with `check:planes`, `check:no-server`, `check:comms`) will stay green — the guardrails enforce these structurally.
