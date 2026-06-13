import { Fragment, useState } from "react";

import { api, type EvalReport } from "../api";
import { Card, Empty, Pill } from "../components/ui";

// #EXT-010-REQ-8 Start
export function Evals() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [running, setRunning] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setReport(null);
    try {
      setReport(await api.evals());
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="grid" style={{ gap: 16 }}>
      <Card
        title="Agent evaluations"
        desc="reproducible, declarative checks — input → expected decision/result, no model-grading flakiness"
        right={<button className="primary" disabled={running} onClick={run}>{running ? "Running…" : "▶ Run eval suite"}</button>}
      >
        {report ? (
          report.error ? (
            <div style={{ color: "var(--red)" }}>Eval error: {report.error}</div>
          ) : (
            <div className="grid cols-4">
              <div className="stat"><div className="label">Cases</div><div className="value">{report.total}</div></div>
              <div className="stat"><div className="label">Passed</div><div className="value green">{report.passed}</div></div>
              <div className="stat"><div className="label">Failed</div><div className="value" style={{ color: report.failed ? "var(--red)" : undefined }}>{report.failed}</div></div>
              <div className="stat"><div className="label">Suite</div><div style={{ marginTop: 8 }}><Pill tone={report.ok ? "ok" : "bad"}>{report.ok ? "green" : "failing"}</Pill></div></div>
            </div>
          )
        ) : (
          <div className="hint">
            Runs <code>evals/*.json</code> against the built-in + plugin agents and the loaded tools. Because reasoning emits inert data
            and execution is deterministic, results reproduce exactly — debuggable like any test.
          </div>
        )}
      </Card>

      {report && !report.error && (
        <Card title="Cases" desc="click a case to see its checks" right={<span className="hint mono">{report.passed}/{report.total}</span>}>
          {report.results.length === 0 ? (
            <Empty>No eval cases found in evals/. Add some to test your agents.</Empty>
          ) : (
            <table>
              <thead><tr><th></th><th>case</th><th>checks</th></tr></thead>
              <tbody>
                {report.results.map((r) => (
                  <Fragment key={r.case}>
                    <tr style={{ cursor: "pointer" }} onClick={() => setOpen(open === r.case ? null : r.case)}>
                      <td><Pill tone={r.passed ? "ok" : "bad"}>{r.passed ? "pass" : "fail"}</Pill></td>
                      <td style={{ fontFamily: "var(--sans)" }}>{r.case}</td>
                      <td style={{ color: "var(--muted)" }}>{r.checks.filter((c) => c.ok).length}/{r.checks.length} checks{r.error ? " · error" : ""}</td>
                    </tr>
                    {open === r.case && (
                      <tr>
                        <td colSpan={3} style={{ background: "var(--bg-grid)" }}>
                          {r.error && <div style={{ color: "var(--red)", marginBottom: 6 }}>error: {r.error}</div>}
                          {r.checks.map((c, i) => (
                            <div key={i} className="row" style={{ gap: 8, padding: "3px 0" }}>
                              <span className="tag" style={{ color: c.ok ? "var(--green)" : "var(--red)", borderColor: c.ok ? "var(--green-dim)" : "#6a2a2a" }}>{c.ok ? "ok" : "x"}</span>
                              <span className="mono" style={{ color: "var(--text-2)" }}>{c.name}</span>
                              {c.detail && <span className="hint">{c.detail}</span>}
                            </div>
                          ))}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}
// #EXT-010-REQ-8 End
