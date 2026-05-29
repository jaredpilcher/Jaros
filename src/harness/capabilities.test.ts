import { test } from "node:test";
import assert from "node:assert/strict";
import * as os from "os";
import * as path from "path";
import * as fs from "fs";
import { Queue } from "../comms/queue";
import { SharedFileSystem } from "../comms/fs";
import {
  grant,
  revoke,
  RevokedCapabilityError,
  type Grants,
} from "./capabilities";

function tmpFs(): SharedFileSystem {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jaros-cap-"));
  return new SharedFileSystem(dir).ensureLayout();
}

function anyQueue(): Queue<unknown> {
  return new Queue<unknown>((v): v is unknown => true, "test-q");
}

test("granted QueueSend handle wraps the queue and works", () => {
  const q = anyQueue();
  const { grants } = grant({ queueSend: q });
  assert.ok(grants.queueSend);
  grants.queueSend!.send({ hello: "world" });
  assert.equal(q.size, 1);
  assert.deepEqual(q.peek(), { hello: "world" });
});

test("granted FsWrite/FsRead handles wrap the shared fs and work", () => {
  const sfs = tmpFs();
  const { grants } = grant({ fs: sfs, fsWrite: true, fsRead: true });
  grants.fsWrite!.write("outbox/note.txt", "hi");
  assert.equal(grants.fsRead!.read("outbox/note.txt"), "hi");
});

test("revoked handle throws RevokedCapabilityError and performs no side effect", () => {
  const q = anyQueue();
  const revocable = grant({ queueSend: q });
  revoke(revocable);
  assert.throws(
    () => revocable.grants.queueSend!.send("x"),
    (err: unknown) => err instanceof RevokedCapabilityError
  );
  // No side effect: nothing was enqueued.
  assert.equal(q.size, 0);
});

test("revoked fs handles fail closed", () => {
  const sfs = tmpFs();
  const revocable = grant({ fs: sfs, fsWrite: true, fsRead: true });
  revoke(revocable);
  assert.throws(() => revocable.grants.fsWrite!.write("outbox/x", "y"), RevokedCapabilityError);
  assert.throws(() => revocable.grants.fsRead!.read("outbox/x"), RevokedCapabilityError);
});

test("an agent granted only QueueSend has no fs or receive handles", () => {
  const q = anyQueue();
  const { grants }: { grants: Grants } = grant({ queueSend: q });
  assert.ok(grants.queueSend);
  assert.equal(grants.queueReceive, undefined);
  assert.equal(grants.fsWrite, undefined);
  assert.equal(grants.fsRead, undefined);
});

test("fs handles are not granted unless explicitly requested", () => {
  const sfs = tmpFs();
  // fs supplied but no fsWrite/fsRead flags -> no handles.
  const { grants } = grant({ fs: sfs });
  assert.equal(grants.fsWrite, undefined);
  assert.equal(grants.fsRead, undefined);
});

test("granted handles are frozen (agent cannot rebind the verb)", () => {
  const q = anyQueue();
  const { grants } = grant({ queueSend: q });
  assert.throws(() => {
    (grants.queueSend as { send: unknown }).send = () => {};
  });
});
