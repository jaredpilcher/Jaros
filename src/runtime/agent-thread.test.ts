import { test } from "node:test";
import assert from "node:assert/strict";
import type { ReasoningBoundary } from "../core/reasoning-boundary";
import type { Decision } from "../core/decision";
import { AgentThread } from "./agent-thread";

/** A trivial reasoning boundary that emits a single inert decision. */
function boundary(): ReasoningBoundary {
  return {
    async decide(): Promise<Decision[]> {
      return [{ id: "d1", source: "test", kind: "noop", payload: null }];
    },
  };
}

test("spawn allocates only an in-process unit (no async, no server)", () => {
  const t = AgentThread.spawn({
    id: "a1",
    boundary: boundary(),
    grants: {},
    body: () => [],
  });
  assert.equal(t.id, "a1");
  assert.equal(t.state, "spawned");
});

test("spawn+run+teardown lifecycle completes and reaches a terminal state", async () => {
  let released = false;
  const t = AgentThread.spawn({
    id: "a1",
    boundary: boundary(),
    grants: {},
    body: async (ctx) => ctx.boundary.decide(undefined),
    releaseHandles: () => {
      released = true;
    },
  });

  const decisions = await t.run();
  assert.equal(decisions.length, 1);
  assert.equal(t.state, "torndown");
  assert.equal(released, true, "handles were released on teardown");
});

test("spawn+teardown completes within a tight time bound", async () => {
  const start = Date.now();
  // Spawn and tear down many agents routinely; should be cheap (in-process).
  for (let i = 0; i < 200; i++) {
    const t = AgentThread.spawn({
      id: `a${i}`,
      boundary: boundary(),
      grants: {},
      body: () => [],
    });
    await t.run();
    assert.equal(t.state, "torndown");
  }
  const elapsed = Date.now() - start;
  assert.ok(elapsed < 2000, `200 spawn+teardown cycles took ${elapsed}ms (expected < 2000ms)`);
});

test("teardown is idempotent and releases handles at most once", async () => {
  let releases = 0;
  const t = AgentThread.spawn({
    id: "a1",
    boundary: boundary(),
    grants: {},
    body: () => [],
    releaseHandles: () => {
      releases += 1;
    },
  });
  await t.run();
  await t.teardown();
  await t.teardown();
  assert.equal(releases, 1);
});

test("an unhandled error is contained: agent marked failed, run does not reject", async () => {
  let reported: unknown = undefined;
  let released = false;
  const t = AgentThread.spawn({
    id: "boom",
    boundary: boundary(),
    grants: {},
    body: () => {
      throw new Error("agent blew up");
    },
    onFailed: (err) => {
      reported = err;
    },
    releaseHandles: () => {
      released = true;
    },
  });

  // run() must resolve (not reject) so the process is not crashed.
  const decisions = await t.run();
  assert.deepEqual(decisions, []);
  assert.equal(t.state, "failed");
  assert.ok(t.error instanceof Error);
  assert.equal((reported as Error).message, "agent blew up");
  assert.equal(released, true, "a failed agent is still torn down cleanly");
});

test("running from a non-spawned state is rejected", async () => {
  const t = AgentThread.spawn({
    id: "a1",
    boundary: boundary(),
    grants: {},
    body: () => [],
  });
  await t.run();
  await assert.rejects(() => t.run(), /cannot run from state/);
});
