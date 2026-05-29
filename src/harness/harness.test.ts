import { test } from "node:test";
import assert from "node:assert/strict";
import * as os from "os";
import * as path from "path";
import * as fs from "fs";
import { Queue } from "../comms/queue";
import { SharedFileSystem } from "../comms/fs";
import { RevokedCapabilityError } from "./capabilities";
import { Harness } from "./harness";

function tmpFs(): SharedFileSystem {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jaros-harness-"));
  return new SharedFileSystem(dir).ensureLayout();
}

function anyQueue(): Queue<unknown> {
  return new Queue<unknown>((v): v is unknown => true, "test-q");
}

test("spawn gives an agent only its grants, no global refs", () => {
  const h = new Harness();
  const q = anyQueue();
  const ctx = h.spawn("a1", { queueSend: q });
  assert.equal(ctx.agentId, "a1");
  assert.ok(ctx.grants.queueSend);
  assert.equal(ctx.grants.queueReceive, undefined);
  assert.equal(ctx.grants.fsWrite, undefined);
  // No way to reach a raw queue/fs/network off the context.
  assert.deepEqual(Object.keys(ctx), ["agentId", "grants"]);
});

test("harness performs an allowed action only via the granted handle", async () => {
  const h = new Harness();
  const q = anyQueue();
  h.spawn("a1", { queueSend: q });
  const res = await h.request("a1", { type: "queue.send", args: { message: "ping" } });
  assert.equal(res.ok, true);
  assert.equal(q.size, 1);
  assert.equal(q.peek(), "ping");
});

test("default-deny: unknown action is refused with no side effect", async () => {
  const h = new Harness();
  const q = anyQueue();
  h.spawn("a1", { queueSend: q });
  const res = await h.request("a1", { type: "network.connect", args: {} });
  assert.equal(res.ok, false);
  if (!res.ok) assert.match(res.reason, /default-deny/);
  assert.equal(q.size, 0);
  // The denial was reported in the audit log.
  const denied = h.audit().find((e) => e.action === "network.connect");
  assert.equal(denied?.allowed, false);
});

test("agent given only QueueSend cannot read or write fs (default-deny)", async () => {
  const h = new Harness();
  const sfs = tmpFs();
  h.spawn("a1", { queueSend: anyQueue() });

  const w = await h.request("a1", { type: "fs.write", args: { path: "outbox/x", data: "y" } });
  assert.equal(w.ok, false);
  if (!w.ok) assert.match(w.reason, /FsWrite/);

  const r = await h.request("a1", { type: "fs.read", args: { path: "outbox/x" } });
  assert.equal(r.ok, false);
  if (!r.ok) assert.match(r.reason, /FsRead/);

  // No file was created as a side effect.
  assert.equal(fs.existsSync(path.join(sfs.baseDir, "outbox", "x")), false);
});

test("fs.write then fs.read round-trips for an agent granted both", async () => {
  const h = new Harness();
  const sfs = tmpFs();
  h.spawn("writer", { fs: sfs, fsWrite: true, fsRead: true });
  const w = await h.request("writer", {
    type: "fs.write",
    args: { path: "artifacts/out.txt", data: "hello" },
  });
  assert.equal(w.ok, true);
  const r = await h.request("writer", { type: "fs.read", args: { path: "artifacts/out.txt" } });
  assert.equal(r.ok, true);
  if (r.ok) assert.equal(r.value, "hello");
});

test("requests from an unknown/torn-down agent are denied", async () => {
  const h = new Harness();
  const q = anyQueue();
  h.spawn("a1", { queueSend: q });
  h.teardown("a1");
  const res = await h.request("a1", { type: "queue.send", args: { message: "x" } });
  assert.equal(res.ok, false);
  assert.equal(q.size, 0);
});

test("teardown revokes the handles the agent still holds", async () => {
  const h = new Harness();
  const q = anyQueue();
  const ctx = h.spawn("a1", { queueSend: q });
  h.teardown("a1");
  // The agent's retained handle now fails closed.
  assert.throws(() => ctx.grants.queueSend!.send("x"), RevokedCapabilityError);
  assert.equal(q.size, 0);
});

test("describeRules on the harness exposes the active rules", () => {
  const h = new Harness();
  const rules = h.describeRules();
  assert.ok(rules.some((r) => r.action === "queue.send"));
});
