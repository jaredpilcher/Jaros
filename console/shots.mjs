/**
 * Capture screenshots of the Jaros Console for the docs.
 *
 * Boots a daemon + the bridge on a throwaway data dir, submits a few example
 * jobs, then drives the system Chrome (via Playwright) to screenshot every page
 * into docs/screenshots/. Repeatable — run it any time the UI changes.
 *
 * Run:  npm run screenshots        (from console/, after `npm install`)
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..");
const PORT = 7392;
const base = `http://localhost:${PORT}`;
const OUT = path.join(HERE, "docs", "screenshots");
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(fn, timeout = 30000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) { try { if (await fn()) return true; } catch {} await sleep(400); }
  return false;
}

const data = fs.mkdtempSync(path.join(os.tmpdir(), "jaros-shots-data-"));
for (const area of ["plugins", "tools"]) {
  fs.mkdirSync(path.join(data, area), { recursive: true });
  const src = path.join(REPO, "examples", area);
  for (const f of fs.readdirSync(src)) fs.copyFileSync(path.join(src, f), path.join(data, area, f));
}

const env = { ...process.env, JAROS_DATA_DIR: data, JAROS_TICK_MS: "150", JAROS_CONSOLE_API_PORT: String(PORT) };
const daemon = spawn("python", ["-m", "jaros.cli", "--data-dir", data, "serve"], { cwd: REPO, env, stdio: "ignore" });
// Single killable node process (no shell wrapper, so .kill() actually stops it).
const bridge = spawn(process.execPath, ["--import", "tsx", "server/index.ts"], { cwd: HERE, env, stdio: "ignore" });

let browser;
try {
  if (!(await waitFor(() => fs.existsSync(path.join(data, "status.json"))))) throw new Error("daemon did not boot");
  if (!(await waitFor(async () => (await fetch(`${base}/api/health`)).ok))) throw new Error("bridge did not start");
  for (const [kind, input] of [["advance", "{}"], ["echo", '{"msg":"hello from the console"}'], ["greeter", '{"name":"Jaros"}']]) {
    await fetch(`${base}/api/jobs`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ kind, input }) });
  }
  await waitFor(async () => (await (await fetch(`${base}/api/snapshot`)).json()).counts.processed >= 3);
  console.log("[shots] daemon + bridge ready, jobs processed");

  browser = await chromium.launch({ channel: "chrome", headless: true }).catch(() => chromium.launch({ channel: "msedge", headless: true }));
  const page = await browser.newPage({ viewport: { width: 1440, height: 820 }, deviceScaleFactor: 2, colorScheme: "dark" });

  const routes = [["/", "overview"], ["/jobs", "jobs"], ["/agents", "agents"], ["/replay", "reproducibility"], ["/state", "state-machine"], ["/harness", "harness"]];
  for (const [route, name] of routes) {
    await page.goto(base + route, { waitUntil: "domcontentloaded" });
    await sleep(1400); // settle: initial fetches + first live SSE snapshot render
    await page.waitForSelector(".app", { timeout: 10000 }).catch(() => {});
    if (route === "/replay") {
      try {
        await page.waitForFunction(() => {
          const b = [...document.querySelectorAll("button")].find((x) => x.textContent.includes("Replay decision log"));
          return b && !b.disabled;
        }, { timeout: 8000 });
        await page.locator("button", { hasText: "Replay decision log" }).click({ timeout: 5000 });
        await sleep(2800);
      } catch { /* best-effort: still capture the decision log */ }
    }
    await page.screenshot({ path: path.join(OUT, `${name}.png`) });
    console.log("[shots] captured", `${name}.png`);
  }
  console.log("SHOTS_OK ->", OUT);
} catch (e) {
  console.error("[shots] error:", e.message);
} finally {
  if (browser) await browser.close();
  daemon.kill();
  bridge.kill();
  await sleep(300);
  fs.rmSync(data, { recursive: true, force: true });
}
