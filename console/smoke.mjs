/**
 * End-to-end smoke for the Jaros Console: boot a daemon + the bridge on a
 * throwaway data dir, then drive EVERY interactive path through the console API —
 * submit jobs, install an agent and a custom tool, create/list/delete a
 * schedule, run the eval suite, introspect the model + harness, and replay.
 *
 * Run:  node console/smoke.mjs   (from repo root, after `npm install` in console/)
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..");
const API = 7399;
const base = `http://localhost:${API}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const j = (path, opts) => fetch(`${base}${path}`, opts).then((r) => r.json());
const post = (path, body) => j(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

async function waitFor(fn, timeout = 30000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) { try { if (await fn()) return true; } catch { /* retry */ } await sleep(400); }
  return false;
}

const data = fs.mkdtempSync(path.join(os.tmpdir(), "jaros-console-"));
for (const area of ["agents", "tools", "evals"]) fs.mkdirSync(path.join(data, area), { recursive: true });
// Stage the example + read-only library so jobs, tools, and the eval suite work.
for (const [area, root] of [["agents", "examples/agents"], ["tools", "examples/tools"], ["agents", "examples/readonly/agents"], ["tools", "examples/readonly/tools"], ["evals", "examples/readonly/evals"]]) {
  const src = path.join(REPO, root);
  for (const f of fs.readdirSync(src)) if (f.endsWith(".py") || f.endsWith(".json")) fs.copyFileSync(path.join(src, f), path.join(data, area, f));
}
console.log("[smoke] data dir:", data);

const env = { ...process.env, JAROS_DATA_DIR: data, JAROS_TICK_MS: "150", JAROS_CONSOLE_API_PORT: String(API) };
const daemon = spawn("python", ["-m", "jaros.cli", "--data-dir", data, "serve"], { cwd: REPO, env, stdio: "ignore" });
// Single killable node process (no shell wrapper), so kill() actually stops it.
const bridge = spawn(process.execPath, ["--import", "tsx", "server/index.ts"], { cwd: HERE, env, stdio: "ignore" });

let code = 1;
try {
  if (!(await waitFor(() => fs.existsSync(path.join(data, "status.json"))))) throw new Error("daemon did not boot");
  if (!(await waitFor(async () => (await fetch(`${base}/api/health`)).ok))) throw new Error("bridge did not start");
  console.log("[smoke] daemon + bridge up");

  // 1. Submit jobs (Jobs page).
  for (const [kind, input] of [["advance", "{}"], ["echo", '{"msg":"hi"}'], ["greeter", '{"name":"Jaros"}']]) {
    if ((await post("/api/jobs", { kind, input })).error) throw new Error(`submit ${kind} failed`);
  }
  await waitFor(async () => (await j("/api/snapshot")).counts.processed >= 3);

  // 2. Install an agent + a custom tool (Agents & Tools page).
  const installAgent = await post("/api/agents", { name: "smoke_agent.py", source: 'import uuid\nfrom jaros.core import create_decision\nKIND="smoke"\nclass B:\n  def __init__(self, llm): pass\n  def decide(self, c): return [create_decision(id=f"s-{uuid.uuid4().hex}", source="smoke", kind="advance", payload={"events":["start","complete"]})]\ndef build(llm): return B()\n' });
  const installTool = await post("/api/tools", { name: "smoke_tool.py", source: 'from jaros.core.decision_gate import ValidationResult\nclass T:\n  NAME="smoke.noop"\n  def validate(self, d): return ValidationResult.accept(d)\n  def execute(self, d, **k): return {"ok": True}\n' });
  const agents = await j("/api/agents");

  // 3. Create / list / delete a schedule (Schedules page).
  const createSched = await post("/api/schedules", { name: "smoke-sched", schedule: { id: "smoke-sched", kind: "advance", input: {}, every_seconds: 3600, enabled: true } });
  const schedAfterCreate = await j("/api/schedules");
  await fetch(`${base}/api/schedules?name=smoke-sched`, { method: "DELETE" });
  const schedAfterDelete = await j("/api/schedules");

  // 4. Run the eval suite (Evaluations page).
  const evals = await post("/api/evals", {});

  // 5. Reproducibility + introspection.
  const decisions = await j("/api/decisions");
  const model = await j("/api/model");
  const harness = await j("/api/harness");
  const replay = await post("/api/replay", {});
  const snap = await j("/api/snapshot");

  const checks = {
    "submit jobs -> processed >= 3": snap.counts.processed >= 3 && snap.counts.failed === 0,
    "install agent (POST /api/agents)": !!installAgent.path && agents.agents.includes("smoke_agent.py"),
    "install tool (POST /api/tools)": !!installTool.path && agents.tools.includes("smoke_tool.py"),
    "create schedule (POST /api/schedules)": !!createSched.name && schedAfterCreate.some((s) => s.id === "smoke-sched"),
    "delete schedule (DELETE)": !schedAfterDelete.some((s) => s.id === "smoke-sched"),
    "run evals (POST /api/evals)": evals.ok === true && evals.total >= 4,
    "decisions logged": decisions.length >= 3,
    "state model introspected": Array.isArray(model.states) && model.states.includes("DONE"),
    "harness rules introspected": harness.rules && Object.keys(harness.rules).length > 0,
    "replay reproducible (deterministic + byte-identical)": replay.ok === true && replay.deterministic === true && replay.modelCalls === 0,
  };
  let allOk = true;
  for (const [name, ok] of Object.entries(checks)) { console.log(`        [${ok ? "PASS" : "FAIL"}] ${name}`); if (!ok) allOk = false; }
  code = allOk ? 0 : 1;
  console.log(allOk ? "PASS: the console drives every interactive path against a live Jaros." : "FAIL: some console paths failed.");
} catch (e) {
  console.error("[smoke] error:", e.message);
} finally {
  daemon.kill();
  bridge.kill();
  await sleep(300);
  fs.rmSync(data, { recursive: true, force: true });
  process.exit(code);
}
