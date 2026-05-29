import { test } from "node:test";
import assert from "node:assert/strict";
import * as os from "os";
import * as nodeFs from "fs";
import * as nodePath from "path";
import {
  SharedFileSystem,
  LayoutViolationError,
  LAYOUT_DIRS,
} from "./fs";

function makeTempBase(): string {
  return nodeFs.mkdtempSync(nodePath.join(os.tmpdir(), "jaros-fs-"));
}

function cleanup(base: string): void {
  nodeFs.rmSync(base, { recursive: true, force: true });
}

test("write + read round-trip within the layout", () => {
  const base = makeTempBase();
  try {
    const sfs = new SharedFileSystem(base).ensureLayout();
    sfs.write("outbox/result.txt", "hello fabric");
    assert.equal(sfs.read("outbox/result.txt"), "hello fabric");
    // Round-trips into each canonical dir.
    for (const dir of LAYOUT_DIRS) {
      sfs.write(`${dir}/probe.txt`, dir);
      assert.equal(sfs.read(`${dir}/probe.txt`), dir);
    }
  } finally {
    cleanup(base);
  }
});

test("write refuses path traversal escaping the layout", () => {
  const base = makeTempBase();
  try {
    const sfs = new SharedFileSystem(base).ensureLayout();
    assert.throws(
      () => sfs.write("../escape.txt", "nope"),
      (err: unknown) => {
        assert.ok(err instanceof LayoutViolationError, "expected LayoutViolationError");
        return true;
      }
    );
    assert.throws(
      () => sfs.write("outbox/../../escape.txt", "nope"),
      LayoutViolationError
    );
    // Nothing leaked outside the base dir.
    assert.equal(nodeFs.existsSync(nodePath.join(base, "..", "escape.txt")), false);
  } finally {
    cleanup(base);
  }
});

test("write refuses an absolute path", () => {
  const base = makeTempBase();
  try {
    const sfs = new SharedFileSystem(base).ensureLayout();
    const abs = nodePath.join(os.tmpdir(), "jaros-abs-escape.txt");
    assert.throws(() => sfs.write(abs, "nope"), LayoutViolationError);
    assert.equal(nodeFs.existsSync(abs), false);
  } finally {
    cleanup(base);
  }
});

test("validateLayout passes on a freshly created layout", () => {
  const base = makeTempBase();
  try {
    const sfs = new SharedFileSystem(base).ensureLayout();
    assert.doesNotThrow(() => sfs.validateLayout());
  } finally {
    cleanup(base);
  }
});

test("validateLayout fails loudly when a canonical dir is missing", () => {
  const base = makeTempBase();
  try {
    const sfs = new SharedFileSystem(base).ensureLayout();
    nodeFs.rmSync(nodePath.join(base, "inbox"), { recursive: true, force: true });
    assert.throws(() => sfs.validateLayout(), (err: unknown) => {
      assert.ok(err instanceof LayoutViolationError);
      assert.match((err as LayoutViolationError).message, /inbox/);
      return true;
    });
  } finally {
    cleanup(base);
  }
});
