// #EXT-001-REQ-2 Start
// Barrel for reasoning-side consumers. Re-exports the inert Decision contract
// and the ReasoningBoundary interface only.
export type {
  Decision,
  DecisionInput,
} from "./decision";
export { createDecision, assertSerializable } from "./decision";
export type { ReasoningBoundary } from "./reasoning-boundary";
export type {
  JsonValue,
  JsonObject,
  JsonArray,
  JsonPrimitive,
} from "./json";
// #EXT-001-REQ-2 End
