import { useEffect, useState } from "react";

import { api, type Job, type OutboxResult } from "../api";
import { Card, Empty, Json, PageIntro, Tip } from "../components/ui";

const PRESETS: { kind: string; input: string }[] = [
  { kind: "advance", input: "{}" },
  { kind: "echo", input: '{ "msg": "hello from the console" }' },
  { kind: "greeter", input: '{ "name": "Jaros" }' },
];

// #EXT-010-REQ-3 Start
export function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [outbox, setOutbox] = useState<OutboxResult[]>([]);
  const [kind, setKind] = useState("advance");
  const [input, setInput] = useState("{}");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [sel, setSel] = useState<OutboxResult | null>(null);

  async function refresh() {
    setJobs(await api.jobs());
    setOutbox(await api.outbox());
  }
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, []);

  async function submit() {
    setMsg(null);
    const r = await api.submitJob(kind, input);
    if (r.error) setMsg({ ok: false, text: r.error });
    else {
      setMsg({ ok: true, text: `submitted ${kind} → inbox/${r.id}.json` });
      refresh();
    }
  }

  const byArea = (a: Job["area"]) => jobs.filter((j) => j.area === a);

  return (
    <>
    <PageIntro icon="▣" sub="Pick a preset for a one-click start, or enter any agent kind." to="/help#jobs">
      Submit a job and watch it flow <b>inbox → processed → outbox</b>. A job is the only way work enters Jaros.
    </PageIntro>
    <div className="grid cols-2" style={{ alignItems: "start" }}>
      <div className="grid" style={{ gap: 16 }}>
        <Card title={<>Submit a job <Tip text="The kind selects which agent reasons over the job; the JSON input is passed to it as context." /></>} desc="written atomically to the shared inbox — the only entry point">
          <label className="field">Agent kind</label>
          <div className="row" style={{ marginBottom: 12, flexWrap: "wrap" }}>
            <input value={kind} onChange={(e) => setKind(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
            {PRESETS.map((p) => (
              <button
                key={p.kind}
                onClick={() => {
                  setKind(p.kind);
                  setInput(p.input);
                }}
              >
                {p.kind}
              </button>
            ))}
          </div>
          <label className="field">Input (JSON)</label>
          <textarea rows={5} value={input} onChange={(e) => setInput(e.target.value)} style={{ marginBottom: 12 }} />
          <div className="row">
            <button className="primary" onClick={submit}>
              Submit job
            </button>
            {msg && <span className={`tag ${msg.ok ? "green" : ""}`} style={{ color: msg.ok ? "var(--green)" : "var(--red)" }}>{msg.text}</span>}
          </div>
        </Card>

        <Card title="Queue" desc="inbox · processed · failed" right={<span className="hint mono">{jobs.length} total</span>}>
          {(["inbox", "processed", "failed"] as const).map((area) => (
            <div key={area} className="mb">
              <div className="section-title">{area} · {byArea(area).length}</div>
              {byArea(area).length === 0 ? (
                <div className="hint">none</div>
              ) : (
                <table>
                  <tbody>
                    {byArea(area).map((j) => (
                      <tr key={j.id}>
                        <td><span className="tag kind">{j.kind ?? "?"}</span></td>
                        <td style={{ color: "var(--muted)" }}>{j.id.slice(0, 12)}</td>
                        {area === "failed" && <td style={{ color: "var(--red)" }}>{j.reason}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ))}
        </Card>
      </div>

      <Card title="Outbox results" desc="job outputs the daemon wrote back" right={<span className="hint mono">{outbox.length}</span>}>
        {outbox.length === 0 ? (
          <Empty>No results yet — submit a job.</Empty>
        ) : (
          <div className="grid" style={{ gap: 8 }}>
            {outbox.map((o) => (
              <div
                key={o.id}
                className="card"
                style={{ padding: 12, cursor: "pointer", borderColor: sel?.id === o.id ? "var(--green-dim)" : undefined }}
                onClick={() => setSel(sel?.id === o.id ? null : o)}
              >
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className="tag kind">{o.kind ?? "?"}</span>
                  <span className="hint mono">{o.id.slice(0, 12)}</span>
                </div>
                {sel?.id === o.id && <div style={{ marginTop: 10 }}><Json value={o.result} /></div>}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
    </>
  );
}
// #EXT-010-REQ-3 End
