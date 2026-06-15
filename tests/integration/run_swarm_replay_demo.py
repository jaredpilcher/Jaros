"""Integration/e2e: run a SWARM in Docker, then replay it and find the culprit.

The headline proof of the Prime Directive's apex purpose (EXT-015). Boots a Jaros
container on a bind-mounted volume staged with a support-triage hive
(planner -> worker -> reviewer), submits work from the host including one seeded
**bad handoff**, STOPS the container, then runs `jaros replay` on the host and
asserts it (a) reconstructs the whole swarm byte-identically with zero model
calls and (b) attributes the failure to the exact agent + decision that produced
it. Uses the deterministic mock LLM, so it needs no model server. Skips
gracefully when docker is absent.

Run:  python tests/integration/run_swarm_replay_demo.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

IMAGE = "jaros:swarm"
CONTAINER = "jaros_swarm"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _docker_ok() -> bool:
    return shutil.which("docker") is not None and _run(["docker", "info"]).returncode == 0


def _wait(predicate, timeout=90, interval=0.5) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            if predicate():
                return True
        except OSError:
            pass
        time.sleep(interval)
    return False


def _stage_swarm(data: Path) -> None:
    """Drop the swarm agents + the handoff tool into the mounted volume."""
    for area, src in (("agents", "examples/swarm/agents"), ("tools", "examples/swarm/tools")):
        (data / area).mkdir(parents=True, exist_ok=True)
        for f in (REPO_ROOT / src).glob("*.py"):
            shutil.copy(f, data / area / f.name)


def _submit(data: Path, kind: str, payload: dict) -> subprocess.CompletedProcess:
    return _run(
        [sys.executable, "-m", "jaros.cli", "--data-dir", str(data),
         "submit", kind, "--input", json.dumps(payload)],
        cwd=str(REPO_ROOT),
    )


# #EXT-015-REQ-6 Start
def main() -> int:
    if not _docker_ok():
        print("SKIP: docker is not available.")
        return 0

    data = Path(tempfile.mkdtemp(prefix="jaros-swarm-e2e-"))
    _stage_swarm(data)
    print(f"[swarm-e2e] data dir: {data}")
    try:
        build = _run(["docker", "build", "-t", IMAGE, "."], cwd=str(REPO_ROOT))
        if build.returncode != 0:
            print(build.stdout, build.stderr)
            print("FAIL: docker build failed.")
            return 1

        _run(["docker", "rm", "-f", CONTAINER])
        # JAROS_LLM_PROVIDER=default (the deterministic mock) is already the image
        # default, so the hive runs with no model server.
        run = _run([
            "docker", "run", "-d", "--name", CONTAINER,
            "--mount", f"type=bind,source={data},target=/data", IMAGE,
        ])
        if run.returncode != 0:
            print(run.stderr)
            print("FAIL: docker run failed.")
            return 1

        if not _wait(lambda: (data / "status.json").exists(), timeout=90):
            print("FAIL: daemon did not boot.")
            return 1

        # A support-triage swarm: two clean tickets through planner -> worker ->
        # reviewer, plus one seeded BAD handoff from a worker.
        for ticket in ("login keeps failing", "double-charged on billing"):
            _submit(data, "planner", {"ticket": ticket})
            _submit(data, "worker", {"ticket": ticket})
            _submit(data, "reviewer", {"ticket": ticket})
        _submit(data, "worker", {"ticket": "refund please", "bad": True})  # the culprit

        # Wait until all 7 decisions are recorded (the bad handoff is recorded then
        # fails on execute, so it is in the log too).
        from jaros.state import DecisionLog, read_decisions

        if not _wait(lambda: len(read_decisions(DecisionLog(data / "state"))) >= 7, timeout=90):
            n = len(read_decisions(DecisionLog(data / "state")))
            print(f"FAIL: swarm did not record all decisions (got {n}/7).")
            return 1
        print("[swarm-e2e] hive ran; stopping the container (no daemon now)")
        _run(["docker", "rm", "-f", CONTAINER])

        # Replay the whole swarm ON THE HOST against the container-recorded log.
        replay = _run(
            [sys.executable, "-m", "jaros.cli", "--data-dir", str(data), "replay", "--json"],
            cwd=str(REPO_ROOT),
        )
        report = json.loads(replay.stdout.strip() or "{}")
        print(f"[swarm-e2e] jaros replay --json -> {json.dumps(report)}")
        attrib = report.get("attribution") or {}

        checks = {
            "exit 0 (reproducible)": replay.returncode == 0,
            "byte-identical swarm replay": report.get("byteIdentical") is True,
            "zero model calls": report.get("modelCalls") == 0,
            "tamper-evident chain intact": report.get("chainOk") is True,
            "all 7 decisions across 3 agents": report.get("decisions") == 7
                and set(report.get("byAgent", {})) == {"planner", "worker", "reviewer"},
            "culprit attributed to a worker": attrib.get("source") == "worker"
                and attrib.get("kind") == "failure",
        }
        for name, ok in checks.items():
            print(f"        [{'PASS' if ok else 'FAIL'}] {name}")
        if all(checks.values()):
            print("PASS: a container-recorded swarm replays byte-identically AND the culprit is found.")
            return 0
        print("FAIL: swarm replay did not reproduce + attribute the run.")
        return 1
    finally:
        _run(["docker", "rm", "-f", CONTAINER])
        shutil.rmtree(data, ignore_errors=True)


# #EXT-015-REQ-6 End


if __name__ == "__main__":
    raise SystemExit(main())
