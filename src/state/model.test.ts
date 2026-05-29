import { test } from "node:test";
import assert from "node:assert/strict";
import { STATES, EVENTS, TRANSITIONS, listTransitions, isState, isEvent } from "./model";

test("no transition points to an undeclared state", () => {
  for (const from of STATES) {
    for (const event of EVENTS) {
      const to = TRANSITIONS[from][event];
      if (to !== undefined) {
        assert.ok(
          (STATES as readonly string[]).includes(to),
          `transition (${from}, ${event}) -> ${to} targets an undeclared state`
        );
      }
    }
  }
});

test("every transition originates from a declared state", () => {
  for (const from of Object.keys(TRANSITIONS)) {
    assert.ok((STATES as readonly string[]).includes(from), `${from} is not a declared state`);
  }
});

test("listTransitions flattens to (from,event,to) triples deterministically", () => {
  const triples = listTransitions();
  // Each triple must be a declared transition.
  for (const t of triples) {
    assert.equal(TRANSITIONS[t.from][t.event], t.to);
  }
  // Stable order: re-running yields an identical sequence.
  assert.deepEqual(listTransitions(), triples);
  // Count equals the number of declared edges.
  const declared = STATES.flatMap((s) => Object.keys(TRANSITIONS[s])).length;
  assert.equal(triples.length, declared);
});

test("isState / isEvent guard the declared sets", () => {
  assert.ok(isState("PENDING"));
  assert.ok(!isState("NOPE"));
  assert.ok(!isState(42));
  assert.ok(isEvent("START"));
  assert.ok(!isEvent("LAUNCH"));
});
