import type { Decision } from "../core/decision";
import { validateDecision } from "../core/decision-gate";

// #EXT-001-REQ-3 Start
/** Outcome of attempting to apply a decision. */
export type ApplyResult =
  | { applied: true; decision: Decision }
  | { applied: false; reason: string };

/** Minimal logger surface so tests can capture refusals deterministically. */
export interface Logger {
  warn(message: string): void;
}

/**
 * Deterministic executor entry point. It runs `validateDecision` FIRST and
 * refuses to act on any decision the gate rejects: on `ok: false` it logs the
 * reason and returns without mutating any state.
 *
 * This module is part of the Execution Plane: it imports the gate from core but
 * never imports the LLM client/adapter or the ReasoningBoundary.
 */
export function apply(d: unknown, logger: Logger = console): ApplyResult {
  const result = validateDecision(d);

  if (!result.ok) {
    logger.warn(`[executor] refused decision: ${result.reason}`);
    return { applied: false, reason: result.reason };
  }

  // Decision is valid and normalized. Deterministic dispatch on `kind` would
  // happen here; for this spec, applying a valid decision is the seam that
  // later execution work hangs off of. No non-deterministic input is consulted.
  return { applied: true, decision: result.value };
}
// #EXT-001-REQ-3 End
