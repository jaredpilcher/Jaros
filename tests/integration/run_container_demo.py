"""Integration test: actually run the Jaros OS in a Docker container and drive
it from the host via the shared-FS CLI.

This proves the end-to-end story the Prime Directive demands:
  - the OS boots inside the container and keeps running (EXT-007);
  - the host adds work ONLY through the shared volume, using the CLI (EXT-008);
  - the daemon ingests the job, runs an agent as a thread, validates the
    decision, drives a durable state transition, and writes a result;
  - the host watches the result + status purely by reading the shared volume.

It builds the image, runs the container with a bind-mounted data dir, submits a
job with `jaros submit`, polls the mounted `outbox/` + `status.json`, and asserts
success. Skips gracefully (exit 0) when docker is unavailable.

Run:  python tests/integration/run_container_demo.py
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
CONTAINER = "jaros_demo"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return _run(["docker", "info"]).returncode == 0


def main() -> int:
    if not _docker_available():
        print("SKIP: docker is not available; skipping container integration test.")
        return 0

    data_dir = Path(tempfile.mkdtemp(prefix="jaros-demo-"))
    print(f"[demo] host data dir: {data_dir}")

    try:
        print(f"[demo] building image {IMAGE} ...")
        build = _run(["docker", "build", "-t", IMAGE, "."], cwd=str(REPO_ROOT))
        if build.returncode != 0:
            print(build.stdout)
            print(build.stderr)
            print("FAIL: docker build failed.")
            return 1

        # Clean any stale container, then boot the OS with the host dir bind-mounted
        # at /data. --mount avoids ':' path-parsing issues across OSes.
        _run(["docker", "rm", "-f", CONTAINER])
        print(f"[demo] starting the OS (container {CONTAINER}) ...")
        run = _run(
            [
                "docker", "run", "-d", "--name", CONTAINER,
                "--mount", f"type=bind,source={data_dir},target=/data",
                IMAGE,
            ]
        )
        if run.returncode != 0:
            print(run.stderr)
            print("FAIL: docker run failed.")
            return 1

        # Wait for the daemon to boot (status.json appears in the shared volume).
        status_path = data_dir / "status.json"
        if not _wait_for(lambda: status_path.exists(), timeout=30):
            print(_logs())
            print("FAIL: daemon did not publish status.json within 30s.")
            return 1
        print("[demo] OS booted; status.json is live.")

        # Add work from the HOST using the CLI — pure shared-FS transport.
        print("[demo] submitting a job from the host via `jaros submit` ...")
        submit = _run(
            [sys.executable, "-m", "jaros.cli", "--data-dir", str(data_dir),
             "submit", "advance", "--input", "{}"],
            cwd=str(REPO_ROOT),
        )
        print("       " + submit.stdout.strip())
        if submit.returncode != 0:
            print(submit.stderr)
            print("FAIL: `jaros submit` failed.")
            return 1

        # Watch for the result purely by reading the shared volume.
        outbox = data_dir / "outbox"
        if not _wait_for(lambda: any(outbox.glob("*.json")), timeout=30):
            print(_logs())
            print("FAIL: no result appeared in outbox/ within 30s.")
            return 1

        result_file = next(iter(outbox.glob("*.json")))
        result = json.loads(result_file.read_text(encoding="utf-8"))
        status = json.loads(status_path.read_text(encoding="utf-8"))
        print(f"[demo] result: {result_file.name} -> {json.dumps(result)[:200]}")
        print(f"[demo] status: processed={status.get('processed')} "
              f"failed={status.get('failed')} state={status.get('state')}")

        ok = status.get("processed", 0) >= 1 and status.get("failed", 0) == 0
        # The daemon keeps running (it's an OS) — show a couple heartbeat lines.
        print("[demo] recent daemon heartbeat:")
        for line in _logs().splitlines()[-4:]:
            print("       " + line)

        if ok:
            print("PASS: the OS booted in the container, ingested a host-submitted "
                  "job over the shared volume, and produced a result.")
            return 0
        print("FAIL: status did not reflect a clean processed job.")
        return 1
    finally:
        _run(["docker", "rm", "-f", CONTAINER])
        shutil.rmtree(data_dir, ignore_errors=True)


def _logs() -> str:
    return _run(["docker", "logs", CONTAINER]).stdout


def _wait_for(predicate, timeout: float, interval: float = 0.5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if predicate():
                return True
        except OSError:
            pass
        time.sleep(interval)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
