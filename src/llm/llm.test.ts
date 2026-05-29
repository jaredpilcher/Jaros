import { test } from "node:test";
import assert from "node:assert/strict";
import { createLlmClient } from "./index";
import type { LlmClient, LlmResponse } from "./index";

// All callers go through the barrel and the `LlmClient` interface only —
// no concrete adapter is imported here, mirroring real caller code.

test("factory returns a working client for the 'default' provider", async () => {
  const client: LlmClient = createLlmClient({ provider: "default" });
  const res = await client.complete({ prompt: "hello" });
  assert.equal(res.text, "echo: hello");
  assert.equal(res.model, "default-echo");
});

test("factory returns a working client for the 'uppercase' provider", async () => {
  const client: LlmClient = createLlmClient({ provider: "uppercase" });
  const res = await client.complete({ prompt: "hello" });
  assert.equal(res.text, "HELLO");
  assert.equal(res.model, "uppercase-echo");
});

test("unknown provider throws a clear error", () => {
  assert.throws(
    () => createLlmClient({ provider: "does-not-exist" }),
    /Unknown LLM provider "does-not-exist"/
  );
});

test("swapping provider config changes behavior at the same call site (REQ-2/REQ-4)", async () => {
  // The call site is identical; only the configuration differs.
  const callSite = async (client: LlmClient) =>
    (await client.complete({ prompt: "swap me" })).text;

  const a = await callSite(createLlmClient({ provider: "default" }));
  const b = await callSite(createLlmClient({ provider: "uppercase" }));

  assert.notEqual(a, b, "different configured adapters must yield different output");
  assert.equal(a, "echo: swap me");
  assert.equal(b, "SWAP ME");
});

test("response carries data only — no functions/handles (REQ-3)", async () => {
  const client = createLlmClient({ provider: "default" });
  const res = await client.complete({
    prompt: "data",
    context: { items: [1, 2, 3] },
    params: { tone: "neutral" },
  });

  assertDataOnly(res);
  // The response must survive a JSON round-trip (no closures/handles smuggled).
  assert.doesNotThrow(() => JSON.parse(JSON.stringify(res)));
});

/** Recursively asserts a value contains no functions/symbols/handles. */
function assertDataOnly(value: unknown, path = "response"): void {
  const t = typeof value;
  assert.notEqual(t, "function", `${path} must not be a function`);
  assert.notEqual(t, "symbol", `${path} must not be a symbol`);
  if (value === null || t !== "object") {
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((v, i) => assertDataOnly(v, `${path}[${i}]`));
    return;
  }
  const proto = Object.getPrototypeOf(value);
  assert.ok(
    proto === Object.prototype || proto === null,
    `${path} must be a plain object (no class instance / handle)`
  );
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    assertDataOnly(v, `${path}.${k}`);
  }
}
