import { useEffect, useState } from "react";

import { api, type HarnessModel, type Job } from "../api";
import { Card, Empty } from "../components/ui";

export function Harness() {
  const [model, setModel] = useState<HarnessModel | null>(null);
  const [failed, setFailed] = useState<Job[]>([]);

  useEffect(() => {
    api.harness().then(setModel);
    const refresh = () => api.jobs().then((j) => setFailed(j.filter((x) => x.area === "failed")));
    refresh();
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, []);

  if (model?.error) return <Card title="Harness">Could not introspect: {model.error}</Card>;
  if (!model) return <Card>Loading the harness model…</Card>;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <Card title="Capability-safety" desc="structural least-privilege — not an adversarial sandbox; host isolation is the security boundary">
        <div className="hint">
          Agents hold only the scoped handles the harness grants. A bug or bad decision cannot reach what it was never given, and every
          mediated action is default-deny. Isolation against hostile code is delegated to the host (process / container / VPC).
        </div>
      </Card>

      <div className="grid cols-2" style={{ alignItems: "start" }}>
        <Card title="Mediation rules" desc="action type → required capability (fail-closed for anything unlisted)">
          <table>
            <thead><tr><th>action</th><th>requires</th></tr></thead>
            <tbody>
              {Object.entries(model.rules).map(([action, cap]) => (
                <tr key={action}>
                  <td><span className="tag kind">{action}</span></td>
                  <td style={{ color: "var(--green)" }}>{cap}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Roles" desc="a role is a named bundle of capability handles">
          <table>
            <thead><tr><th>role</th><th>capabilities</th></tr></thead>
            <tbody>
              {Object.entries(model.roles).map(([role, caps]) => (
                <tr key={role}>
                  <td>{role}</td>
                  <td>
                    <div className="row" style={{ flexWrap: "wrap", gap: 5 }}>
                      {caps.length ? caps.map((c) => <span key={c} className="tag green">{c}</span>) : <span className="hint">none</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Card title="Refusal audit" desc="contained failures the daemon recorded — the auditable record" right={<span className="hint mono">{failed.length}</span>}>
        {failed.length === 0 ? (
          <Empty>No refused or failed jobs.</Empty>
        ) : (
          <table>
            <thead><tr><th>job</th><th>kind</th><th>reason</th></tr></thead>
            <tbody>
              {failed.map((j) => (
                <tr key={j.id}>
                  <td style={{ color: "var(--muted)" }}>{j.id.slice(0, 12)}</td>
                  <td><span className="tag kind">{j.kind ?? "?"}</span></td>
                  <td style={{ color: "var(--red)" }}>{j.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
