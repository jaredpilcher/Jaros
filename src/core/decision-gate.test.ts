import { test } from "node:test";
import assert from "node:assert/strict";
import { validateDecision } from "./decision-gate";
import { createDecision } from "./decision";

test("validateDecision accepts a good decision", () => {
  const d = createDecision({
    id: "d1",
    source: "agent-a",
    kind: "write-file",
    payload: { path: "/outbox/x", bytes: 12 },
  });

  const result = validateDecision(d);
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal(result.value.id, "d1");
    assert.equal(result.value.kind, "write-file");
    assert.deepEqual(result.value.payload, { path: "/outbox/x", bytes: 12 });
  }
});

test("validateDecision rejects a malformed decision (missing kind)", () => {
  const result = validateDecision({ id: "d1", source: "a", payload: {} });
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.match(result.reason, /kind/);
  }
});

test("validateDecision rejects an empty id", () => {
  const result = validateDecision({ id: "", source: "a", kind: "k", payload: {} });
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.match(result.reason, /id/);
  }
});

test("validateDecision rejects a non-serializable payload", () => {
  const result = validateDecision({
    id: "d1",
    source: "a",
    kind: "k",
    payload: { go: () => 1 },
  });
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.match(result.reason, /serializable/);
  }
});

test("validateDecision rejects a non-object", () => {
  assert.equal(validateDecision(null).ok, false);
  assert.equal(validateDecision("nope").ok, false);
});

test("validateDecision is deterministic for identical inputs", () => {
  const input = { id: "d1", source: "a", kind: "k", payload: { n: 1 } };
  assert.deepEqual(validateDecision(input), validateDecision(input));
});
