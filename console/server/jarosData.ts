/**
 * File-system access layer for a running Jaros OS.
 *
 * The console never talks to the daemon over a socket — there is none. It reads
 * and writes the shared data directory exactly as the host CLI does: status.json,
 * the inbox/outbox, the durable decision + transition logs, and the agents/tools
 * drop folders. The Jaros node stays serverless; this is a host-side companion.
 */

import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

// #EXT-010-REQ-1 Start
export function resolveDataDir(): string {
  const fromArg = process.argv.find((a) => a.startsWith("--data-dir="));
  const dir =
    (fromArg ? fromArg.slice("--data-dir=".length) : undefined) ??
    process.env.JAROS_DATA_DIR ??
    ".jaros-data";
  return path.resolve(dir);
}

export const DATA_DIR = resolveDataDir();

function abs(rel: string): string {
  return path.join(DATA_DIR, rel);
}

function readTextSafe(rel: string): string | null {
  try {
    return fs.readFileSync(abs(rel), "utf-8");
  } catch {
    return null;
  }
}

function readJsonSafe<T = unknown>(rel: string): T | null {
  const raw = readTextSafe(rel);
  if (raw == null) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function listFiles(rel: string, ext?: string): string[] {
  try {
    return fs
      .readdirSync(abs(rel))
      .filter((f) => (ext ? f.endsWith(ext) : true))
      .sort();
  } catch {
    return [];
  }
}

/** Newline-delimited JSON log reader that tolerates a torn trailing line. */
function readNdjson<T>(rel: string): T[] {
  const raw = readTextSafe(rel);
  if (!raw) return [];
  const out: T[] = [];
  for (const line of raw.split("\n")) {
    if (!line.trim()) continue;
    try {
      out.push(JSON.parse(line) as T);
    } catch {
      // torn trailing / partial line — skip defensively
    }
  }
  return out;
}

export interface JarosStatus {
  state?: string;
  pool?: { bound: number; active: number; pending: number; agents: { id: string; state: string }[] };
  processed?: number;
  failed?: number;
  lastResult?: unknown;
  tick?: number;
  uptimeSec?: number;
}

export function getStatus(): JarosStatus | null {
  return readJsonSafe<JarosStatus>("status.json");
}

export interface DecisionRecord {
  index: number;
  decision: { id: string; source: string; kind: string; payload: unknown };
  checksum: string;
}

export function getDecisions(): DecisionRecord[] {
  return readNdjson<DecisionRecord>("state/decisions.log");
}

export interface TransitionEntry {
  index: number;
  event: string;
  state: string;
  checksum: string;
}

export function getTransitions(): TransitionEntry[] {
  return readNdjson<TransitionEntry>("state/transitions.log");
}

export interface JobSummary {
  id: string;
  kind?: string;
  area: "inbox" | "processed" | "failed";
  reason?: string;
}

export function getJobs(): JobSummary[] {
  const jobs: JobSummary[] = [];
  for (const area of ["inbox", "processed", "failed"] as const) {
    for (const file of listFiles(area, ".json")) {
      const id = file.replace(/\.json$/, "");
      const body = readJsonSafe<{ kind?: string }>(`${area}/${file}`);
      const reason =
        area === "failed" ? readTextSafe(`failed/${file}.reason`)?.trim() : undefined;
      jobs.push({ id, kind: body?.kind, area, reason: reason ?? undefined });
    }
  }
  return jobs;
}

export interface OutboxResult {
  id: string;
  kind?: string;
  result?: unknown;
}

export function getOutbox(): OutboxResult[] {
  return listFiles("outbox", ".json").map((file) => {
    const id = file.replace(/\.json$/, "");
    const body = readJsonSafe<{ kind?: string; result?: unknown }>(`outbox/${file}`);
    return { id, kind: body?.kind, result: body?.result };
  });
}

export function getAgents(): string[] {
  return listFiles("agents", ".py").filter((f) => !f.startsWith("_"));
}

export function getTools(): string[] {
  return listFiles("tools", ".py").filter((f) => !f.startsWith("_"));
}
// #EXT-010-REQ-1 End

// #EXT-010-REQ-3 Start
/** Atomically write a job descriptor into inbox/ (temp file + rename). */
export function submitJob(kind: string, input: unknown): { id: string } {
  const id = randomUUID().replace(/-/g, "");
  const inbox = abs("inbox");
  fs.mkdirSync(inbox, { recursive: true });
  const tmp = path.join(inbox, `.tmp-${id}`);
  const dest = path.join(inbox, `${id}.json`);
  fs.writeFileSync(tmp, JSON.stringify({ id, kind, input }, null, 2), "utf-8");
  fs.renameSync(tmp, dest);
  return { id };
}
// #EXT-010-REQ-3 End

// #EXT-010-REQ-4 Start
/** Atomically install an agent or custom tool module. */
export function installModule(area: "agents" | "tools", name: string, source: string): { path: string } {
  const safe = name.endsWith(".py") ? name : `${name}.py`;
  if (safe.includes("/") || safe.includes("\\") || safe.startsWith(".")) {
    throw new Error("invalid module name");
  }
  const dir = abs(area);
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, `.tmp-${randomUUID()}`);
  const dest = path.join(dir, safe);
  fs.writeFileSync(tmp, source, "utf-8");
  fs.renameSync(tmp, dest);
  return { path: `${area}/${safe}` };
}
// #EXT-010-REQ-4 End

