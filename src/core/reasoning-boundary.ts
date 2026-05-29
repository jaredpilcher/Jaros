// This module imports ONLY from decision.ts. It has no reference to the
// executor, state store, queue, or file system — the reasoning side cannot
// reach into execution.
import type { Decision } from "./decision";

// #EXT-001-REQ-2 Start
/**
 * The single seam through which all reasoning is funnelled. Its only output
 * type is `Decision` (a collection thereof). Implementations propose inert
 * decisions; they cannot perform side effects, mutate state, or invoke the
 * executor directly.
 */
export interface ReasoningBoundary {
  /**
   * Produce zero or more inert decisions for the given context. The `context`
   * is itself opaque to the boundary contract; implementations interpret it,
   * but may only ever return `Decision[]`.
   */
  decide(context: unknown): Promise<Decision[]>;
}
// #EXT-001-REQ-2 End
