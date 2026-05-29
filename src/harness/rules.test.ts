import { test } from "node:test";
import assert from "node:assert/strict";
import { describeRules, ruleFor } from "./rules";

test("describeRules returns the active rule set for audit", () => {
  const rules = describeRules();
  const actions = rules.map((r) => r.action).sort();
  assert.deepEqual(actions, ["fs.read", "fs.write", "queue.receive", "queue.send"]);
  const send = rules.find((r) => r.action === "queue.send");
  assert.equal(send?.requires, "QueueSend");
});

test("ruleFor resolves known actions and default-denies unknown ones", () => {
  assert.equal(ruleFor("fs.write")?.requires, "FsWrite");
  assert.equal(ruleFor("network.connect"), undefined);
  assert.equal(ruleFor(""), undefined);
});

test("agent code cannot mutate the rule set at runtime", () => {
  const rules = describeRules();
  // The returned snapshot is frozen.
  assert.equal(Object.isFrozen(rules), true);
  assert.equal(Object.isFrozen(rules[0]), true);
  assert.throws(() => {
    // @ts-expect-error attempting to push onto a frozen array
    rules.push({ action: "fs.write", requires: "FsWrite", description: "evil" });
  });
  assert.throws(() => {
    // @ts-expect-error attempting to rewrite a rule field
    rules[0].requires = "FsWrite";
  });
});

test("mutating a describeRules snapshot does not affect the real rules", () => {
  const first = describeRules();
  try {
    // @ts-expect-error best-effort mutation that should be a no-op (frozen)
    first[0].requires = "TAMPERED";
  } catch {
    // frozen objects throw in strict mode; either way nothing changes.
  }
  const second = describeRules();
  const send = second.find((r) => r.action === "queue.send");
  assert.equal(send?.requires, "QueueSend");
});
