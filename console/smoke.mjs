/**
 * End-to-end smoke for the Jaros Console: boot a daemon on a throwaway data dir,
 * start the bridge, then drive everything through the console API — submit jobs,
 * read the decision log, introspect the state model + harness, and run a replay.
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

async function waitFor(fn, timeout = 30000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    try { if (await fn()) return true; } catch { /* retry */ }
    await sleep(400);
  }
  return false;
}

const data = fs.mkdtempSync(path.join(os.tmpdir(), "jaros-console-"));
fs.mkdirSync(path.join(data, "plugins"), { recursive: true });
fs.mkdirSync(path.join(data, "tools"), { recursive: true });
for (const f of fs.readdirSync(path.join(REPO, "examples", "plugins"))) fs.copyFileSync(path.join(REPO, "examples", "plugins", f), path.join(data, "plugins", f));
for (const f of fs.readdirSync(path.join(REPO, "examples", "tools"))) fs.copyFileSync(path.join(REPO, "examples", "tools", f), path.join(data, "tools", f));
console.log("[smoke] data dir:", data);

const env = { ...process.env, JAROS_DATA_DIR: data, JAROS_TICK_MS: "150", JAROS_CONSOLE_API_PORT: String(API) };
const daemon = spawn("python", ["-m", "jaros.cli", "--data-dir", data, "serve"], { cwd: REPO, env, stdio: "ignore" });
const bridge = spawn("npx", ["tsx", "server/index.ts"], { cwd: HERE, env, stdio: "ignore", shell: process.platform === "win32" });

let code = 1;
try {
  if (!(await waitFor(() => fs.existsSync(path.join(data, "status.json"))))) throw new Error("daemon did not boot");
  if (!(await waitFor(async () => (await fetch(`${base}/api/health`)).ok))) throw new Error("bridge did not start");
  console.log("[smoke] daemon + bridge up");

  for (const [kind, input] of [["advance", "{}"], ["echo", '{"msg":"hi"}'], ["greeter", '{"name":"Jaros"}']]) {
    const r = await (await fetch(`${base}/api/jobs`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ kind, input }) })).json();
    if (r.error) throw new Error(`submit ${kind}: ${r.error}`);
  }
  console.log("[smoke] submitted 3 jobs via the console API");

  if (!(await waitFor(async () => (await (await fetch(`${base}/api/snapshot`)).json()).counts.processed >= 3))) throw new Error("jobs not processed");

  const snap = await (await fetch(`${base}/api/snapshot`)).json();
  const decisions = await (await fetch(`${base}/api/decisions`)).json();
  const model = await (await fetch(`${base}/api/model`)).json();
  const harness = await (await fetch(`${base}/api/harness`)).json();
  const replay = await (await fetch(`${base}/api/replay`, { method: "POST" })).json();

  const checks = {
    "processed >= 3": snap.counts.processed >= 3,
    "no failures": snap.counts.failed === 0,
    "decisions logged >= 3": decisions.length >= 3,
    "state model introspected": Array.isArray(model.states) && model.states.includes("DONE"),
    "harness rules introspected": harness.rules && Object.keys(harness.rules).length > 0,
    "replay ok": replay.ok === true,
    "replay reconstructs DONE": replay.finalState === "DONE",
    "replay no model call": replay.modelCalls === 0,
  };
  let allOk = true;
  for (const [name, ok] of Object.entries(checks)) { console.log(`        [${ok ? "PASS" : "FAIL"}] ${name}`); if (!ok) allOk = false; }
  console.log(`[smoke] replay -> ${JSON.stringify(replay)}`);
  code = allOk ? 0 : 1;
  console.log(allOk ? "PASS: console stack drives a live Jaros end-to-end." : "FAIL: some checks failed.");
} catch (e) {
  console.error("[smoke] error:", e.message);
} finally {
  daemon.kill();
  bridge.kill();
  await sleep(300);
  fs.rmSync(data, { recursive: true, force: true });
  process.exit(code);
}
