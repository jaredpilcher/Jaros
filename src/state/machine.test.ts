import { test } from "node:test";
import assert from "node:assert/strict";
import * as os from "os";
import * as fs from "fs";
import * as path from "path";
import {
  transition,
  commit,
  assertValidState,
  UndefinedTransitionError,
  InvalidStateError,
} from "./machine";
import { TransitionLog, type LogEntryInput } from "./log";

function tmpDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "jaros-machine-"));
}

test("valid transition returns the next state", () => {
  assert.equal(transition("PENDING", "START"), "RUNNING");
  assert.equal(transition("RUNNING", "COMPLETE"), "DONE");
  assert.equal(transition("FAILED", "RETRY"), "PENDING");
});

test("undefined (state,event) is rejected with a typed error and no mutation", () => {
  let state = "DONE" as const;
  assert.throws(
    () => {
      state = transition("DONE", "START") as typeof state;
    },
    (err: unknown) => {
      assert.ok(err instanceof UndefinedTransitionError, "expected UndefinedTransitionError");
      assert.equal((err as UndefinedTransitionError).state, "DONE");
      assert.equal((err as UndefinedTransitionError).event, "START");
      return true;
    }
  );
  assert.equal(state, "DONE", "state must be unchanged after a rejected transition");
});

test("assertValidState enforces the declared-state invariant", () => {
  assert.doesNotThrow(() => assertValidState("RUNNING"));
  assert.throws(() => assertValidState("WAT"), InvalidStateError);
});

test("commit appends to the log then applies (durable before observable)", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    const r1 = commit(log, "PENDING", "START");
    assert.equal(r1.state, "RUNNING");
    assert.equal(r1.entry.index, 1);
    // The entry is durable: visible via a fresh log over the same file.
    const reread = new TransitionLog(dir).read();
    assert.equal(reread.length, 1);
    assert.equal(reread[0].to, "RUNNING");
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("commit does NOT apply (or log) when the append fails", () => {
  const dir = tmpDir();
  try {
    // A log whose append always throws (simulated I/O failure).
    const log = new TransitionLog(dir);
    const failing = Object.create(TransitionLog.prototype) as TransitionLog;
    Object.assign(failing, log);
    (failing as unknown as { append: (i: LogEntryInput) => never }).append = () => {
      throw new Error("disk full");
    };

    const before = "PENDING" as const;
    let after: string = before;
    assert.throws(() => {
      after = commit(failing, before, "START").state;
    }, /disk full/);
    assert.equal(after, before, "state must not advance when append fails");
    // Nothing was persisted.
    assert.equal(new TransitionLog(dir).read().length, 0);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("commit rejects an undefined transition without touching the log", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    assert.throws(() => commit(log, "DONE", "START"), UndefinedTransitionError);
    assert.equal(log.read().length, 0);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
