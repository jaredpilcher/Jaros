import { test } from "node:test";
import assert from "node:assert/strict";
import * as os from "os";
import * as fs from "fs";
import * as path from "path";
import { TransitionLog } from "./log";
import { ReplicatedLog, FileReplicaSink, ReplicationError, type ReplicaSink } from "./replication";
import type { LogEntry } from "./log";

function tmpDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "jaros-repl-"));
}

test("each appended entry is mirrored to every replica before acknowledge", () => {
  const dir = tmpDir();
  try {
    const primary = new TransitionLog(dir, "primary.log");
    const repA = new FileReplicaSink("A", new TransitionLog(dir, "a.log"));
    const repB = new FileReplicaSink("B", new TransitionLog(dir, "b.log"));
    const repl = new ReplicatedLog(primary, [repA, repB]);

    repl.append({ from: "PENDING", event: "START", to: "RUNNING" });
    repl.append({ from: "RUNNING", event: "COMPLETE", to: "DONE" });

    const toTuples = (es: LogEntry[]) => es.map((e) => [e.index, e.from, e.event, e.to]);
    const expected = [
      [1, "PENDING", "START", "RUNNING"],
      [2, "RUNNING", "COMPLETE", "DONE"],
    ];
    assert.deepEqual(toTuples(primary.read()), expected);
    assert.deepEqual(toTuples(repA.read()), expected);
    assert.deepEqual(toTuples(repB.read()), expected);
    assert.ok(repl.hasConverged());
    assert.equal(repl.convergedPrefix().length, 2);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("loss of a single replica loses no committed transition", () => {
  const dir = tmpDir();
  try {
    const primary = new TransitionLog(dir, "primary.log");
    const repA = new FileReplicaSink("A", new TransitionLog(dir, "a.log"));
    const repB = new FileReplicaSink("B", new TransitionLog(dir, "b.log"));
    const repl = new ReplicatedLog(primary, [repA, repB]);

    repl.append({ from: "PENDING", event: "START", to: "RUNNING" });
    repl.append({ from: "RUNNING", event: "COMPLETE", to: "DONE" });

    // Simulate losing replica B entirely (its file is destroyed).
    fs.rmSync(repB["log"].filePath, { force: true });

    // Every committed entry still survives on the primary and replica A.
    assert.equal(primary.read().length, 2);
    assert.equal(repA.read().length, 2);
    // The converged prefix collapses (B is now behind) but no data is lost...
    assert.ok(!repl.hasConverged());

    // ...and reconciliation brings B back to the full committed sequence.
    repl.reconcile();
    assert.equal(repB.read().length, 2);
    assert.ok(repl.hasConverged());
    assert.equal(repl.convergedPrefix().length, 2);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("a failing replica raises ReplicationError (entry not acknowledged)", () => {
  const dir = tmpDir();
  try {
    const primary = new TransitionLog(dir, "primary.log");
    const broken: ReplicaSink = {
      id: "broken",
      accept() {
        throw new Error("network partition");
      },
      read() {
        return [];
      },
    };
    const repl = new ReplicatedLog(primary, [broken]);
    assert.throws(
      () => repl.append({ from: "PENDING", event: "START", to: "RUNNING" }),
      (err: unknown) => {
        assert.ok(err instanceof ReplicationError);
        assert.equal((err as ReplicationError).replicaId, "broken");
        return true;
      }
    );
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("convergedPrefix is the longest index+checksum-agreed prefix", () => {
  const dir = tmpDir();
  try {
    const primary = new TransitionLog(dir, "primary.log");
    const repA = new FileReplicaSink("A", new TransitionLog(dir, "a.log"));
    const repl = new ReplicatedLog(primary, [repA]);

    repl.append({ from: "PENDING", event: "START", to: "RUNNING" });
    // Primary races ahead with a second entry the replica has not yet seen.
    primary.append({ from: "RUNNING", event: "COMPLETE", to: "DONE" });

    // Only the first entry is on both nodes -> converged prefix length 1.
    assert.equal(repl.convergedPrefix().length, 1);
    assert.ok(!repl.hasConverged());
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
