/**
 * Jaros Console bridge — a host-side companion server.
 *
 * It serves the React SPA and a small REST + SSE API over the shared data
 * directory. It opens a localhost port (it is an admin tool, like the CLI), but
 * it is NOT part of the Jaros node: the node remains serverless and file-system
 * only. Everything here is reads/writes of the data dir, plus shelling out to
 * `jaros` (via jaros_introspect.py) for the real state model, harness rules, and
 * deterministic replay.
 */

import { execFile } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  DATA_DIR,
  dataDirExists,
  deleteSchedule,
  getDecisions,
  getJobs,
  getOutbox,
  getAgents,
  getSchedules,
  getStatus,
  getTools,
  getTransitions,
  installModule,
  submitJob,
  writeSchedule,
} from "./jarosData";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DIST = path.join(ROOT, "dist");
const PY = process.env.JAROS_PYTHON ?? "python";
const INTROSPECT = path.join(__dirname, "jaros_introspect.py");
const PORT = Number(process.env.JAROS_CONSOLE_API_PORT ?? 7373);

// ---- helpers ---------------------------------------------------------------

function sendJson(res: http.ServerResponse, code: number, body: unknown): void {
  const data = JSON.stringify(body);
  res.writeHead(code, { "content-type": "application/json", "cache-control": "no-store" });
  res.end(data);
}

function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => resolve(raw));
  });
}

