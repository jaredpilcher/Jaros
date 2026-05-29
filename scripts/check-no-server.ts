import * as fs from "fs";
import * as path from "path";

// #EXT-003-REQ-3 Start
/**
 * No-server architecture check (structural enforcement of [REQ-3]).
 *
 * Agents are lightweight in-process threads, never per-agent services. This
 * checker scans `src/runtime/**` and any agent code and FAILS (exits non-zero)
 * if it finds a per-agent server/listener footprint, namely:
 *
 *   - `http.createServer` / `https.createServer` / `http2.create*Server`
 *   - `net.createServer` / `tls.createServer` / `dgram.createSocket`
 *   - a `.listen(` call (binding a socket/port)
 *   - `new WebSocketServer` / `new Server(` style socket bindings
 *
 * Scanned scope:
 *   - everything under `src/runtime/**`
 *   - any module whose path marks it as agent code (an `agent`/`agents` path
 *     segment, or a filename containing `agent`)
 *
 * Tests (`*.test.ts`) are excluded. If there is nothing to scan, the check
 * passes (exit 0).
 */
const ROOT = path.resolve(__dirname, "..", "..");
const SRC = path.join(ROOT, "src");
const RUNTIME_DIR = path.join(SRC, "runtime");

/** Source patterns that indicate a per-agent server/listener footprint. */
const SERVER_PATTERNS: ReadonlyArray<{ re: RegExp; reason: string }> = [
  { re: /\b(?:https?|http2)\.create(?:Secure)?Server\s*\(/, reason: "creates an HTTP server" },
  { re: /\bnet\.createServer\s*\(/, reason: "creates a TCP server" },
  { re: /\btls\.createServer\s*\(/, reason: "creates a TLS server" },
  { re: /\bdgram\.createSocket\s*\(/, reason: "creates a UDP socket" },
  { re: /\.listen\s*\(/, reason: "binds a listening socket/port via .listen(" },
  { re: /\bnew\s+WebSocketServer\b/, reason: "starts a WebSocket server" },
  { re: /\bnew\s+(?:WebSocket\.)?Server\s*\(/, reason: "starts a socket server" },
];

interface Violation {
  file: string;
  line: number;
  text: string;
  reason: string;
}

/** Recursively collect all `.ts` files under a directory (excluding tests). */
function collectTsFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) {
    return [];
  }
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...collectTsFiles(full));
    } else if (
      entry.isFile() &&
      entry.name.endsWith(".ts") &&
      !entry.name.endsWith(".test.ts")
    ) {
      out.push(full);
    }
  }
  return out;
}

/** True if a file (by its path) counts as agent code we must police. */
function isAgentCode(file: string): boolean {
  const rel = path.relative(SRC, file).replace(/\\/g, "/");
  const segments = rel.split("/");
  const dirSegments = segments.slice(0, -1);
  const base = segments[segments.length - 1];
  if (dirSegments.some((s) => s === "agent" || s === "agents")) {
    return true;
  }
  return /agent/i.test(base);
}

function main(): void {
  const runtimeFiles = collectTsFiles(RUNTIME_DIR);
  const allSrcFiles = collectTsFiles(SRC);
  const agentFiles = allSrcFiles.filter(isAgentCode);

  const fileSet = new Set<string>([...runtimeFiles, ...agentFiles]);
  const files = [...fileSet];

  const violations: Violation[] = [];

  for (const file of files) {
    const lines = fs.readFileSync(file, "utf8").split(/\r?\n/);
    const relFile = path.relative(ROOT, file).replace(/\\/g, "/");

    lines.forEach((text, i) => {
      for (const { re, reason } of SERVER_PATTERNS) {
        if (re.test(text)) {
          violations.push({ file: relFile, line: i + 1, text: text.trim(), reason });
          break;
        }
      }
    });
  }

  if (violations.length > 0) {
    console.error(
      "No-server violation: agents are lightweight threads and must not start a server/listener."
    );
    for (const v of violations) {
      console.error(`  ${v.file}:${v.line}  ${v.reason}\n    ${v.text}`);
    }
    process.exit(1);
  }

  console.log(
    `check-no-server: OK — scanned ${files.length} runtime/agent file(s); no per-agent server/listener footprint.`
  );
  process.exit(0);
}

main();
// #EXT-003-REQ-3 End
