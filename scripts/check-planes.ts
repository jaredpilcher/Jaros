import * as fs from "fs";
import * as path from "path";

// #EXT-001-REQ-4 Start
/**
 * Plane-separation architecture check (structural enforcement of [REQ-4]).
 *
 * Scans every source file under `src/exec/**` and fails (exits non-zero) if any
 * execution-plane module imports reasoning/LLM code, namely:
 *   - anything under `src/llm/**`
 *   - the `reasoning-boundary` module
 *
 * Exits 0 when the exec plane is clean.
 */
const ROOT = path.resolve(__dirname, "..", "..");
const EXEC_DIR = path.join(ROOT, "src", "exec");

interface Violation {
  file: string;
  line: number;
  text: string;
}

/** Recursively collect all `.ts` files under a directory. */
function collectTsFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) {
    return [];
  }
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...collectTsFiles(full));
    } else if (entry.isFile() && entry.name.endsWith(".ts")) {
      out.push(full);
    }
  }
  return out;
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
  // Bare side-effect import: `import "x";` / `import 'x';` (no `from`).
  const bareImport = line.match(/^\s*import\s+["']([^"']+)["']\s*;?\s*$/);
  if (bareImport) {
    return bareImport[1];
  }
  return null;
}

/** Determine whether a module specifier reaches into the reasoning/LLM side. */
function isForbidden(spec: string): boolean {
  const normalized = spec.replace(/\\/g, "/");
  if (/(^|\/)llm(\/|$)/.test(normalized)) {
    return true;
  }
  if (/(^|\/)reasoning-boundary$/.test(normalized)) {
    return true;
  }
  return false;
}

function main(): void {
  const files = collectTsFiles(EXEC_DIR);
  const violations: Violation[] = [];

  for (const file of files) {
    const lines = fs.readFileSync(file, "utf8").split(/\r?\n/);
    lines.forEach((text, i) => {
      const spec = importSpecifier(text);
      if (spec && isForbidden(spec)) {
        violations.push({
          file: path.relative(ROOT, file).replace(/\\/g, "/"),
          line: i + 1,
          text: text.trim(),
        });
      }
    });
  }

  if (violations.length > 0) {
    console.error(
      "Plane separation violation: execution-plane modules must not import LLM/reasoning code."
    );
    for (const v of violations) {
      console.error(`  ${v.file}:${v.line}  ${v.text}`);
    }
    process.exit(1);
  }

  console.log(
    `check-planes: OK — scanned ${files.length} exec file(s); no reasoning/LLM imports.`
  );
  process.exit(0);
}

main();
// #EXT-001-REQ-4 End
