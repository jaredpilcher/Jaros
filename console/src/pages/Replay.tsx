import { Fragment, useEffect, useState } from "react";

import { api, type DecisionRecord, type ReplayResult } from "../api";
import { Card, Empty, Json, PageIntro, Pill, Tip } from "../components/ui";

// #EXT-010-REQ-5 Start
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
      <PageIntro icon="↻" sub="Replay runs in an isolated sandbox and never touches the live data dir." to="/help#replay">
        Jaros's headline guarantee: rebuild any run from the decision log <b>byte-identically</b>, with <b>zero model calls</b>.
      </PageIntro>
      <Card
        title={<>Reproducibility by replay <Tip text="The recorded decisions are the run's only non-deterministic input. Re-applying them through the same deterministic handlers reconstructs the run exactly." /></>}
        desc="the recorded decisions are the run's only non-deterministic input — re-execute them to reconstruct it exactly"
        right={
          <button className="primary" disabled={running || decisions.length === 0} onClick={runReplay}>
            {running ? "Replaying…" : "▶ Replay decision log"}
          </button>
        }
      >
        {result ? (
          result.error ? (
            <div style={{ color: "var(--red)" }}>Replay error: {result.error}</div>
          ) : (
            <div className="grid" style={{ gap: 14 }}>
              <div className="grid cols-4">
                <div className="stat"><div className="label">Decisions replayed</div><div className="value">{result.decisions}</div></div>
                <div className="stat"><div className="label">Reconstructed state</div><div className="value green" style={{ fontSize: 22 }}>{result.finalState}</div></div>
                <div className="stat">
                  <div className="label">Byte-identical</div>
                  <div style={{ marginTop: 8 }}><Pill tone={result.byteIdentical ? "ok" : "warn"}>{result.byteIdentical ? "identical" : "diverged"}</Pill></div>
                  <div className="foot">{result.byteIdentical ? "whole swarm matches the live run" : "a handler diverged"}</div>
                </div>
                <div className="stat">
                  <div className="label">Tamper-evident chain</div>
                  <div style={{ marginTop: 8 }}><Pill tone={result.chainOk === false ? "bad" : "ok"}>{result.chainOk === false ? "broken" : "intact"}</Pill></div>
                  <div className="foot">model calls: {result.modelCalls}</div>
                </div>
              </div>

              {result.byAgent && Object.keys(result.byAgent).length > 0 && (
                <div>
                  <div className="section-title">Per-agent provenance · who did how much</div>
                  <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
                    {Object.entries(result.byAgent).map(([src, n]) => (
                      <span key={src} className="tag green">◆ {src}: {n}</span>
                    ))}
                  </div>
                </div>
              )}

              {result.attribution ? (
                <div className="card" style={{ padding: 13, borderColor: result.attribution.kind === "divergence" ? "#6a2a2a" : "#6a5b1e" }}>
                  <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
                    <Pill tone={result.attribution.kind === "divergence" ? "bad" : "warn"}>{result.attribution.kind}</Pill>
                    <span>attributed to agent <b style={{ color: "var(--yellow)" }}>{result.attribution.source}</b> — decision #{result.attribution.index} <span className="mono hint">({result.attribution.id.slice(0, 20)})</span></span>
                  </div>
                  <div className="hint" style={{ marginTop: 7 }}>{result.attribution.reason}</div>
                </div>
              ) : (
                <div className="hint">Reproduced the whole swarm byte-identically, with no model call — every member's decisions in recorded order.</div>
              )}
            </div>
          )
        ) : (
          <div className="hint">
            Replaying feeds every member's recorded decisions back through the deterministic executor — with no model call — rebuilding the
            whole swarm's state and attributing any failure to the exact agent. Crash recovery is just a special case of this.
          </div>
        )}
      </Card>

      <Card title="Durable decision log" desc="state/decisions.log — append-only, one accepted decision per record" right={<span className="hint mono">{decisions.length} records</span>}>
        {decisions.length === 0 ? (
          <Empty>No decisions recorded yet. Submit a job, then replay it here.</Empty>
        ) : (
          <table>
            <thead>
              <tr><th>#</th><th>type</th><th>source</th><th>decision id</th><th>checksum</th></tr>
            </thead>
            <tbody>
              {decisions.map((d) => (
                <Fragment key={d.index}>
                  <tr style={{ cursor: "pointer" }} onClick={() => setOpen(open === d.index ? null : d.index)}>
                    <td style={{ color: "var(--muted)" }}>{d.index}</td>
                    <td><span className="tag kind">{d.decision.type}</span></td>
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
// #EXT-010-REQ-5 End
