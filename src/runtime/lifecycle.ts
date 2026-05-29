import type { Decision } from "../core/decision";

// #EXT-003-REQ-1 Start
// #EXT-003-REQ-2 Start
/**
 * Shared runtime lifecycle types for the agent thread runtime.
 *
 * These are pure runtime-plumbing contracts (state labels and the structural
 * shape of a runnable unit). They describe the runtime itself, not any agent's
 * behaviour, and carry no inter-agent channel — the pool depends on this
 * structural interface rather than reaching into the thread module directly.
 *
 * ```text
 *   spawned -> running -> (done | failed) -> torndown
 * ```
 */
export type AgentState = "spawned" | "running" | "failed" | "done" | "torndown";

/**
 * The structural contract the bounded pool drives: a lightweight in-process unit
 * with an id, an observable state, a contained `run()` that never rejects, and a
 * deterministic `teardown()`. Any implementation (e.g. an agent thread) is
 * hosted purely through this shape.
 */
export interface RunnableAgent {
  readonly id: string;
  readonly state: AgentState;
  readonly error: unknown;
  /** Run to completion; faults are contained, so this never rejects. */
  run(): Promise<Decision[]>;
  /** Release handles and join deterministically. Safe to call repeatedly. */
  teardown(): Promise<void>;
}
// #EXT-003-REQ-2 End
// #EXT-003-REQ-1 End
