/** Typed client for the Jaros Console bridge API + a live SSE hook. */

import { useEffect, useRef, useState } from "react";

export interface Status {
  state?: string;
  pool?: { bound: number; active: number; pending: number; agents: { id: string; state: string }[] };
  processed?: number;
  failed?: number;
  lastResult?: unknown;
  tick?: number;
  uptimeSec?: number;
}

export interface Snapshot {
  ts: number;
  connected: boolean;
  status: Status | null;
  counts: {
    inbox: number;
    processed: number;
    failed: number;
    outbox: number;
    decisions: number;
    agents: number;
    tools: number;
  };
}

export interface Job { id: string; agent?: string; area: "inbox" | "processed" | "failed"; reason?: string }
export interface OutboxResult { id: string; agent?: string; result?: unknown }
export interface DecisionRecord {
  index: number;
  decision: { id: string; source: string; type: string; payload: unknown };
  checksum: string;
}
export interface TransitionEntry { index: number; event: string; state: string; checksum: string }
export interface Agents { agents: string[]; tools: string[] }
export interface ScheduleRow {
  name: string;
  id?: string;
  agent?: string;
  input?: unknown;
  enabled?: boolean;
  every_seconds?: number;
  cron?: string;
  at?: string;
  trigger?: string;
  lastRun?: string | null;
  nextRun?: string | null;
}
export interface StateModel {
  states: string[];
  events: string[];
  initial: string;
  transitions: { from: string; event: string; to: string }[];
  error?: string;
}
export interface HarnessModel { rules: Record<string, string>; roles: Record<string, string[]>; error?: string }
export interface EvalCheck { name: string; ok: boolean; detail: string }
export interface EvalCaseResult { case: string; passed: boolean; error: string | null; checks: EvalCheck[] }
export interface EvalReport {
  total: number;
  passed: number;
  failed: number;
  ok: boolean;
  results: EvalCaseResult[];
  error?: string;
}
export interface Attribution {
  kind: "failure" | "divergence";
  index: number;
  id: string;
  source: string;
  reason: string;
}
export interface ReplayResult {
  decisions: number;
  applied: number;
  finalState: string;
  byteIdentical: boolean;
  deterministic: boolean;
  modelCalls: number;
  ok: boolean;
  byAgent?: Record<string, number>;
  chainOk?: boolean;
  attribution?: Attribution | null;
  error?: string;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`);
  return (await r.json()) as T;
}
async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return (await r.json()) as T;
}

export const api = {
  snapshot: () => get<Snapshot>("/snapshot"),
  jobs: () => get<Job[]>("/jobs"),
  submitJob: (agent: string, input: string) => post<{ id?: string; error?: string }>("/jobs", { agent, input }),
  outbox: () => get<OutboxResult[]>("/outbox"),
  decisions: () => get<DecisionRecord[]>("/decisions"),
  transitions: () => get<TransitionEntry[]>("/transitions"),
  agents: () => get<Agents>("/agents"),
  installAgent: (name: string, source: string) => post<{ path?: string; error?: string }>("/agents", { name, source }),
  installTool: (name: string, source: string) => post<{ path?: string; error?: string }>("/tools", { name, source }),
  model: () => get<StateModel>("/model"),
  harness: () => get<HarnessModel>("/harness"),
  replay: () => post<ReplayResult>("/replay", {}),
  evals: () => post<EvalReport>("/evals", {}),
  schedules: () => get<ScheduleRow[]>("/schedules"),
  createSchedule: (name: string, schedule: Record<string, unknown>) =>
    post<{ name?: string; error?: string }>("/schedules", { name, schedule }),
  deleteSchedule: async (name: string) => {
    const r = await fetch(`/api/schedules?name=${encodeURIComponent(name)}`, { method: "DELETE" });
    return (await r.json()) as { removed?: boolean; error?: string };
  },
};

/** Subscribe to the live event stream; falls back to polling if SSE drops. */
export function useLiveSnapshot(): Snapshot | null {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/events");
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        setSnap(JSON.parse(e.data));
      } catch {
        /* ignore */
      }
    };
    es.onerror = () => {
      // EventSource auto-reconnects; nothing to do.
    };
    return () => es.close();
  }, []);

  return snap;
}
