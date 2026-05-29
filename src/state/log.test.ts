import { test } from "node:test";
import assert from "node:assert/strict";
import * as os from "os";
import * as fs from "fs";
import * as path from "path";
import { TransitionLog, parseEntry, checksumOf } from "./log";

function tmpDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "jaros-log-"));
}

test("append then read preserves order and assigns 1-indexed positions", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    log.append({ from: "PENDING", event: "START", to: "RUNNING" });
    log.append({ from: "RUNNING", event: "COMPLETE", to: "DONE" });
    const entries = log.read();
    assert.equal(entries.length, 2);
    assert.deepEqual(
      entries.map((e) => [e.index, e.from, e.event, e.to]),
      [
        [1, "PENDING", "START", "RUNNING"],
        [2, "RUNNING", "COMPLETE", "DONE"],
      ]
    );
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("read of a missing log returns empty (no throw)", () => {
  const dir = tmpDir();
  try {
    assert.deepEqual(new TransitionLog(dir).read(), []);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("each appended entry carries a matching checksum", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    const e = log.append({ from: "PENDING", event: "START", to: "RUNNING" });
    assert.equal(e.checksum, checksumOf(1, "PENDING", "START", "RUNNING"));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("a torn (newline-less) trailing line is skipped by read", () => {
  const dir = tmpDir();
  try {
    const log = new TransitionLog(dir);
    log.append({ from: "PENDING", event: "START", to: "RUNNING" });
    // Simulate an interrupted write: a partial JSON fragment with no newline.
    fs.appendFileSync(log.filePath, '{"index":2,"from":"RUNNING","ev');
    const entries = log.read();
    assert.equal(entries.length, 1, "torn trailing fragment must be ignored");
    assert.equal(entries[0].index, 1);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("parseEntry returns null for blank or malformed lines", () => {
  assert.equal(parseEntry(""), null);
  assert.equal(parseEntry("   "), null);
  assert.equal(parseEntry("{not json"), null);
  assert.equal(parseEntry('{"index":1}'), null);
});

test("the log exposes no mutate or delete method (append-only surface)", () => {
  const log = new TransitionLog(tmpDir());
  const surface = Object.getOwnPropertyNames(Object.getPrototypeOf(log));
  for (const forbidden of ["delete", "remove", "update", "mutate", "truncate", "clear"]) {
    assert.ok(!surface.includes(forbidden), `log must not expose "${forbidden}"`);
  }
  assert.ok(surface.includes("append"));
  assert.ok(surface.includes("read"));
});
