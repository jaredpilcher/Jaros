import * as nodeFs from "fs";
import * as nodePath from "path";
import type { Event, State } from "./model";

// #EXT-002-REQ-3 Start
/**
 * The durable, append-only transition log ([REQ-3]). Every accepted transition
 * is persisted here before it is considered committed / observable. The store is
 * a single newline-delimited JSON (NDJSON) file under a configurable base
 * directory, so tests can point it at an `os.tmpdir()` location and never touch
 * the real workspace.
 *
 * Append-only API surface: the only mutating operation is {@link append}. There
 * is deliberately no update or delete method — existing entries are never
 * mutated or removed in normal operation. {@link read} streams entries back in
 * the exact order they were appended.
 *
 * Durability: {@link append} opens the file in append mode, writes the entry,
 * and `fsync`s the file descriptor before returning, so a committed entry
 * survives a crash. A torn (partially written) trailing line is tolerated by the
 * reader and by recovery (`./recover`).
 */

/** A single immutable log entry recording one committed transition. */
export interface LogEntry {
  /** 1-indexed position of this entry in the log. */
  readonly index: number;
  /** The state the machine was in before the transition. */
  readonly from: State;
  /** The event that drove the transition. */
  readonly event: Event;
  /** The resulting state after the transition. */
  readonly to: State;
  /** Checksum over `index|from|event|to`, used for replica reconciliation. */
  readonly checksum: string;
}

/** Fields of a {@link LogEntry} the caller supplies; index/checksum are derived. */
export type LogEntryInput = Pick<LogEntry, "from" | "event" | "to">;

/** Default workspace-relative directory for the transition log. */
export const DEFAULT_LOG_DIR = ".jaros-data/state";

/** Default file name for the append-only log within the base directory. */
export const DEFAULT_LOG_FILE = "transition.log";

/**
 * A small, dependency-free checksum (FNV-1a 32-bit, hex) over the canonical
 * fields of an entry. Strong enough to detect divergence / corruption between
 * replicas without pulling in a crypto dependency.
 */
export function checksumOf(index: number, from: State, event: Event, to: State): string {
  const data = `${index}|${from}|${event}|${to}`;
  let hash = 0x811c9dc5;
  for (let i = 0; i < data.length; i++) {
    hash ^= data.charCodeAt(i);
    // 32-bit FNV prime multiply via shifts to stay in integer range.
    hash = (hash + ((hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24))) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

/** Serialize one entry to a single NDJSON line (terminated with `\n`). */
export function serializeEntry(entry: LogEntry): string {
  return JSON.stringify(entry) + "\n";
}

/**
 * Parse one NDJSON line into a {@link LogEntry}, or return `null` if the line is
 * empty, torn (not terminated by a newline at the caller's level), or otherwise
 * not a complete, well-formed entry. Never throws — callers treat `null` as "no
 * usable entry" so a torn trailing write does not crash recovery.
 */
export function parseEntry(line: string): LogEntry | null {
  const trimmed = line.trim();
  if (trimmed.length === 0) {
    return null;
  }
  try {
    const obj = JSON.parse(trimmed) as Partial<LogEntry>;
    if (
      typeof obj.index !== "number" ||
      typeof obj.from !== "string" ||
      typeof obj.event !== "string" ||
      typeof obj.to !== "string" ||
      typeof obj.checksum !== "string"
    ) {
      return null;
    }
    return obj as LogEntry;
  } catch {
    return null;
  }
}

/**
 * Durable append-only transition log backed by a single NDJSON file. The public
 * surface is intentionally append-only: {@link append} and read-only accessors
 * only — there is no mutate or delete.
 */
export class TransitionLog {
  /** Absolute path to the NDJSON log file. */
  readonly filePath: string;

  constructor(baseDir: string = DEFAULT_LOG_DIR, fileName: string = DEFAULT_LOG_FILE) {
    this.filePath = nodePath.resolve(baseDir, fileName);
  }

  /** Ensure the containing directory exists. Idempotent; returns this. */
  ensure(): this {
    nodeFs.mkdirSync(nodePath.dirname(this.filePath), { recursive: true });
    return this;
  }

  /**
   * Append a transition to durable storage and return the persisted
   * {@link LogEntry} (with its assigned 1-indexed position and checksum). The
   * write is `fsync`ed before returning, so on success the entry is durable.
   *
   * This is the ONLY mutating operation. Existing entries are never touched.
   */
  append(input: LogEntryInput): LogEntry {
    this.ensure();
    const index = this.length() + 1;
    const checksum = checksumOf(index, input.from, input.event, input.to);
    const entry: LogEntry = { index, from: input.from, event: input.event, to: input.to, checksum };
    const fd = nodeFs.openSync(this.filePath, "a");
    try {
      nodeFs.writeSync(fd, serializeEntry(entry));
      nodeFs.fsyncSync(fd);
    } finally {
      nodeFs.closeSync(fd);
    }
    return entry;
  }

  /**
   * Read all entries in append order. A torn / partially-written trailing line
   * (e.g. an interrupted commit) is silently skipped rather than throwing, so
   * the log remains readable after a crash. Recovery (`./recover`) relies on
   * this lenient behavior.
   */
  read(): LogEntry[] {
    let raw: string;
    try {
      raw = nodeFs.readFileSync(this.filePath, "utf8");
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") {
        return [];
      }
      throw err;
    }
    const entries: LogEntry[] = [];
    for (const line of raw.split("\n")) {
      const parsed = parseEntry(line);
      if (parsed !== null) {
        entries.push(parsed);
      }
    }
    return entries;
  }

  /** Number of well-formed entries currently in the log. */
  length(): number {
    return this.read().length;
  }
}
// #EXT-002-REQ-3 End
