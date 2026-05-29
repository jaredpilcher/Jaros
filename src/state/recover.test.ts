import { test } from "node:test";
import assert from "node:assert/strict";
import * as os from "os";
import * as fs from "fs";
import * as path from "path";
import { TransitionLog } from "./log";
import { commit } from "./machine";
import { recover } from "./recover";

function tmpDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "jaros-recover-"));
}

test("recover rebuilds state by replaying the log 1..N", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    let s = commit(log, "PENDING", "START").state; // RUNNING
    s = commit(log, s, "COMPLETE").state; // DONE
    // Simulate crash + restart: a fresh log over the same file.
    const recovered = recover(new TransitionLog(dir));
    assert.equal(recovered.state, "DONE");
    assert.equal(recovered.appliedCount, 2);
    assert.equal(recovered.discardedTornEntry, false);
    assert.equal(recovered.state, s);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("recover of an empty/missing log yields the initial state", () => {
  const dir = tmpDir();
  try {
    assert.equal(recover(new TransitionLog(dir)).state, "PENDING");
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("post-recovery state equals the pre-crash state when the final commit is torn", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    const s1 = commit(log, "PENDING", "START").state; // RUNNING, durable
    // Simulate an interrupted final commit: a torn, newline-less trailing entry.
    fs.appendFileSync(
      log.filePath,
      '{"index":2,"from":"RUNNING","event":"COMPLETE","to":"DON'
    );
    const recovered = recover(new TransitionLog(dir));
    // The torn entry is discarded; we recover the last durable state.
    assert.equal(recovered.state, s1);
    assert.equal(recovered.state, "RUNNING");
    assert.equal(recovered.appliedCount, 1);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("recover discards a checksum-corrupt trailing entry and everything after it", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    commit(log, "PENDING", "START"); // index 1, RUNNING
    // A complete line whose checksum does not match (silent corruption).
    fs.appendFileSync(
      log.filePath,
      JSON.stringify({
        index: 2,
        from: "RUNNING",
        event: "COMPLETE",
        to: "DONE",
        checksum: "deadbeef",
      }) + "\n"
    );
    const recovered = recover(new TransitionLog(dir));
    assert.equal(recovered.state, "RUNNING");
    assert.equal(recovered.appliedCount, 1);
    assert.equal(recovered.discardedTornEntry, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
