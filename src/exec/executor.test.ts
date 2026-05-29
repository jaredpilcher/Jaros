import { test } from "node:test";
import assert from "node:assert/strict";
import { apply, type Logger } from "./executor";
import { createDecision } from "../core/decision";

function captureLogger(): { logger: Logger; messages: string[] } {
  const messages: string[] = [];
  return { logger: { warn: (m) => messages.push(m) }, messages };
}

test("executor applies a valid decision", () => {
  const d = createDecision({
    id: "d1",
    source: "agent-a",
    kind: "noop",
    payload: { ok: true },
  });
  const { logger, messages } = captureLogger();

  const result = apply(d, logger);
  assert.equal(result.applied, true);
  assert.equal(messages.length, 0, "no refusal should be logged for a valid decision");
});

test("executor refuses an invalid decision and does not mutate (logs reason)", () => {
  const invalid = { id: "d1", source: "a", payload: {} }; // missing kind
  const { logger, messages } = captureLogger();

  const result = apply(invalid, logger);

  assert.equal(result.applied, false);
  if (!result.applied) {
    assert.match(result.reason, /kind/);
  }
  assert.equal(messages.length, 1, "refusal should be logged");
  assert.match(messages[0], /refused decision/);
});

test("executor refuses a decision with a non-serializable payload", () => {
  const invalid = { id: "d1", source: "a", kind: "k", payload: { go: () => 1 } };
  const { logger } = captureLogger();

  const result = apply(invalid, logger);
  assert.equal(result.applied, false);
});
