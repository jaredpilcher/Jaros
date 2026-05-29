import type { LlmClient, LlmRequest, LlmResponse } from "../client";

// #EXT-004-REQ-2 Start
/**
 * A concrete, dependency-free `LlmClient`. This is the swappable boundary, not a
 * real provider integration, so it is a deterministic stub: it derives its
 * response purely from the request (echoes the prompt back). A real adapter
 * would call out to a provider SDK here instead.
 *
 * Per the Prime Directive ([PRIME-001 / REQ-4], EXT-004 REQ-3) the adapter
 * returns DATA ONLY. It never invokes a state transition, never performs a side
 * effect, and never hands a runtime handle back to the caller.
 */
export class DefaultAdapter implements LlmClient {
  /** Stable identifier reported on every response's `model` field. */
  static readonly model = "default-echo";

  async complete(req: LlmRequest): Promise<LlmResponse> {
    // Deterministic derivation: echo the prompt. Pure data in → data out.
    return {
      text: `echo: ${req.prompt}`,
      model: DefaultAdapter.model,
    };
  }
}
// #EXT-004-REQ-2 End
