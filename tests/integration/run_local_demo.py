"""Integration smoke: stand up the Jaros OS locally (no Docker) on a throwaway
data dir and drive it from the host via the shared-FS CLI, with example agents.

Proves the end-to-end story without touching any in-use data dir:
  - the daemon boots and keeps running (EXT-007);
  - host work + plugins/tools arrive only through the shared volume (EXT-006/008);
  - a built-in agent and two example plugin agents (one calling a custom tool)
    each run, validate, drive durable transitions, and write a result;
  - every accepted decision is recorded to the durable decision log (EXT-002/REQ-6).

Uses a fresh ``tempfile.mkdtemp`` dir and a daemon process this script starts and
stops itself — it never writes to ``.jaros-data`` or any externally-owned dir.

Run:  python tests/integration/run_local_demo.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"


def _cli(data_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "jaros.cli", "--data-dir", str(data_dir), *args],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def _wait_for(predicate, timeout: float, interval: float = 0.3) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if predicate():
                return True
        except OSError:
            pass
        time.sleep(interval)
    return False


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="jaros-local-"))
    print(f"[local] throwaway data dir: {data_dir}")

    # Stage example plugins + a custom tool into the shared volume before boot.
    (data_dir / "plugins").mkdir(parents=True, exist_ok=True)
    (data_dir / "tools").mkdir(parents=True, exist_ok=True)
    for p in (EXAMPLES / "plugins").glob("*.py"):
        shutil.copy(p, data_dir / "plugins" / p.name)
    for p in (EXAMPLES / "tools").glob("*.py"):
        shutil.copy(p, data_dir / "tools" / p.name)

    log_path = data_dir / "daemon.out"
    env = {**os.environ, "JAROS_TICK_MS": "150", "JAROS_LLM_PROVIDER": "default"}
    env.pop("JAROS_DATA_DIR", None)  # never inherit an external data dir

    print("[local] starting daemon (jaros serve) ...")
    with open(log_path, "w", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            [sys.executable, "-m", "jaros.cli", "--data-dir", str(data_dir), "serve"],
            stdout=logf, stderr=subprocess.STDOUT, cwd=str(REPO_ROOT), env=env,
        )
    try:
        status_path = data_dir / "status.json"
        if not _wait_for(status_path.exists, timeout=30):
            print(log_path.read_text(encoding="utf-8"))
            print("FAIL: daemon did not publish status.json within 30s.")
            return 1
        print("[local] OS booted; status.json is live.")

        # Submit work from the host: built-in + two example plugin agents.
        jobs = [
            ("advance", "{}"),
            ("echo", '{"msg": "hello from the host"}'),
            ("greeter", '{"name": "Jaros"}'),
        ]
        for kind, payload in jobs:
            r = _cli(data_dir, "submit", kind, "--input", payload)
            print(f"[local] submit {kind}: {r.stdout.strip() or r.stderr.strip()}")
            if r.returncode != 0:
                print("FAIL: submit failed.")
                return 1

        outbox = data_dir / "outbox"
        if not _wait_for(lambda: len(list(outbox.glob("*.json"))) >= 3, timeout=30):
            print(log_path.read_text(encoding="utf-8"))
            print("FAIL: fewer than 3 results appeared in outbox/ within 30s.")
            return 1

        results = {}
        for f in outbox.glob("*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            results[r.get("kind")] = r.get("result")
        print("[local] outbox results:")
        for kind, res in results.items():
            print(f"        {kind}: {json.dumps(res)[:160]}")

        status = json.loads(status_path.read_text(encoding="utf-8"))
        print(f"[local] status: processed={status.get('processed')} "
              f"failed={status.get('failed')} state={status.get('state')}")

        # Verify the durable decision log recorded every accepted decision.
        sys.path.insert(0, str(REPO_ROOT))
        from jaros.state import DecisionLog
        dlog = DecisionLog(data_dir / "state")
        recorded = dlog.length()
        print(f"[local] decision log records: {recorded}")

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
        print("[local] checks:")
        for name, ok in checks.items():
            print(f"        [{'PASS' if ok else 'FAIL'}] {name}")

        if all(checks.values()):
            print("PASS: local OS stood up, ran built-in + example plugin agents + "
                  "a custom tool, and recorded decisions for replay.")
            return 0
        print(log_path.read_text(encoding="utf-8")[-1500:])
        print("FAIL: one or more checks failed.")
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
