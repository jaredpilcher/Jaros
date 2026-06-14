import { useEffect, useState } from "react";

import { api, type StateModel, type TransitionEntry } from "../api";
import { Card, Empty, StateBadge } from "../components/ui";

// #EXT-010-REQ-6 Start
export function StateMachine() {
  const [model, setModel] = useState<StateModel | null>(null);
  const [log, setLog] = useState<TransitionEntry[]>([]);

  useEffect(() => {
    api.model().then(setModel);
    const refresh = () => api.transitions().then(setLog);
    refresh();
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, []);

  if (model?.error) return <Card title="State model">Could not introspect: {model.error}</Card>;
  if (!model) return <Card>Loading the state model…</Card>;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <Card title="States" desc={`single source of truth · initial = ${model.initial}`}>
        <div className="row" style={{ flexWrap: "wrap", gap: 12 }}>
          {model.states.map((st) => (
            <div key={st} className="card" style={{ padding: "12px 16px", minWidth: 120, textAlign: "center", borderColor: st === model.initial ? "var(--green-dim)" : undefined }}>
              <StateBadge state={st} />
              {st === model.initial && <div className="hint" style={{ marginTop: 6 }}>initial</div>}
            </div>
          ))}
        </div>
      </Card>

      <div className="grid cols-2" style={{ alignItems: "start" }}>
        <Card title="Transition table" desc="only declared transitions are permitted; everything else is rejected">
          <table>
            <thead><tr><th>from</th><th>event</th><th>to</th></tr></thead>
            <tbody>
              {model.transitions.map((t, i) => (
                <tr key={i}>
                  <td>{t.from}</td>
                  <td><span className="tag kind">{t.event}</span></td>
                  <td style={{ color: "var(--green)" }}>→ {t.to}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Durable transition log" desc="state/transitions.log — every committed transition, checksummed" right={<span className="hint mono">{log.length}</span>}>
          {log.length === 0 ? (
            <Empty>No transitions committed yet.</Empty>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {log.slice(-40).map((e) => (
                <div key={e.index} className="row" style={{ justifyContent: "space-between", padding: "6px 8px", borderBottom: "1px solid var(--border-soft)" }}>
                  <span className="mono" style={{ color: "var(--muted)", width: 34 }}>#{e.index}</span>
                  <span className="tag kind">{e.event}</span>
                  <span className="mono" style={{ flex: 1, textAlign: "right", color: "var(--green)" }}>→ {e.state}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
// #EXT-010-REQ-6 End
