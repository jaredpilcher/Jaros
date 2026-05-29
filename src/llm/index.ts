// #EXT-004-REQ-1 Start
// Barrel for LLM consumers. Re-exports the single narrow `LlmClient` interface,
// its provider-neutral request/response types, and the config-driven factory.
// Callers import from here and never reach a concrete adapter directly, so the
// model is interchangeable behind one boundary ([EXT-004 / REQ-1, REQ-2]).
export type { LlmClient, LlmRequest, LlmResponse } from "./client";
export type { LlmConfig } from "./factory";
export { createLlmClient } from "./factory";
// #EXT-004-REQ-1 End
