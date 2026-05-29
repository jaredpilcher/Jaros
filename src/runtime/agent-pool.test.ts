import { test } from "node:test";
import assert from "node:assert/strict";
import type { ReasoningBoundary } from "../core/reasoning-boundary";
import type { Decision } from "../core/decision";
import { AgentThread } from "./agent-thread";
import { AgentPool } from "./agent-pool";

function boundary(): ReasoningBoundary {
  return {
    async decide(): Promise<Decision[]> {
      return [];
    },
  };
}

/** A deferred promise helper for controlling agent completion in tests. */
function deferred<T = void>(): { promise: Promise<T>; resolve: (v: T) => void } {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

test("submit runs an agent to completion and frees the slot", async () => {
  const pool = new AgentPool(2);
  const t = await pool.submit(() =>
    AgentThread.spawn({ id: "a1", boundary: boundary(), grants: {}, body: () => [] })
  );
  await t.teardown();
  await pool.drain();
  assert.equal(pool.active().length, 0);
});

test("pool respects the bound and queues excess submissions (backpressure)", async () => {
  const pool = new AgentPool(2);
  const gate = deferred();

  const makeBlocking = (id: string) => () =>
    AgentThread.spawn({
      id,
      boundary: boundary(),
      grants: {},
      body: async () => {
        await gate.promise;
        return [];
      },
    });

  await pool.submit(makeBlocking("a1"));
  await pool.submit(makeBlocking("a2"));

  // Third submission must NOT start immediately — it is queued behind the bound.
  let thirdStarted = false;
  const third = pool.submit(makeBlocking("a3")).then((t) => {
    thirdStarted = true;
    return t;
  });

  await Promise.resolve();
  assert.equal(pool.active().length, 2, "never exceeds the bound");
  assert.equal(pool.pending, 1, "excess submission is queued");
  assert.equal(thirdStarted, false, "queued submission has not started");

  // Release the running agents; the queued one should then be admitted.
  gate.resolve();
  await third;
  assert.equal(thirdStarted, true, "queued submission admitted after a slot frees");

  await pool.drain();
  assert.equal(pool.active().length, 0);
});

test("snapshot lists each active agent's id and state", async () => {
  const pool = new AgentPool(3);
  const gate = deferred();
  const make = (id: string) => () =>
    AgentThread.spawn({
      id,
      boundary: boundary(),
      grants: {},
      body: async () => {
        await gate.promise;
        return [];
      },
    });

  await pool.submit(make("x1"));
  await pool.submit(make("x2"));

  const snap = pool.snapshot();
  assert.equal(snap.length, 2);
  const ids = snap.map((s) => s.id).sort();
  assert.deepEqual(ids, ["x1", "x2"]);
  for (const entry of snap) {
    assert.equal(entry.state, "running");
  }

  gate.resolve();
  await pool.drain();
});

test("a throwing agent is contained: process survives, failure reported, siblings keep running", async () => {
  const failures: Array<{ id: string; error: unknown }> = [];
  const pool = new AgentPool(3, {
    onAgentFailed: (f) => failures.push(f),
  });

  const siblingGate = deferred();
  let siblingFinished = false;

  // A sibling that stays running until we release it.
  await pool.submit(() =>
    AgentThread.spawn({
      id: "sibling",
      boundary: boundary(),
      grants: {},
      body: async () => {
        await siblingGate.promise;
        siblingFinished = true;
        return [];
      },
    })
  );

  // A throwing agent — the pool drives its run; its failure must be contained.
  const boom = await pool.submit(() =>
    AgentThread.spawn({
      id: "boom",
      boundary: boundary(),
      grants: {},
      body: () => {
        throw new Error("kaboom");
      },
    })
  );

  // Wait for the pool-driven, contained run + teardown to settle and for the
  // failure to be reported. The throwing agent reaches a terminal state without
  // ever rejecting up to the test.
  for (let i = 0; failures.length === 0 && i < 1000; i++) {
    await Promise.resolve();
  }

  assert.equal(boom.state, "failed");
  assert.equal(failures.length, 1, "onAgentFailed fired for the failed agent");
  assert.equal(failures[0].id, "boom");
  assert.ok(failures[0].error instanceof Error);

  // The sibling is unaffected and still running.
  const sibling = pool.active().find((t) => t.id === "sibling");
  assert.ok(sibling, "sibling is still active after peer failed");
  assert.equal(sibling!.state, "running");

  // The process is still alive — finish the sibling normally.
  siblingGate.resolve();
  await pool.drain();
  assert.equal(siblingFinished, true, "sibling completed unaffected by the peer failure");
});

test("bound must be a positive integer", () => {
  assert.throws(() => new AgentPool(0), TypeError);
  assert.throws(() => new AgentPool(-1), TypeError);
  assert.throws(() => new AgentPool(1.5), TypeError);
});
