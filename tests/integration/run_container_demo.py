"""Integration test: actually run the Jaros OS in a Docker container and drive
it from the host via the shared-FS CLI, with example agents.

This proves the end-to-end story the Prime Directive demands:
  - the OS boots inside the container and keeps running (EXT-007);
  - the host adds work + plugins + tools ONLY through the shared volume (EXT-006/008);
  - the daemon ingests each job, runs an agent as a thread, validates the
    decision, drives a durable state transition, and writes a result;
  - a built-in agent, two example plugin agents (one calling a custom tool), all
    run; every accepted decision is recorded to the durable decision log
    (EXT-002 / REQ-6);
  - the host watches results + status purely by reading the shared volume.

It builds the image, runs the container with a bind-mounted throwaway data dir,
stages the example plugins/tools into it, submits jobs with `jaros submit`, polls
the mounted `outbox/` + `status.json`, and asserts success. Skips gracefully
(exit 0) when docker is unavailable.

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
EXAMPLES = REPO_ROOT / "examples"


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

    # Stage the example plugin agents + custom tool into the shared volume so the
    # containerized daemon loads them at runtime over the mount.
    (data_dir / "plugins").mkdir(parents=True, exist_ok=True)
    (data_dir / "tools").mkdir(parents=True, exist_ok=True)
    for p in (EXAMPLES / "plugins").glob("*.py"):
        shutil.copy(p, data_dir / "plugins" / p.name)
    for p in (EXAMPLES / "tools").glob("*.py"):
        shutil.copy(p, data_dir / "tools" / p.name)

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
        if not _wait_for(lambda: status_path.exists(), timeout=60):
            print(_logs())
            print("FAIL: daemon did not publish status.json within 60s.")
            return 1
        print("[demo] OS booted; status.json is live.")

        # Add work from the HOST using the CLI — pure shared-FS transport.
        jobs = [
            ("advance", "{}"),
            ("echo", '{"msg": "hello from the host"}'),
            ("greeter", '{"name": "Jaros"}'),
        ]
        for kind, payload in jobs:
            submit = _run(
                [sys.executable, "-m", "jaros.cli", "--data-dir", str(data_dir),
                 "submit", kind, "--input", payload],
                cwd=str(REPO_ROOT),
            )
            print(f"[demo] submit {kind}: {submit.stdout.strip() or submit.stderr.strip()}")
            if submit.returncode != 0:
                print(submit.stderr)
                print("FAIL: `jaros submit` failed.")
                return 1

        # Watch for results purely by reading the shared volume.
        outbox = data_dir / "outbox"
        if not _wait_for(lambda: len(list(outbox.glob("*.json"))) >= 3, timeout=60):
            print(_logs())
            print("FAIL: fewer than 3 results appeared in outbox/ within 60s.")
            return 1

        results = {}
        for f in outbox.glob("*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            results[r.get("kind")] = r.get("result")
        status = json.loads(status_path.read_text(encoding="utf-8"))
        print("[demo] outbox results:")
        for kind, res in results.items():
            print(f"        {kind}: {json.dumps(res)[:160]}")
        print(f"[demo] status: processed={status.get('processed')} "
              f"failed={status.get('failed')} state={status.get('state')}")

        # The durable decision log must have recorded every accepted decision.
        sys.path.insert(0, str(REPO_ROOT))
        from jaros.state import DecisionLog
        recorded = DecisionLog(data_dir / "state").length()
        print(f"[demo] decision log records: {recorded}")

        checks = {
            "processed >= 3": status.get("processed", 0) >= 3,
            "no failures": status.get("failed", 1) == 0,
            "advance ran": isinstance(results.get("advance"), dict),
            "echo agent ran": "echo" in results,
            "greeter+custom tool ran":
                isinstance(results.get("greeter"), dict)
                and "hello, Jaros!" in json.dumps(results.get("greeter")),
            "decisions recorded (>=3)": recorded >= 3,
        }
        print("[demo] checks:")
        for name, ok in checks.items():
            print(f"        [{'PASS' if ok else 'FAIL'}] {name}")

        print("[demo] recent daemon heartbeat:")
        for line in _logs().splitlines()[-4:]:
            print("       " + line)

        if all(checks.values()):
            print("PASS: the OS booted in the container, ingested host-submitted jobs "
                  "(built-in + example plugin agents + a custom tool) over the shared "
                  "volume, produced results, and recorded decisions for replay.")
            return 0
        print("FAIL: one or more checks failed.")
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
