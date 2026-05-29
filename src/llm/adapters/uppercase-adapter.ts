import type { LlmClient, LlmRequest, LlmResponse } from "../client";

// #EXT-004-REQ-2 Start
/**
 * A second deterministic, dependency-free `LlmClient`. It exists to prove the
 * boundary is genuinely pluggable: swapping `config.provider` from "default" to
 * "uppercase" changes observable behavior through the SAME `LlmClient.complete`
 * call site, with zero caller changes ([EXT-004 / REQ-2, REQ-4]).
 *
 * Like every adapter it returns DATA ONLY and never drives control flow
 * ([PRIME-001 / REQ-4], EXT-004 REQ-3).
 */
export class UppercaseAdapter implements LlmClient {
  /** Stable identifier reported on every response's `model` field. */
  static readonly model = "uppercase-echo";

  async complete(req: LlmRequest): Promise<LlmResponse> {
    return {
      text: req.prompt.toUpperCase(),
      model: UppercaseAdapter.model,
    };
  }
}
// #EXT-004-REQ-2 End
