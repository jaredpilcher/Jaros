import * as fs from "fs";
import * as path from "path";

// #EXT-006-REQ-3 Start
// #EXT-006-REQ-5 Start
/**
 * Communication-fabric architecture check (structural enforcement of [REQ-3]
 * and [REQ-5]).
 *
 * Inter-agent communication may flow ONLY through the rigid queue and the
 * shared file system. This checker scans agent/runtime code and fails (exits
 * non-zero) on any structural path that would let one agent reach another
 * directly, namely:
 *
 *   - a cross-agent module import that is NOT `src/comms/queue` or
 *     `src/comms/fs` (the only sanctioned inter-agent dependencies);
 *   - an RPC / network call (http/https/net/dgram/grpc/fetch/WebSocket, etc.),
 *     which would be an out-of-band channel between agents.
 *
 * Scanned scope:
 *   - everything under `src/runtime/**`
 *   - any module whose path marks it as agent code (a path segment of `agent`
 *     or `agents`, or a filename containing `agent`)
 *
 * If `src/runtime/**` and agent code do not exist yet, there is nothing to
 * violate and the check passes (exit 0).
 */
const ROOT = path.resolve(__dirname, "..", "..");
const SRC = path.join(ROOT, "src");
const RUNTIME_DIR = path.join(SRC, "runtime");

/** Module specifiers that ARE the sanctioned inter-agent channels. */
const ALLOWED_COMMS = ["comms/queue", "comms/fs"];

/** Node/network modules whose use signals an out-of-band agent channel. */
const NETWORK_MODULES = new Set([
  "http",
  "https",
  "http2",
  "net",
  "tls",
  "dgram",
  "dns",
  "node:http",
  "node:https",
  "node:http2",
  "node:net",
  "node:tls",
  "node:dgram",
  "node:dns",
  "grpc",
  "@grpc/grpc-js",
  "ws",
  "socket.io",
  "socket.io-client",
  "axios",
  "node-fetch",
]);

/** Global network/RPC call expressions that need no import. */
const NETWORK_CALLS = [/\bfetch\s*\(/, /\bnew\s+WebSocket\b/, /\bXMLHttpRequest\b/];

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

/** Extract the module specifier from an import / require statement, if any. */
function importSpecifier(line: string): string | null {
  const fromMatch = line.match(/\bfrom\s+["']([^"']+)["']/);
  if (fromMatch) {
    return fromMatch[1];
  }
  const importCall = line.match(/\bimport\s*\(\s*["']([^"']+)["']\s*\)/);
  if (importCall) {
    return importCall[1];
  }
  const requireCall = line.match(/\brequire\s*\(\s*["']([^"']+)["']\s*\)/);
  if (requireCall) {
    return requireCall[1];
  }
  const bareImport = line.match(/^\s*import\s+["']([^"']+)["']\s*;?\s*$/);
  if (bareImport) {
    return bareImport[1];
  }
  return null;
}

/** Normalize a relative module specifier to a comms-relative form for matching. */
function normalizeSpec(spec: string): string {
  return spec.replace(/\\/g, "/").replace(/\.(ts|js)$/, "");
}

/**
 * Decide whether an import from an agent module is a forbidden cross-agent
 * dependency. Local/relative imports are fine UNLESS they reach into another
 * agent's code; the comms channels are always allowed.
 */
function importViolationReason(spec: string): string | null {
  const norm = normalizeSpec(spec);

  // The two sanctioned inter-agent channels are always allowed.
  if (ALLOWED_COMMS.some((a) => norm === a || norm.endsWith("/" + a))) {
    return null;
  }

  // Network/RPC modules are never an inter-agent channel.
  if (NETWORK_MODULES.has(spec) || NETWORK_MODULES.has(norm)) {
    return `imports network/RPC module "${spec}" (only queues + shared FS are permitted)`;
  }

  // A relative import that reaches into agent code of a *different* agent is a
  // direct agent-to-agent reference. We approximate "agent code" by the path
  // containing an agent/agents segment or an `agent` filename.
  if (spec.startsWith(".")) {
    const segs = norm.split("/");
    const reachesAgent =
      segs.some((s) => s === "agent" || s === "agents") ||
      /agent/i.test(segs[segs.length - 1]);
    if (reachesAgent) {
      return `directly references another agent's module "${spec}" (use a queue or the shared FS)`;
    }
  }

  return null;
}

function main(): void {
  // Scan runtime tree plus any agent code anywhere under src.
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
      const spec = importSpecifier(text);
      if (spec) {
        const reason = importViolationReason(spec);
        if (reason) {
          violations.push({ file: relFile, line: i + 1, text: text.trim(), reason });
        }
      }
      for (const re of NETWORK_CALLS) {
        if (re.test(text)) {
          violations.push({
            file: relFile,
            line: i + 1,
            text: text.trim(),
            reason: "makes a direct network/RPC call (only queues + shared FS are permitted)",
          });
          break;
        }
      }
    });
  }

  if (violations.length > 0) {
    console.error(
      "Communication-fabric violation: agents may only communicate via the rigid queue and shared file system."
    );
    for (const v of violations) {
      console.error(`  ${v.file}:${v.line}  ${v.reason}\n    ${v.text}`);
    }
    process.exit(1);
  }

  console.log(
    `check-comms: OK — scanned ${files.length} runtime/agent file(s); no direct agent-to-agent paths.`
  );
  process.exit(0);
}

main();
// #EXT-006-REQ-5 End
// #EXT-006-REQ-3 End
