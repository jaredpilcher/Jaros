import type { ReasoningBoundary } from "../core/reasoning-boundary";
import type { Decision } from "../core/decision";
import type { Grants } from "../harness/capabilities";
import type { AgentState, RunnableAgent } from "./lifecycle";

// #EXT-003-REQ-1 Start
// #EXT-003-REQ-4 Start
export type { AgentState } from "./lifecycle";

/**
 * What an agent actually does while running. It is handed ONLY its granted
 * capability handles (no global queue/fs/network references) and its reasoning
 * boundary. It returns the decisions the reasoning side proposed; it can never
 * perform a side effect except through its granted handles.
 */
export interface AgentBody {
  (ctx: AgentRunContext): Promise<Decision[]> | Decision[];
}

/** The minimal context an agent body runs against. */
export interface AgentRunContext {
  readonly agentId: string;
  /** The agent's reasoning seam — emits inert decisions only. */
  readonly boundary: ReasoningBoundary;
  /** ONLY the granted handles. Absent fields mean no access (no ambient power). */
  readonly grants: Grants;
}

/** Configuration for constructing an {@link AgentThread}. */
export interface AgentThreadConfig {
  readonly id: string;
  readonly boundary: ReasoningBoundary;
  readonly grants: Grants;
  /** The work the agent performs; wraps a call into its reasoning boundary. */
  readonly body: AgentBody;
  /**
   * Optional resource release hook (file handles, timers, queue handles). Called
   * exactly once by {@link AgentThread.teardown}. Must be idempotent-safe — the
   * thread guarantees it is invoked at most once.
   */
  readonly releaseHandles?: () => void | Promise<void>;
  /**
   * Called when execution is contained after an unhandled error, before
   * teardown completes. Lets the owner (e.g. the pool/harness) observe the fault.
   */
  readonly onFailed?: (error: unknown) => void;
}

/**
 * A lightweight, in-process unit of agent execution.
 *
 * An `AgentThread` is NOT a service: it opens no socket, binds no port, and
 * needs no deployment. It is a cheap task wrapping a {@link ReasoningBoundary},
 * running under only its granted capabilities. Spawn and teardown are intended
 * to be performed routinely at runtime.
 *
 * Fault containment: {@link run} wraps the agent body so any unhandled error is
 * CAUGHT, marks the agent `failed`, fires `onFailed`, and triggers
 * {@link teardown}. The error never propagates out to crash the process; `run`
 * resolves rather than rejects.
 */
export class AgentThread implements RunnableAgent {
  private readonly config: AgentThreadConfig;
  private _state: AgentState = "spawned";
  private _error: unknown = undefined;
  private released = false;
  private runPromise: Promise<void> | null = null;

  private constructor(config: AgentThreadConfig) {
    this.config = config;
  }

  /**
   * Cheaply allocate an in-process agent thread. Allocates only an object — no
   * network service, container, or port is provisioned.
   */
  static spawn(config: AgentThreadConfig): AgentThread {
    if (typeof config.id !== "string" || config.id.length === 0) {
      throw new TypeError("AgentThread.spawn requires a non-empty id.");
    }
    return new AgentThread(config);
  }

  /** This agent's stable id. */
  get id(): string {
    return this.config.id;
  }

  /** The agent's current lifecycle state. */
  get state(): AgentState {
    return this._state;
  }

  /** The contained error, if this agent failed; otherwise `undefined`. */
  get error(): unknown {
    return this._error;
  }

  /**
   * Run the agent body to completion. Faults are CONTAINED: an unhandled error
   * is caught, the agent is marked `failed`, `onFailed` fires, and teardown is
   * triggered. This method never rejects — it always resolves so a single
   * agent's failure cannot crash the runtime or reject up to siblings.
   *
   * Returns the decisions the agent emitted (empty array on failure).
   */
  async run(): Promise<Decision[]> {
    if (this._state !== "spawned") {
      throw new Error(
        `AgentThread "${this.id}" cannot run from state "${this._state}".`
      );
    }
    this._state = "running";

    let decisions: Decision[] = [];
    let task!: () => Promise<void>;

    this.runPromise = new Promise<void>((resolve) => {
      task = async () => {
        try {
          const ctx: AgentRunContext = {
            agentId: this.id,
            boundary: this.config.boundary,
            grants: this.config.grants,
          };
          decisions = await this.config.body(ctx);
          if (this._state === "running") {
            this._state = "done";
          }
        } catch (err) {
          // Fault containment: do NOT rethrow. Mark failed and report.
          this._error = err;
          this._state = "failed";
          try {
            this.config.onFailed?.(err);
          } catch {
            // A faulty failure reporter must not itself escape containment.
          }
        } finally {
          resolve();
        }
      };
    });

    await task();
    // A failed or done agent always tears down, releasing its handles.
    await this.teardown();
    return decisions;
  }

  /**
   * Release all handles and join the underlying task deterministically. Safe to
   * call multiple times; resource release runs at most once. After teardown the
   * agent is in a terminal state and holds no live handles.
   */
  async teardown(): Promise<void> {
    // Join the in-flight run (if any) so teardown is deterministic.
    if (this.runPromise) {
      await this.runPromise;
    }

    if (!this.released) {
      this.released = true;
      try {
        await this.config.releaseHandles?.();
      } catch {
        // Releasing handles must not throw out of teardown.
      }
    }

    // Preserve a `failed` marker; otherwise mark terminal as torn down.
    if (this._state !== "failed") {
      this._state = "torndown";
    }
  }
}
// #EXT-003-REQ-4 End
// #EXT-003-REQ-1 End
