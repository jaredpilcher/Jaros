import type { JsonValue } from "../core/json";

// #EXT-004-REQ-1 Start
/**
 * Provider-neutral request handed to an {@link LlmClient}. It carries inert,
 * serializable data only: a prompt and optional structured context/parameters.
 * No provider-specific types appear here, so callers never couple to a concrete
 * model or SDK.
 *
 * - `prompt`  the text the model is asked to complete/reason over
 * - `context` optional inert, JSON-serializable context for the model
 * - `params`  optional provider-neutral knobs (e.g. a temperature-like hint)
 */
export interface LlmRequest {
  readonly prompt: string;
  readonly context?: JsonValue;
  readonly params?: {
    readonly [key: string]: JsonValue;
  };
}

/**
 * Provider-neutral response returned by an {@link LlmClient}.
 *
 * IMPORTANT — control-flow quarantine ([PRIME-001 / REQ-4], EXT-004 REQ-3):
 * an `LlmResponse` carries TEXT and STRUCTURED OUTPUT (data) ONLY. It MUST NOT
 * contain functions, callbacks, closures, runtime handles, or anything that
 * could invoke a state transition or perform a side effect. The model is an
 * advisor: it returns data describing *what* it proposes. The deterministic
 * Execution Plane decides *how* — and whether — anything happens. An adapter
 * therefore never calls a state-machine transition and never hands a lever back
 * to the caller; its entire interface with the world is data in → data out.
 *
 * - `text`       the model's primary textual output
 * - `structured` optional inert, JSON-serializable structured output
 * - `model`      identifier of the model/provider that produced the response
 */
export interface LlmResponse {
  readonly text: string;
  readonly structured?: JsonValue;
  readonly model: string;
}

/**
 * The single narrow interface through which ALL model access flows. Any
 * conforming provider/model can satisfy it, and every caller depends only on
 * this type — never on a concrete adapter. `complete` is the one primary entry
 * point: it accepts a provider-neutral request and resolves to a data-only
 * response. It returns data; it never drives control flow.
 */
export interface LlmClient {
  complete(req: LlmRequest): Promise<LlmResponse>;
}
// #EXT-004-REQ-1 End
