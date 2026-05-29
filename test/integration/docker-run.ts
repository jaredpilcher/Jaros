/**
 * Docker integration test runner.
 *
 * Builds the production image, runs the end-to-end smoke container, and asserts
 * the container reports success. It is a plain script (no test framework) so it
 * can run anywhere `node` is available:
 *
 *   1. docker build -t jaros:integration .
 *   2. docker run --rm jaros:integration
 *   3. assert stdout contains JAROS_SMOKE_OK and exit code is 0.
 *
 * It SKIPS gracefully (exit 0 with a SKIP message) when the docker CLI is not
 * available, so unit-only environments do not fail — but when docker IS present
 * it genuinely builds and runs the image.
 */

import { spawnSync } from "node:child_process";
import * as path from "node:path";

const IMAGE_TAG = "jaros:integration";
const OK_MARKER = "JAROS_SMOKE_OK";
// Repo root is two levels up from dist/test/integration (and from test/integration).
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

/** True when the `docker` CLI is invocable. */
function dockerAvailable(): boolean {
  const probe = spawnSync("docker", ["--version"], { encoding: "utf8" });
  return probe.status === 0;
}

function run(args: string[]): { status: number; stdout: string; stderr: string } {
  const result = spawnSync("docker", args, {
    cwd: REPO_ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  if (result.error) {
    return { status: 1, stdout: result.stdout ?? "", stderr: String(result.error) };
  }
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function fail(message: string): never {
  console.error(`FAIL: ${message}`);
  process.exit(1);
}

function main(): void {
  if (!dockerAvailable()) {
    console.log("SKIP: docker CLI is unavailable; skipping Docker integration test.");
    process.exit(0);
  }

  console.log(`[docker-run] building image ${IMAGE_TAG} ...`);
  const build = run(["build", "-t", IMAGE_TAG, "."]);
  if (build.status !== 0) {
    console.error(build.stdout);
    console.error(build.stderr);
    fail(`docker build exited with status ${build.status}`);
  }

  console.log(`[docker-run] running container ${IMAGE_TAG} ...`);
  const runResult = run(["run", "--rm", IMAGE_TAG]);
  process.stdout.write(runResult.stdout);
  if (runResult.stderr) {
    process.stderr.write(runResult.stderr);
  }

  if (runResult.status !== 0) {
    fail(`container exited with non-zero status ${runResult.status}`);
  }
  if (!runResult.stdout.includes(OK_MARKER)) {
    fail(`container stdout did not contain "${OK_MARKER}"`);
  }

  console.log(`PASS: container printed ${OK_MARKER} and exited 0.`);
  process.exit(0);
}

main();
