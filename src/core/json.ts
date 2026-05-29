// #EXT-001-REQ-1 Start
/**
 * `JsonValue` is the structural type of all inert data that may cross the
 * reasoning/execution boundary. It is recursively composed of JSON primitives,
 * arrays, and plain objects only. Functions, class instances with methods, and
 * runtime handles are not assignable to this type, so a `Decision.payload`
 * typed as `JsonValue` cannot carry executable side effects at compile time.
 */
export type JsonPrimitive = string | number | boolean | null;

export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

export type JsonArray = JsonValue[];
// #EXT-001-REQ-1 End
