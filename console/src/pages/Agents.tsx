import { useEffect, useState } from "react";

import { api, type Agents as AgentsModel } from "../api";
import { Card, Empty } from "../components/ui";

const PLUGIN_TEMPLATE = `import uuid
from jaros.core import create_decision

KIND = "my_agent"

class MyBoundary:
    def __init__(self, llm):
        self._llm = llm

    def decide(self, context) -> list:
        return [create_decision(
            id=f"my-{uuid.uuid4().hex}",
            source=KIND,
            kind="advance",
            payload={"events": ["start", "complete"], "note": str(context)},
        )]

def build(llm):
    return MyBoundary(llm)
`;

const TOOL_TEMPLATE = `from jaros.core.decision_gate import ValidationResult

class MyTool:
    NAME = "demo.my_action"

    def validate(self, decision) -> ValidationResult:
        return ValidationResult.accept(decision)

    def execute(self, decision, **collaborators) -> dict:
        return {"ok": True, "payload": decision.payload}
`;

// #EXT-010-REQ-4 Start
export function Agents() {
  const [agents, setAgents] = useState<AgentsModel>({ plugins: [], tools: [] });
  const [tab, setTab] = useState<"plugins" | "tools">("plugins");
  const [name, setName] = useState("my_agent.py");
  const [source, setSource] = useState(PLUGIN_TEMPLATE);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function refresh() {
    setAgents(await api.agents());
  }
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, []);

  function pick(t: "plugins" | "tools") {
    setTab(t);
    setName(t === "plugins" ? "my_agent.py" : "my_tool.py");
    setSource(t === "plugins" ? PLUGIN_TEMPLATE : TOOL_TEMPLATE);
    setMsg(null);
  }

  async function install() {
    setMsg(null);
    const r = tab === "plugins" ? await api.installPlugin(name, source) : await api.installTool(name, source);
    if (r.error) setMsg({ ok: false, text: r.error });
    else {
      setMsg({ ok: true, text: `installed ${r.path} — loaded on the next daemon tick` });
      refresh();
    }
  }

  return (
    <div className="grid cols-2" style={{ alignItems: "start" }}>
      <div className="grid" style={{ gap: 16 }}>
        <Card title="Plugin agents" desc="loaded from plugins/ at runtime — no restart" right={<span className="hint mono">{agents.plugins.length}</span>}>
          {agents.plugins.length === 0 ? <Empty>No plugin agents installed.</Empty> : (
            <table><tbody>{agents.plugins.map((p) => <tr key={p}><td><span className="tag green">◆</span></td><td>{p}</td></tr>)}</tbody></table>
          )}
        </Card>
        <Card title="Custom tools" desc="namespaced actions loaded from tools/" right={<span className="hint mono">{agents.tools.length}</span>}>
          {agents.tools.length === 0 ? <Empty>No custom tools installed.</Empty> : (
            <table><tbody>{agents.tools.map((p) => <tr key={p}><td><span className="tag kind">⚙</span></td><td>{p}</td></tr>)}</tbody></table>
          )}
        </Card>
      </div>

      <Card
        title="Install a module"
        desc="dropped atomically into the shared volume"
        right={
          <div className="row">
            <button className={tab === "plugins" ? "primary" : ""} onClick={() => pick("plugins")}>Plugin</button>
            <button className={tab === "tools" ? "primary" : ""} onClick={() => pick("tools")}>Tool</button>
          </div>
        }
      >
        <label className="field">File name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} style={{ marginBottom: 12 }} />
        <label className="field">Source (Python)</label>
        <textarea rows={16} value={source} onChange={(e) => setSource(e.target.value)} style={{ marginBottom: 12 }} />
        <div className="row">
          <button className="primary" onClick={install}>Install {tab === "plugins" ? "plugin" : "tool"}</button>
          {msg && <span style={{ color: msg.ok ? "var(--green)" : "var(--red)", fontSize: 12 }}>{msg.text}</span>}
        </div>
      </Card>
    </div>
  );
}
// #EXT-010-REQ-4 End
