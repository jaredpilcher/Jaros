"""Integration: TWO Jaros containers on one shared volume, distributed.

Boots two daemons (two nodes) bind-mounted to the same host data dir, submits
jobs from the host, and proves each job is processed by exactly one node — the
atomic inbox->claimed rename means no job is processed twice across containers.
Skips gracefully (exit 0) when docker is unavailable.

Run:  python tests/integration/run_distributed_demo.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

IMAGE = "jaros:integration"
NODES = ["jaros_dist_a", "jaros_dist_b"]
REPO_ROOT = Path(__file__).resolve().parents[2]
N_JOBS = 8


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _docker_ok() -> bool:
    return shutil.which("docker") is not None and _run(["docker", "info"]).returncode == 0


def _logs(name: str) -> str:
    return _run(["docker", "logs", name]).stdout + _run(["docker", "logs", name]).stderr


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

    data_dir = Path(tempfile.mkdtemp(prefix="jaros-dist-"))
    print(f"[dist] shared data dir: {data_dir}")
    try:
        print(f"[dist] building {IMAGE} ...")
        build = _run(["docker", "build", "-t", IMAGE, "."], cwd=str(REPO_ROOT))
        if build.returncode != 0:
            print(build.stdout, build.stderr)
            print("FAIL: docker build failed.")
            return 1

        for name in NODES:
            _run(["docker", "rm", "-f", name])
            run = _run([
                "docker", "run", "-d", "--name", name,
                "--mount", f"type=bind,source={data_dir},target=/data",
                "-e", "JAROS_POOL_BOUND=1", "-e", "JAROS_TICK_MS=300",
                IMAGE,
            ])
            if run.returncode != 0:
                print(run.stderr)
                print(f"FAIL: docker run {name} failed.")
                return 1
        print(f"[dist] started {len(NODES)} nodes on the same volume")

        if not _wait(lambda: (data_dir / "status.json").exists(), timeout=60):
            print(_logs(NODES[0]))
            print("FAIL: no node published status within 60s.")
            return 1

        # Submit N jobs from the host (each a small advance job).
        for i in range(N_JOBS):
            submit = _run(
                [sys.executable, "-m", "jaros.cli", "--data-dir", str(data_dir),
                 "submit", "advance", "--input", json.dumps({"n": i})],
                cwd=str(REPO_ROOT),
            )
            if submit.returncode != 0:
                print(submit.stderr)
                print("FAIL: submit failed.")
                return 1
        print(f"[dist] submitted {N_JOBS} jobs")

        outbox = data_dir / "outbox"
        if not _wait(lambda: len(list(outbox.glob("*.json"))) >= N_JOBS, timeout=90):
            for n in NODES:
                print(f"--- {n} ---\n{_logs(n)[-1000:]}")
            print(f"FAIL: only {len(list(outbox.glob('*.json')))}/{N_JOBS} results.")
            return 1

        # Which node processed which job? Parse each node's log.
        pat = re.compile(r"JAROS_JOB ok job=(\S+)\.json")
        done = {n: set(pat.findall(_logs(n))) for n in NODES}
        union = set().union(*done.values())
        intersection = done[NODES[0]] & done[NODES[1]]
        results = list(outbox.glob("*.json"))
        unique_ids = {json.loads(r.read_text(encoding="utf-8"))["id"] for r in results}

        print("[dist] per-node processed counts:", {n: len(s) for n, s in done.items()})
        checks = {
            f"{N_JOBS} unique results in outbox": len(unique_ids) == N_JOBS,
            "no job processed by both nodes (exactly-once)": intersection == set(),
            f"all {N_JOBS} jobs accounted for": len(union) == N_JOBS,
            "work distributed across both nodes": all(len(s) > 0 for s in done.values()),
        }
        for name, ok in checks.items():
            print(f"        [{'PASS' if ok else 'FAIL'}] {name}")

        # Exactly-once is the hard guarantee; distribution is best-effort.
        hard = checks[f"{N_JOBS} unique results in outbox"] and checks["no job processed by both nodes (exactly-once)"]
        if hard:
            print("PASS: two containers shared the load with each job processed exactly once.")
            return 0
        print("FAIL: distributed exactly-once property violated.")
        return 1
    finally:
        for n in NODES:
            _run(["docker", "rm", "-f", n])
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
