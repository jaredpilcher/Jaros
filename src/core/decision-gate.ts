import type { Decision } from "./decision";
import { assertSerializable } from "./decision";

// #EXT-001-REQ-3 Start
/** Result of passing a decision through the validation gate. */
export type ValidationResult =
  | { ok: true; value: Decision }
  | { ok: false; reason: string };

/**
 * Deterministic validation/normalization gate. Every `Decision` passes through
 * this before any executor acts on it. Returns a normalized decision on success
 * or a typed rejection with a human-readable reason on failure.
 *
 * Determinism: identical input always yields identical output; the gate has no
 * side effects and consults no non-deterministic source.
 */
export function validateDecision(d: unknown): ValidationResult {
  if (d === null || typeof d !== "object") {
    return { ok: false, reason: "decision must be an object" };
  }

  const candidate = d as Partial<Decision>;

  for (const field of ["id", "source", "kind"] as const) {
    const v = candidate[field];
    if (typeof v !== "string") {
      return { ok: false, reason: `field "${field}" must be a string` };
    }
    if (v.length === 0) {
      return { ok: false, reason: `field "${field}" must not be empty` };
    }
  }

  if (!("payload" in candidate)) {
    return { ok: false, reason: 'field "payload" is required' };
  }

  try {
    assertSerializable(candidate.payload);
  } catch (err) {
    return {
      ok: false,
      reason: err instanceof Error ? err.message : "payload is not serializable",
    };
  }

  // Normalize: produce a clean decision with only the contract fields, in a
  // stable shape. Deterministic for identical inputs.
  const normalized: Decision = Object.freeze({
    id: candidate.id as string,
    source: candidate.source as string,
    kind: candidate.kind as string,
    payload: candidate.payload as Decision["payload"],
  });

  return { ok: true, value: normalized };
}
// #EXT-001-REQ-3 End
