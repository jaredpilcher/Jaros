import { Fragment, useEffect, useState } from "react";

import { api, type DecisionRecord, type ReplayResult } from "../api";
import { Card, Empty, Json, Pill } from "../components/ui";

export function Replay() {
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [result, setResult] = useState<ReplayResult | null>(null);
  const [running, setRunning] = useState(false);

  async function refresh() {
    setDecisions(await api.decisions());
  }
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, []);

  async function runReplay() {
    setRunning(true);
    setResult(null);
    try {
      setResult(await api.replay());
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="grid" style={{ gap: 16 }}>
      <Card
        title="Reproducibility by replay"
        desc="the recorded decisions are the run's only non-deterministic input — re-execute them to reconstruct it exactly"
        right={
          <button className="primary" disabled={running || decisions.length === 0} onClick={runReplay}>
            {running ? "Replaying…" : "▶ Replay decision log"}
          </button>
        }
      >
        {result ? (
          result.ok ? (
            <div className="grid cols-4">
              <div className="stat"><div className="label">Decisions replayed</div><div className="value">{result.decisions}</div></div>
              <div className="stat"><div className="label">Reconstructed state</div><div className="value green" style={{ fontSize: 22 }}>{result.finalState}</div></div>
              <div className="stat"><div className="label">Model calls</div><div className="value">{result.modelCalls}</div><div className="foot">deterministic re-execution</div></div>
              <div className="stat">
                <div className="label">Byte-identical</div>
                <div style={{ marginTop: 8 }}>
                  <Pill tone={result.byteIdentical ? "ok" : "warn"}>{result.byteIdentical ? "identical" : "state-equal"}</Pill>
                </div>
                <div className="foot">{result.byteIdentical ? "transition log matches the original" : "final state matches; logs differ"}</div>
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--red)" }}>Replay error: {result.error}</div>
          )
        ) : (
          <div className="hint">
            Replaying feeds the recorded decisions back through the deterministic executor — with no model call — and rebuilds the run's
            state. Crash recovery is just a special case of this.
          </div>
        )}
      </Card>

      <Card title="Durable decision log" desc="state/decisions.log — append-only, one accepted decision per record" right={<span className="hint mono">{decisions.length} records</span>}>
        {decisions.length === 0 ? (
          <Empty>No decisions recorded yet. Submit a job, then replay it here.</Empty>
        ) : (
          <table>
            <thead>
              <tr><th>#</th><th>kind</th><th>source</th><th>decision id</th><th>checksum</th></tr>
            </thead>
            <tbody>
              {decisions.map((d) => (
                <Fragment key={d.index}>
                  <tr style={{ cursor: "pointer" }} onClick={() => setOpen(open === d.index ? null : d.index)}>
                    <td style={{ color: "var(--muted)" }}>{d.index}</td>
                    <td><span className="tag kind">{d.decision.kind}</span></td>
                    <td>{d.decision.source}</td>
                    <td style={{ color: "var(--muted)" }}>{d.decision.id.slice(0, 16)}</td>
                    <td style={{ color: "var(--green-dim)" }}>{d.checksum.slice(0, 10)}…</td>
                  </tr>
                  {open === d.index && (
                    <tr>
                      <td colSpan={5} style={{ background: "var(--bg-grid)" }}><Json value={d.decision.payload} /></td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
