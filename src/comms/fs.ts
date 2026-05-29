import * as nodeFs from "fs";
import * as nodePath from "path";

// #EXT-006-REQ-2 Start
/**
 * Shared file system — the second (and only other) sanctioned inter-agent
 * channel alongside the rigid queue (`./queue`). It is the durable exchange
 * surface: agents communicate by writing/reading artifacts under a fixed,
 * canonical layout, never by addressing one another directly.
 *
 * Canonical layout (workspace-relative, rooted at a configurable base dir):
 *
 *   <base>/state       durable agent/system state
 *   <base>/inbox       messages/work delivered to an agent
 *   <base>/outbox      messages/work produced by an agent
 *   <base>/artifacts   produced files (outputs, logs, blobs)
 *
 * Access rules ([REQ-2], [REQ-4]):
 *   - All exchange uses workspace-relative paths that resolve *within* the
 *     layout. Absolute paths and `..` traversal that escape the base are
 *     refused with a typed {@link LayoutViolationError} before any I/O.
 *   - The on-disk structure is validated against the canonical layout via
 *     {@link validateLayout}.
 *
 * The default base dir is `.jaros-data/` (workspace-relative); tests pass a
 * temp dir so they never touch the real workspace.
 */

/** The four canonical, workspace-relative top-level directories of the layout. */
export const LAYOUT_DIRS = ["state", "inbox", "outbox", "artifacts"] as const;

/** A canonical top-level layout directory name. */
export type LayoutDir = (typeof LAYOUT_DIRS)[number];

/** Default workspace-relative base directory for the shared file system. */
export const DEFAULT_BASE_DIR = ".jaros-data";

/**
 * Typed error raised on any access that violates the canonical layout: a write
 * outside the layout, a path that escapes the base via traversal/absolute
 * escape, or an on-disk structure that does not match. Layout violations fail
 * loudly ([REQ-4]).
 */
export class LayoutViolationError extends Error {
  /** The offending path or detail (kept for diagnostics). */
  readonly detail: string;

  constructor(message: string, detail: string) {
    super(message);
    this.name = "LayoutViolationError";
    this.detail = detail;
    Object.setPrototypeOf(this, LayoutViolationError.prototype);
  }
}

/**
 * The shared file system rooted at a single base directory. Every method
 * operates on workspace-relative paths and refuses anything that would resolve
 * outside the base.
 */
export class SharedFileSystem {
  /** Absolute, normalized base directory containing the canonical layout. */
  readonly baseDir: string;

  constructor(baseDir: string = DEFAULT_BASE_DIR) {
    this.baseDir = nodePath.resolve(baseDir);
  }

  /**
   * Create the base dir and all canonical layout directories if absent. Safe to
   * call repeatedly (idempotent). Returns this instance for chaining.
   */
  ensureLayout(): this {
    nodeFs.mkdirSync(this.baseDir, { recursive: true });
    for (const dir of LAYOUT_DIRS) {
      nodeFs.mkdirSync(nodePath.join(this.baseDir, dir), { recursive: true });
    }
    return this;
  }

  /**
   * Resolve a workspace-relative path to an absolute path that is guaranteed to
   * live within {@link baseDir}. Throws {@link LayoutViolationError} for
   * absolute inputs or any `..` traversal that escapes the base.
   */
  resolve(relativePath: string): string {
    if (typeof relativePath !== "string" || relativePath.length === 0) {
      throw new LayoutViolationError(
        "Path must be a non-empty workspace-relative string.",
        String(relativePath)
      );
    }
    if (nodePath.isAbsolute(relativePath)) {
      throw new LayoutViolationError(
        "Absolute paths are not permitted; use a workspace-relative path within the layout.",
        relativePath
      );
    }

    const resolved = nodePath.resolve(this.baseDir, relativePath);
    // The resolved path must be the base dir itself or strictly contained in it.
    const baseWithSep = this.baseDir.endsWith(nodePath.sep)
      ? this.baseDir
      : this.baseDir + nodePath.sep;
    if (resolved !== this.baseDir && !resolved.startsWith(baseWithSep)) {
      throw new LayoutViolationError(
        "Path escapes the shared file system layout.",
        relativePath
      );
    }
    return resolved;
  }

  /**
   * Read a UTF-8 file at a workspace-relative path within the layout. Throws
   * {@link LayoutViolationError} if the path escapes the layout.
   */
  read(relativePath: string): string {
    const abs = this.resolve(relativePath);
    return nodeFs.readFileSync(abs, "utf8");
  }

  /**
   * Write `data` to a workspace-relative path within the layout, creating
   * parent directories as needed. Refuses (throws {@link LayoutViolationError})
   * any path that resolves outside the layout — traversal or absolute escape.
   */
  write(relativePath: string, data: string): void {
    const abs = this.resolve(relativePath);
    nodeFs.mkdirSync(nodePath.dirname(abs), { recursive: true });
    nodeFs.writeFileSync(abs, data, "utf8");
  }

  /**
   * Assert the on-disk structure matches the canonical layout: the base dir and
   * each of the four canonical directories must exist as directories. Throws
   * {@link LayoutViolationError} describing the first missing/invalid entry.
   */
  validateLayout(): void {
    if (!isDirectory(this.baseDir)) {
      throw new LayoutViolationError(
        "Shared file system base directory is missing or not a directory.",
        this.baseDir
      );
    }
    for (const dir of LAYOUT_DIRS) {
      const full = nodePath.join(this.baseDir, dir);
      if (!isDirectory(full)) {
        throw new LayoutViolationError(
          `Canonical layout directory "/${dir}" is missing or not a directory.`,
          full
        );
      }
    }
  }
}

/** True when `p` exists and is a directory. */
function isDirectory(p: string): boolean {
  try {
    return nodeFs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}
// #EXT-006-REQ-2 End