function runPython(args: string[]): Promise<unknown> {
  return new Promise((resolve) => {
    execFile(PY, [INTROSPECT, ...args], { maxBuffer: 8 * 1024 * 1024 }, (err, stdout) => {
      if (err && !stdout) {
        resolve({ error: `python failed: ${err.message}`, ok: false });
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch {
        resolve({ error: "could not parse jaros introspection output", ok: false });
      }
    });
  });
}

// Cache the static model/harness dumps (they don't change at runtime).
let modelCache: unknown | null = null;
let harnessCache: unknown | null = null;

// ---- SSE live updates ------------------------------------------------------

// #EXT-010-REQ-2 Start
const sseClients = new Set<http.ServerResponse>();

function snapshot() {
  const jobs = getJobs();
  return {
    ts: Date.now(),
    connected: dataDirExists(),
    status: getStatus(),
    counts: {
      inbox: jobs.filter((j) => j.area === "inbox").length,
      processed: jobs.filter((j) => j.area === "processed").length,
      failed: jobs.filter((j) => j.area === "failed").length,
      outbox: getOutbox().length,
      decisions: getDecisions().length,
      agents: getAgents().length,
      tools: getTools().length,
    },
  };
}

setInterval(() => {
  if (sseClients.size === 0) return;
  const payload = `data: ${JSON.stringify(snapshot())}\n\n`;
  for (const client of sseClients) client.write(payload);
}, 1000);
// #EXT-010-REQ-2 End

// ---- static SPA serving ----------------------------------------------------

const MIME: Record<string, string> = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

function serveStatic(req: http.IncomingMessage, res: http.ServerResponse, pathname: string): void {
  if (!fs.existsSync(DIST)) {
    res.writeHead(200, { "content-type": "text/html" });
    res.end(
      "<h1>Jaros Console</h1><p>Run <code>npm run dev</code> for the live UI, " +
        "or <code>npm run build</code> then <code>npm start</code> for production.</p>",
    );
    return;
  }
  let filePath = path.join(DIST, pathname === "/" ? "index.html" : pathname);
  if (!filePath.startsWith(DIST) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(DIST, "index.html"); // SPA fallback
  }
  const ext = path.extname(filePath);
  res.writeHead(200, { "content-type": MIME[ext] ?? "application/octet-stream" });
  fs.createReadStream(filePath).pipe(res);
}

// ---- request router --------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);
  const { pathname } = url;
  const method = req.method ?? "GET";

  try {
    if (pathname === "/api/health") {
      return sendJson(res, 200, { dataDir: DATA_DIR, connected: dataDirExists() });
    }
    if (pathname === "/api/snapshot") return sendJson(res, 200, snapshot());
    if (pathname === "/api/status") return sendJson(res, 200, getStatus() ?? {});
    if (pathname === "/api/jobs" && method === "GET") return sendJson(res, 200, getJobs());
    if (pathname === "/api/jobs" && method === "POST") {
      const body = JSON.parse((await readBody(req)) || "{}");
      if (!body.agent) return sendJson(res, 400, { error: "agent is required" });
      let input: unknown = body.input ?? {};
      if (typeof input === "string") {
        try {
          input = input.trim() ? JSON.parse(input) : {};
        } catch {
          return sendJson(res, 400, { error: "input must be valid JSON" });
        }
      }
      return sendJson(res, 200, submitJob(String(body.agent), input));
    }
    if (pathname === "/api/outbox") return sendJson(res, 200, getOutbox());
    if (pathname === "/api/decisions") return sendJson(res, 200, getDecisions());
    if (pathname === "/api/transitions") return sendJson(res, 200, getTransitions());
    if (pathname === "/api/agents" && method === "GET") {
      return sendJson(res, 200, { agents: getAgents(), tools: getTools() });
    }
    if ((pathname === "/api/agents" || pathname === "/api/tools") && method === "POST") {
      const area = pathname.endsWith("/tools") ? "tools" : "agents";
      const body = JSON.parse((await readBody(req)) || "{}");
      if (!body.name || typeof body.source !== "string") {
        return sendJson(res, 400, { error: "name and source are required" });
      }
      try {
        return sendJson(res, 200, installModule(area, String(body.name), body.source));
      } catch (e) {
        return sendJson(res, 400, { error: (e as Error).message });
      }
    }
    if (pathname === "/api/schedules" && method === "GET") {
      return sendJson(res, 200, getSchedules());
    }
    if (pathname === "/api/schedules" && method === "POST") {
      const body = JSON.parse((await readBody(req)) || "{}");
      if (!body.name || !body.schedule) {
        return sendJson(res, 400, { error: "name and schedule are required" });
      }
      try {
        return sendJson(res, 200, writeSchedule(String(body.name), body.schedule));
      } catch (e) {
        return sendJson(res, 400, { error: (e as Error).message });
      }
    }
    if (pathname === "/api/schedules" && method === "DELETE") {
      const name = url.searchParams.get("name");
      if (!name) return sendJson(res, 400, { error: "name query param required" });
      try {
        return sendJson(res, 200, deleteSchedule(name));
      } catch (e) {
        return sendJson(res, 400, { error: (e as Error).message });
      }
    }
    if (pathname === "/api/model") {
      if (!modelCache) modelCache = await runPython(["model"]);
      return sendJson(res, 200, modelCache);
    }
    if (pathname === "/api/harness") {
      if (!harnessCache) harnessCache = await runPython(["harness"]);
      return sendJson(res, 200, harnessCache);
    }
    if (pathname === "/api/replay" && method === "POST") {
      return sendJson(res, 200, await runPython(["replay", DATA_DIR]));
    }
    if (pathname === "/api/evals" && method === "POST") {
      return sendJson(res, 200, await runPython(["evals", DATA_DIR]));
    }
    if (pathname === "/api/events") {
      res.writeHead(200, {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
        connection: "keep-alive",
      });
      res.write(`data: ${JSON.stringify(snapshot())}\n\n`);
      sseClients.add(res);
      req.on("close", () => sseClients.delete(res));
      return;
    }
    if (pathname.startsWith("/api/")) return sendJson(res, 404, { error: "not found" });

    return serveStatic(req, res, pathname);
  } catch (e) {
    return sendJson(res, 500, { error: (e as Error).message });
  }
});

server.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`Jaros Console bridge on http://localhost:${PORT}  (data dir: ${DATA_DIR})`);
});
