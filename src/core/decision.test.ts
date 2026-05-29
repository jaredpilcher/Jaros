import { test } from "node:test";
import assert from "node:assert/strict";
import { createDecision, assertSerializable } from "./decision";

test("assertSerializable rejects functions", () => {
  assert.throws(
    () => assertSerializable({ run: () => 1 }),
    /not serializable/
  );
});

test("assertSerializable rejects nested closures", () => {
  assert.throws(
    () => assertSerializable({ a: { b: [1, () => 2] } }),
    /not serializable/
  );
});

test("assertSerializable rejects non-plain objects (handles)", () => {
  class Handle {
    constructor(public fd: number) {}
  }
  assert.throws(() => assertSerializable({ h: new Handle(3) }), /not serializable/);
});

test("assertSerializable accepts plain JSON data", () => {
  assert.doesNotThrow(() =>
    assertSerializable({ a: 1, b: "x", c: [true, null, { d: 2 }] })
  );
});

test("createDecision rejects a payload carrying a function", () => {
  assert.throws(
    () =>
      createDecision({
        id: "1",
        source: "agent-a",
        kind: "noop",
        // @ts-expect-error intentionally passing a non-serializable payload
        payload: { go: () => undefined },
      }),
    /not serializable/
  );
});

test("createDecision freezes the decision and its payload", () => {
  const d = createDecision({
    id: "1",
    source: "agent-a",
    kind: "write",
    payload: { nested: { count: 1 } },
  });

  assert.ok(Object.isFrozen(d), "decision should be frozen");
  assert.ok(Object.isFrozen(d.payload), "payload should be frozen");
  assert.ok(
    Object.isFrozen((d.payload as { nested: object }).nested),
    "nested payload should be frozen"
  );

  assert.throws(() => {
    // @ts-expect-error mutating a readonly/frozen field
    d.id = "2";
  }, TypeError);
});

test("createDecision requires string id/source/kind", () => {
  assert.throws(
    () =>
      createDecision({
        // @ts-expect-error id must be a string
        id: 5,
        source: "a",
        kind: "k",
        payload: {},
      }),
    /must be a string/
  );
});
