import type { JsonValue } from "./json";

// #EXT-001-REQ-1 Start
/**
 * A `Decision` is the only thing the Reasoning Plane may emit. It is inert,
 * immutable, and fully JSON-serializable: it carries data and intent only and
 * MUST NOT contain callbacks, closures, handles, or any directly executable
 * side effect.
 *
 * - `id`     unique identifier for this decision
 * - `source` emitting agent / reasoning source id
 * - `kind`   discriminator the executor uses for deterministic dispatch
 * - `payload` inert, serializable data only
 */
export interface Decision {
  readonly id: string;
  readonly source: string;
  readonly kind: string;
  readonly payload: JsonValue;
}

/** Input accepted by {@link createDecision}. */
export interface DecisionInput {
  id: string;
  source: string;
  kind: string;
  payload: JsonValue;
}

/**
 * Recursively asserts that `value` is pure, serializable JSON data. Throws a
 * `TypeError` if it encounters a function, symbol, bigint, or any non-plain
 * object (class instance, Map, Set, Date, etc.) — i.e. anything that could
 * smuggle a closure or handle across the boundary.
 */
export function assertSerializable(value: unknown, path = "payload"): void {
  const t = typeof value;

  if (t === "function" || t === "symbol" || t === "bigint" || t === "undefined") {
    throw new TypeError(
      `Decision ${path} is not serializable: encountered ${t}.`
    );
  }

  if (value === null) {
    return;
  }

  if (t === "string" || t === "number" || t === "boolean") {
    if (t === "number" && !Number.isFinite(value as number)) {
      throw new TypeError(
        `Decision ${path} is not serializable: non-finite number.`
      );
    }
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item, i) => assertSerializable(item, `${path}[${i}]`));
    return;
  }

  if (t === "object") {
    // Only plain objects are allowed. Class instances, Map, Set, Date, etc.
    // have a non-Object prototype and are rejected.
    const proto = Object.getPrototypeOf(value);
    if (proto !== Object.prototype && proto !== null) {
      throw new TypeError(
        `Decision ${path} is not serializable: non-plain object (${
          (value as object).constructor?.name ?? "unknown"
        }).`
      );
    }
    for (const [key, v] of Object.entries(value as Record<string, unknown>)) {
      assertSerializable(v, `${path}.${key}`);
    }
    return;
  }

  throw new TypeError(`Decision ${path} is not serializable: unknown type ${t}.`);
}

/**
 * Factory that validates the input is fully serializable, then returns a deeply
 * frozen, immutable `Decision`. Throws if any field is missing/non-string or if
 * the payload carries non-serializable data.
 */
export function createDecision(input: DecisionInput): Decision {
  for (const field of ["id", "source", "kind"] as const) {
    if (typeof input[field] !== "string") {
      throw new TypeError(`Decision.${field} must be a string.`);
    }
  }

  assertSerializable(input.payload);

  const decision: Decision = {
    id: input.id,
    source: input.source,
    kind: input.kind,
    payload: deepFreeze(input.payload),
  };

  return Object.freeze(decision);
}

/** Recursively freezes a JSON value so the decision is immutable. */
function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === "object") {
    for (const v of Object.values(value as Record<string, unknown>)) {
      deepFreeze(v);
    }
    Object.freeze(value);
  }
  return value;
}
// #EXT-001-REQ-1 End
