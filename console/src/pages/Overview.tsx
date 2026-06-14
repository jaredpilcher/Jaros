import { useEffect, useRef, useState } from "react";

import type { Snapshot } from "../api";
import { GetStarted } from "../components/GetStarted";
import { Card, Json, Sparkline, Stat, StateBadge, Tip } from "../components/ui";

// #EXT-010-REQ-2 Start
export function Overview({ snap, onTour }: { snap: Snapshot | null; onTour: () => void }) {
  const [history, setHistory] = useState<number[]>([]);
  const lastTs = useRef(0);

  useEffect(() => {
    if (!snap || snap.ts === lastTs.current) return;
    lastTs.current = snap.ts;
    setHistory((h) => [...h, snap.counts.processed].slice(-48));
  }, [snap]);

  if (!snap) return <Card>Connecting to the bridge…</Card>;

  const s = snap.status ?? {};
  const c = snap.counts;
  const uptime = s.uptimeSec ? `${Math.round(s.uptimeSec)}s` : "—";

  const allDone = snap.connected && c.processed > 0 && c.agents + c.tools > 0 && c.decisions > 0;

  return (
    <div className="grid" style={{ gap: 16 }}>
      {!allDone && <GetStarted snap={snap} onTour={onTour} />}

      <div className="grid cols-4">
        <Stat label="Machine state" value={<StateBadge state={s.state} />} foot={`tick ${s.tick ?? 0} · up ${uptime}`} />
        <Stat label="Processed" value={c.processed} tone="green" foot={`${c.outbox} results in outbox`} />
        <Stat label="Failed" value={c.failed} tone={c.failed ? "red" : undefined} foot={c.failed ? "see Jobs → failed" : "clean"} />
        <Stat label={<>Decisions logged <Tip text="Each accepted decision is recorded to state/decisions.log — the exact input replay re-applies to rebuild the run." /></>} value={c.decisions} foot="replayable to byte-identical state" />
      </div>

      <div className="grid cols-3">
        <Card title="Throughput" desc="processed jobs over recent ticks">
          <Sparkline data={history} width={300} height={70} />
          <div className="hint" style={{ marginTop: 8 }}>
            {history.length < 2 ? "gathering live samples…" : `${c.processed} total · ${c.inbox} queued`}
          </div>
        </Card>

        <Card title="Agent pool" desc="lightweight threads, bounded">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
            <span className="hint">active / bound</span>
            <span className="mono">
              {s.pool?.active ?? 0} / {s.pool?.bound ?? "—"}
            </span>
          </div>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
            <span className="hint">pending</span>
            <span className="mono">{s.pool?.pending ?? 0}</span>
          </div>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="hint">agents / tools</span>
            <span className="mono">
              {c.agents} / {c.tools}
            </span>
          </div>
        </Card>

        <Card title="Runtime profile">
          <div style={{ display: "grid", gap: 9 }}>
            {[
              ["No server", "no listening socket"],
              ["No database", "files are the store"],
              ["No broker", "in-process queues"],
            ].map(([k, v]) => (
              <div key={k} className="row" style={{ justifyContent: "space-between" }}>
                <span className="tag green">{k}</span>
                <span className="hint">{v}</span>
              </div>
            ))}
            <div className="hint" style={{ marginTop: 2 }}>zero-infrastructure · single-node-first</div>
          </div>
        </Card>
      </div>

      <Card title="Last result" desc="most recent job output the daemon wrote">
        {s.lastResult ? <Json value={s.lastResult} /> : <div className="hint">No jobs processed yet.</div>}
      </Card>
    </div>
  );
}
// #EXT-010-REQ-2 End
