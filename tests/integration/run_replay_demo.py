"""Integration/e2e: record a run in a container, then `jaros replay` on the host.

Boots a Jaros container on a bind-mounted volume, submits jobs from the host so
the daemon records the decision + transition logs, STOPS the container, then runs
`jaros replay` on the host (no daemon) and asserts it reconstructs the run
byte-identically with zero model calls. Skips gracefully when docker is absent.

Run:  python tests/integration/run_replay_demo.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

IMAGE = "jaros:integration"
CONTAINER = "jaros_replay"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _docker_ok() -> bool:
    return shutil.which("docker") is not None and _run(["docker", "info"]).returncode == 0


def _wait(predicate, timeout=60, interval=0.5) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            if predicate():
                return True
        except OSError:
            pass
        time.sleep(interval)
    return False


def main() -> int:
    if not _docker_ok():
        print("SKIP: docker is not available.")
        return 0

    data = Path(tempfile.mkdtemp(prefix="jaros-replay-e2e-"))
    print(f"[replay-e2e] data dir: {data}")
    try:
        build = _run(["docker", "build", "-t", IMAGE, "."], cwd=str(REPO_ROOT))
        if build.returncode != 0:
            print(build.stdout, build.stderr)
            print("FAIL: docker build failed.")
            return 1

        _run(["docker", "rm", "-f", CONTAINER])
        run = _run([
            "docker", "run", "-d", "--name", CONTAINER,
            "--mount", f"type=bind,source={data},target=/data", IMAGE,
        ])
        if run.returncode != 0:
            print(run.stderr)
            print("FAIL: docker run failed.")
            return 1

        if not _wait(lambda: (data / "status.json").exists(), timeout=60):
            print("FAIL: daemon did not boot.")
            return 1

        for i in range(3):
            submit = _run(
                [sys.executable, "-m", "jaros.cli", "--data-dir", str(data),
                 "submit", "advance", "--input", json.dumps({"n": i})],
                cwd=str(REPO_ROOT),
            )
            if submit.returncode != 0:
                print(submit.stderr)
                print("FAIL: submit failed.")
                return 1

        # Wait for the run to COMPLETE (outbox results) — each outbox write is the
        # last step after the transitions commit, so the durable logs are whole.
        if not _wait(lambda: len(list((data / "outbox").glob("*.json"))) >= 3, timeout=60):
            print("FAIL: run did not complete (no outbox results).")
            return 1
        print("[replay-e2e] container completed the run; stopping it (no daemon now)")
        _run(["docker", "rm", "-f", CONTAINER])

        # Replay ON THE HOST against the container-recorded logs.
        replay = _run(
            [sys.executable, "-m", "jaros.cli", "--data-dir", str(data), "replay", "--json"],
            cwd=str(REPO_ROOT),
        )
        print(f"[replay-e2e] jaros replay --json -> {replay.stdout.strip()}")
        report = json.loads(replay.stdout.strip() or "{}")

        checks = {
            "exit 0 (reproducible)": replay.returncode == 0,
            "byte-identical": report.get("byteIdentical") is True,
            "zero model calls": report.get("modelCalls") == 0,
            "decisions replayed >= 3": report.get("decisions", 0) >= 3,
            "ok": report.get("ok") is True,
        }
        for name, ok in checks.items():
            print(f"        [{'PASS' if ok else 'FAIL'}] {name}")
        if all(checks.values()):
            print("PASS: a container-recorded run replays byte-identically on the host, no model call.")
            return 0
        print("FAIL: replay did not reproduce the container run.")
        return 1
    finally:
        _run(["docker", "rm", "-f", CONTAINER])
        shutil.rmtree(data, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
