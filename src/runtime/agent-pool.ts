import type { AgentState, RunnableAgent } from "./lifecycle";

// #EXT-003-REQ-2 Start
// #EXT-003-REQ-4 Start
/**
 * A factory that produces a fresh runnable agent to run. The pool calls it when
 * capacity is available. The factory must return a freshly-spawned unit (state
 * `spawned`); the pool drives its `run()`/`teardown()` lifecycle.
 */
export interface AgentFactory {
  (): RunnableAgent;
}

/** Observability record for a single active agent. */
export interface AgentSnapshotEntry {
  readonly id: string;
  readonly state: AgentState;
}

/** Reports a contained agent failure to the harness/owner. */
export interface OnAgentFailed {
  (failure: { readonly id: string; readonly error: unknown }): void;
}

/** Construction options for an {@link AgentPool}. */
export interface AgentPoolOptions {
  /** Reports each contained agent failure; siblings keep running regardless. */
  readonly onAgentFailed?: OnAgentFailed;
}

/**
 * A bounded, observable pool of lightweight agent threads.
 *
 * The pool hosts up to `bound` concurrent agents. {@link submit} applies
 * backpressure: once `active().length === bound`, further spawns are QUEUED
 * rather than allowed to grow unbounded; queued factories start as running
 * agents complete and free a slot.
 *
 * Fault containment: a single agent's failure is contained by the
 * {@link RunnableAgent} and reported via `onAgentFailed`; sibling agents are
 * unaffected and continue running, and a freed slot still admits queued work.
 */
export class AgentPool {
  private readonly bound: number;
  private readonly onAgentFailed?: OnAgentFailed;
  private readonly activeThreads = new Map<string, RunnableAgent>();
  private readonly waiting: Array<{
    factory: AgentFactory;
    resolve: (t: RunnableAgent) => void;
    reject: (err: unknown) => void;
  }> = [];

  constructor(bound: number, options: AgentPoolOptions = {}) {
    if (!Number.isInteger(bound) || bound < 1) {
      throw new TypeError("AgentPool bound must be a positive integer.");
    }
    this.bound = bound;
    this.onAgentFailed = options.onAgentFailed;
  }

  /** The configured maximum number of concurrent agents. */
  get capacity(): number {
    return this.bound;
  }

  /** The currently running/active agent threads. */
  active(): readonly RunnableAgent[] {
    return [...this.activeThreads.values()];
  }

  /** Number of submissions queued behind the bound (backpressure depth). */
  get pending(): number {
    return this.waiting.length;
  }

  /**
   * Submit an agent for execution. If there is free capacity the agent is
   * spawned immediately; otherwise the factory is queued (backpressure) and
   * admitted when a slot frees. Resolves with the {@link RunnableAgent} once it has
   * been admitted and started running.
   */
  submit(factory: AgentFactory): Promise<RunnableAgent> {
    if (this.activeThreads.size < this.bound) {
      return Promise.resolve(this.start(factory));
    }
    return new Promise<RunnableAgent>((resolve, reject) => {
      this.waiting.push({ factory, resolve, reject });
    });
  }

  /** Enumerate active agents' ids and states for observability. */
  snapshot(): AgentSnapshotEntry[] {
    return this.active().map((t) => ({ id: t.id, state: t.state }));
  }

  /**
   * Wait until all active and queued agents have finished and been torn down.
   * Useful for deterministic shutdown in tests and callers.
   */
  async drain(): Promise<void> {
    while (this.activeThreads.size > 0 || this.waiting.length > 0) {
      const running = this.active().map((t) => t.teardown());
      await Promise.all(running);
      // teardown -> run() resolution removes from the map and admits queued work,
      // but loop again to catch newly-admitted agents.
      await Promise.resolve();
    }
  }

  /** Admit one factory: spawn the thread, register it, and drive its run. */
  private start(factory: AgentFactory): RunnableAgent {
    const thread = factory();
    if (this.activeThreads.has(thread.id)) {
      throw new Error(`Agent "${thread.id}" is already active in the pool.`);
    }
    this.activeThreads.set(thread.id, thread);

    // Drive the agent. run() never rejects (faults are contained inside the
    // thread), so a single failure cannot reject up into the pool or siblings.
    void thread.run().then(() => {
      this.activeThreads.delete(thread.id);
      if (thread.state === "failed") {
        try {
          this.onAgentFailed?.({ id: thread.id, error: thread.error });
        } catch {
          // The failure reporter must not destabilize the pool or siblings.
        }
      }
      this.admitNext();
    });

    return thread;
  }

  /** Admit the next queued factory, if any, now that a slot has freed. */
  private admitNext(): void {
    if (this.waiting.length === 0) {
      return;
    }
    if (this.activeThreads.size >= this.bound) {
      return;
    }
    const next = this.waiting.shift()!;
    try {
      const thread = this.start(next.factory);
      next.resolve(thread);
    } catch (err) {
      next.reject(err);
    }
  }
}
// #EXT-003-REQ-4 End
// #EXT-003-REQ-2 End
