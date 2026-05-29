/**
 * End-to-end smoke run that wires every Jaros plane into one deterministic
 * pipeline and proves the whole system runs.
 *
 * This is integration glue (the composition root), not a feature spec — it is
 * the single place permitted to know about every plane at once. The planes
 * themselves stay decoupled; here we merely assemble them in the order the
 * Prime Directive design demands:
 *
 *   FS + Queue (EXT-006)            shared, sanctioned channels
 *     -> LlmClient (EXT-004)        interchangeable reasoning advisor
 *     -> Harness + grants (EXT-005) capability-scoped mediation
 *     -> ReasoningBoundary          emits inert Decision DATA only
 *     -> AgentThread / AgentPool    lightweight thread runtime (EXT-003)
 *     -> validateDecision gate      deterministic acceptance (EXT-001)
 *     -> executor apply             deterministic dispatch (EXT-001)
 *     -> state machine + log        durable, validated transition (EXT-002)
 *     -> artifact write             durable result via granted handle (EXT-006)
 *
 * Architectural invariant respected end to end: reasoning only produces a
 * Decision (data); every side effect (state transition, artifact write) is
 * performed by the deterministic execution side and only through the agent's
 * granted handles mediated by the harness.
 */

import { Queue } from "./comms/queue";
import { SharedFileSystem, DEFAULT_BASE_DIR } from "./comms/fs";
import { createLlmClient, type LlmClient } from "./llm";
import { Harness } from "./harness/harness";
import { AgentPool } from "./runtime/agent-pool";
import { AgentThread } from "./runtime/agent-thread";
import type { AgentRunContext } from "./runtime/agent-thread";
import type { ReasoningBoundary } from "./core/reasoning-boundary";
import { createDecision, type Decision } from "./core/decision";
import { validateDecision } from "./core/decision-gate";
import { apply } from "./exec/executor";
import { commit } from "./state/machine";
import { TransitionLog } from "./state/log";
import { INITIAL_STATE, type Event, type State } from "./state/model";

/** Compact summary printed alongside the success marker. */
interface SmokeSummary {
  readonly finalState: State;
  readonly decisionKind: string;
  readonly artifactPath: string;
  readonly llmProvider: string;
}

const OK_MARKER = "JAROS_SMOKE_OK";
const FAIL_MARKER = "JAROS_SMOKE_FAIL";

