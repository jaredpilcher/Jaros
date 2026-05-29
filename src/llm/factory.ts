import type { LlmClient } from "./client";
import { DefaultAdapter } from "./adapters/default-adapter";
import { UppercaseAdapter } from "./adapters/uppercase-adapter";

// #EXT-004-REQ-2 Start
/**
 * Provider-neutral configuration that selects the active adapter at startup.
 * Swapping the model/provider is achieved by editing this configuration alone —
 * no caller or harness code changes ([EXT-004 / REQ-2, REQ-4]).
 *
 * - `provider` key naming the concrete adapter to construct
 * - `model`    optional model identifier (passed through to a real provider)
 */
export interface LlmConfig {
  readonly provider: string;
  readonly model?: string;
}

/**
 * Registry of known adapter constructors keyed by `provider`. Adding a new
 * adapter is implementing {@link LlmClient} and registering it here — callers
 * are untouched.
 */
const ADAPTERS: Readonly<Record<string, () => LlmClient>> = {
  default: () => new DefaultAdapter(),
  uppercase: () => new UppercaseAdapter(),
};

/**
 * Select and construct an {@link LlmClient} from configuration. The return type
 * is the narrow interface only, so the concrete adapter never leaks to callers.
 * Throws a clear error for an unknown provider.
 */
export function createLlmClient(config: LlmConfig): LlmClient {
  const make = ADAPTERS[config.provider];
  if (!make) {
    const known = Object.keys(ADAPTERS).join(", ");
    throw new Error(
      `Unknown LLM provider "${config.provider}". Known providers: ${known}.`
    );
  }
  return make();
}
// #EXT-004-REQ-2 End