// #EXT-010-REQ-7 Start
export interface ScheduleFile {
  name?: string;
  id?: string;
  kind?: string;
  input?: unknown;
  enabled?: boolean;
  every_seconds?: number;
  cron?: string;
  at?: string;
}

interface LiveSchedule {
  id: string;
  trigger?: string;
  lastRun?: string | null;
  nextRun?: string | null;
}

/** Read the operator schedule files (schedules/*.json), merged with live timing. */
export function getSchedules(): (ScheduleFile & { trigger?: string; lastRun?: string | null; nextRun?: string | null })[] {
  const status = getStatus() as unknown as { schedules?: LiveSchedule[] } | null;
  const live: LiveSchedule[] = status?.schedules ?? [];
  const byId = new Map(live.map((s) => [s.id, s] as const));
  return listFiles("schedules", ".json").map((file) => {
    const name = file.replace(/\.json$/, "");
    const body: ScheduleFile = readJsonSafe<ScheduleFile>(`schedules/${file}`) ?? {};
    const timing = body.id ? byId.get(body.id) : undefined;
    return { ...body, name, trigger: timing?.trigger, lastRun: timing?.lastRun ?? null, nextRun: timing?.nextRun ?? null };
  });
}

/** Atomically write/replace a schedule file (operator action). */
export function writeSchedule(name: string, body: Record<string, unknown>): { name: string } {
  const safe = name.endsWith(".json") ? name : `${name}.json`;
  if (safe.includes("/") || safe.includes("\\") || safe.startsWith(".")) {
    throw new Error("invalid schedule name");
  }
  const dir = abs("schedules");
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, `.tmp-${randomUUID()}`);
  const dest = path.join(dir, safe);
  fs.writeFileSync(tmp, JSON.stringify(body, null, 2), "utf-8");
  fs.renameSync(tmp, dest);
  return { name: safe };
}

/** Remove a schedule file (operator action). */
export function deleteSchedule(name: string): { removed: boolean } {
  const safe = name.endsWith(".json") ? name : `${name}.json`;
  if (safe.includes("/") || safe.includes("\\") || safe.startsWith(".")) {
    throw new Error("invalid schedule name");
  }
  try {
    fs.unlinkSync(abs(`schedules/${safe}`));
    return { removed: true };
  } catch {
    return { removed: false };
  }
}
// #EXT-010-REQ-7 End

export function dataDirExists(): boolean {
  try {
    return fs.statSync(DATA_DIR).isDirectory();
  } catch {
    return false;
  }
}
