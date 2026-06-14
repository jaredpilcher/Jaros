import { useEffect, useState } from "react";

import { api, type ScheduleRow } from "../api";
import { Card, Empty, Pill } from "../components/ui";

const TRIGGERS = ["every_seconds", "cron", "at"] as const;
type TriggerKind = (typeof TRIGGERS)[number];

// #EXT-010-REQ-7 Start
export function Schedules() {
  const [rows, setRows] = useState<ScheduleRow[]>([]);
  const [name, setName] = useState("my-schedule");
  const [kind, setKind] = useState("system-health");
  const [input, setInput] = useState("{}");
  const [triggerKind, setTriggerKind] = useState<TriggerKind>("every_seconds");
  const [triggerVal, setTriggerVal] = useState("60");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function refresh() {
    setRows(await api.schedules());
  }
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, []);

  async function create(enabled = true) {
    setMsg(null);
    let parsedInput: unknown = {};
    try {
      parsedInput = input.trim() ? JSON.parse(input) : {};
    } catch {
      setMsg({ ok: false, text: "input must be valid JSON" });
      return;
    }
    const schedule: Record<string, unknown> = { id: name, kind, input: parsedInput, enabled };
    schedule[triggerKind] = triggerKind === "every_seconds" ? Number(triggerVal) : triggerVal;
    const r = await api.createSchedule(name, schedule);
    if (r.error) setMsg({ ok: false, text: r.error });
    else {
      setMsg({ ok: true, text: `saved schedules/${r.name}` });
      refresh();
    }
  }

  async function toggle(row: ScheduleRow) {
    const schedule: Record<string, unknown> = {
      id: row.id ?? row.name,
      kind: row.kind,
      input: row.input ?? {},
      enabled: !row.enabled,
    };
    if (row.every_seconds != null) schedule.every_seconds = row.every_seconds;
    if (row.cron) schedule.cron = row.cron;
    if (row.at) schedule.at = row.at;
    await api.createSchedule(row.name, schedule);
    refresh();
  }

  async function remove(row: ScheduleRow) {
    await api.deleteSchedule(row.name);
    refresh();
  }

  return (
    <div className="grid cols-2" style={{ alignItems: "start" }}>
      <Card title="Schedules" desc="native cron / interval / one-shot — no external cron" right={<span className="hint mono">{rows.length}</span>}>
        {rows.length === 0 ? (
          <Empty>No schedules. Create one on the right.</Empty>
        ) : (
          <table>
            <thead>
              <tr><th>id</th><th>kind</th><th>trigger</th><th>next / last</th><th></th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name}>
                  <td>{r.id ?? r.name}</td>
                  <td><span className="tag kind">{r.kind ?? "?"}</span></td>
                  <td>{r.trigger ?? (r.every_seconds != null ? `every ${r.every_seconds}s` : r.cron ? `cron ${r.cron}` : r.at ? `at ${r.at}` : "?")}</td>
                  <td style={{ color: "var(--muted)" }}>
                    {r.nextRun ? `→ ${r.nextRun}` : "—"}<br />
                    {r.lastRun ? `last ${r.lastRun}` : "never"}
                  </td>
                  <td>
                    <div className="row" style={{ gap: 6 }}>
                      <button onClick={() => toggle(r)}>{r.enabled ? "Pause" : "Enable"}</button>
                      <button onClick={() => remove(r)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ marginTop: 10 }} className="hint">
          Enabled schedules show a <Pill tone="ok">live</Pill> next-run once a daemon is evaluating them.
        </div>
      </Card>

      <Card title="New schedule" desc="written to schedules/ — the daemon dispatches it natively">
        <label className="field">Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} style={{ marginBottom: 12 }} />
        <label className="field">Agent kind</label>
        <input value={kind} onChange={(e) => setKind(e.target.value)} style={{ marginBottom: 12 }} />
        <label className="field">Input (JSON)</label>
        <textarea rows={3} value={input} onChange={(e) => setInput(e.target.value)} style={{ marginBottom: 12 }} />
        <label className="field">Trigger</label>
        <div className="row" style={{ marginBottom: 12 }}>
          <select value={triggerKind} onChange={(e) => setTriggerKind(e.target.value as TriggerKind)} style={{ maxWidth: 170 }}>
            <option value="every_seconds">every_seconds</option>
            <option value="cron">cron</option>
            <option value="at">at (ISO)</option>
          </select>
          <input
            value={triggerVal}
            onChange={(e) => setTriggerVal(e.target.value)}
            placeholder={triggerKind === "cron" ? "*/15 * * * *" : triggerKind === "at" ? "2026-06-13T18:00:00" : "60"}
          />
        </div>
        <div className="row">
          <button className="primary" onClick={() => create(true)}>Create schedule</button>
          {msg && <span style={{ color: msg.ok ? "var(--green)" : "var(--red)", fontSize: 12 }}>{msg.text}</span>}
        </div>
      </Card>
    </div>
  );
}
// #EXT-010-REQ-7 End