async function runSmoke(): Promise<SmokeSummary> {
  // --- EXT-006: shared comms fabric (queue + canonical FS layout) ----------
  const baseDir = process.env.JAROS_DATA_DIR || DEFAULT_BASE_DIR;
  const fs = new SharedFileSystem(baseDir).ensureLayout();
  fs.validateLayout();

  // A rigid, typed queue. Its contract: a record carrying a string note. We
  // grant the agent a send handle onto it, exercising the queue plane.
  const queue = new Queue<{ note: string }>(
    (v): v is { note: string } =>
      typeof v === "object" &&
      v !== null &&
      typeof (v as { note?: unknown }).note === "string",
    "smoke-queue"
  );

  // --- EXT-004: interchangeable LLM advisor (selected by config/env) -------
  const llmProvider = process.env.JAROS_LLM_PROVIDER || "default";
  const llm: LlmClient = createLlmClient({ provider: llmProvider });

  // --- EXT-005: harness mints ONLY the capabilities the agent needs --------
  const harness = new Harness();
  const ctx = harness.spawn("smoke-agent", {
    queueSend: queue as unknown as Queue<unknown>,
    fs,
    fsWrite: true,
  });

  // --- EXT-001: reasoning boundary. decide() consults the LLM and returns an
  // INERT Decision only. It performs no side effect and holds no handle. -----
  const artifactPath = "artifacts/smoke-result.json";
  const boundary: ReasoningBoundary = {
    async decide(): Promise<Decision[]> {
      const response = await llm.complete({
        prompt: "Propose the next transition for the smoke run.",
        context: { from: INITIAL_STATE },
      });
      // The model is an advisor: we capture WHAT it proposes as data. The
      // deterministic side decides HOW (and whether) below.
      const decision = createDecision({
        id: "smoke-decision-1",
        source: "smoke-agent",
        kind: "advance",
        payload: {
          // The advice (model text) is data only; it drives nothing directly.
          advice: response.text,
          model: response.model,
          // The transition events the executor will deterministically drive.
          events: ["START", "COMPLETE"],
          artifactPath,
        },
      });
      return [decision];
    },
  };

  // --- EXT-003: run the agent as a lightweight thread under a bounded pool.
  // The body may only reach the world through its granted handles; here it
  // funnels reasoning into Decision data. The pool drives run()/teardown(); we
  // capture the emitted decisions via a closure the body writes into. --------
  const emitted: Decision[] = [];
  const pool = new AgentPool(1);
  const thread = await pool.submit(() =>
    AgentThread.spawn({
      id: "smoke-agent",
      boundary,
      grants: ctx.grants,
      body: async (runCtx: AgentRunContext) => {
        const produced = await runCtx.boundary.decide(undefined);
        emitted.push(...produced);
        return produced;
      },
    })
  );
  // Let the pool run the thread to completion and free its slot.
  await pool.drain();

  if (thread.state === "failed") {
    throw new Error(
      `agent failed: ${
        thread.error instanceof Error ? thread.error.message : String(thread.error)
      }`
    );
  }
  if (emitted.length === 0) {
    throw new Error("agent emitted no decisions");
  }

  const decision = emitted[0];

  // --- EXT-001: the gate validates the inert decision FIRST ----------------
  const gated = validateDecision(decision);
  if (!gated.ok) {
    throw new Error(`decision rejected by gate: ${gated.reason}`);
  }

  // --- EXT-001: the executor deterministically accepts the decision --------
  const applied = apply(gated.value);
  if (!applied.applied) {
    throw new Error(`executor refused decision: ${applied.reason}`);
  }

  // --- EXT-002: drive the real durable state machine from the decision -----
  const payload = applied.decision.payload as {
    events: Event[];
    artifactPath: string;
  };
  const log = new TransitionLog(`${fs.baseDir}/state`, "transition.log").ensure();
  let state: State = INITIAL_STATE;
  for (const event of payload.events) {
    state = commit(log, state, event).state; // validates + durably logs each step
  }

  // --- EXT-005/006: write the result artifact ONLY through the granted,
  // harness-mediated FsWrite handle (the agent never touches raw fs). --------
  const artifact = JSON.stringify(
    {
      decision: applied.decision,
      finalState: state,
      logLength: log.length(),
    },
    null,
    2
  );
  const write = await harness.request("smoke-agent", {
    type: "fs.write",
    args: { path: payload.artifactPath, data: artifact },
  });
  if (!write.ok) {
    throw new Error(`harness refused artifact write: ${write.reason}`);
  }

  // Confirm the durable artifact is readable back from the shared FS.
  const persisted = fs.read(payload.artifactPath);
  if (!persisted.includes(state)) {
    throw new Error("artifact did not persist the final state");
  }

  // Tear the agent down — cheap lifecycle, no lingering services.
  harness.teardown("smoke-agent");

  return {
    finalState: state,
    decisionKind: applied.decision.kind,
    artifactPath: payload.artifactPath,
    llmProvider,
  };
}

async function main(): Promise<void> {
  try {
    const summary = await runSmoke();
    if (summary.finalState !== "DONE") {
      throw new Error(`expected final state DONE, got ${summary.finalState}`);
    }
    console.log(OK_MARKER);
    console.log(JSON.stringify(summary));
    process.exit(0);
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    console.error(`${FAIL_MARKER}: ${reason}`);
    process.exit(1);
  }
}

void main();
