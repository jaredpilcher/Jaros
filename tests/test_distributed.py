"""Multi-node distribution tests (EXT-002 / REQ-7, EXT-007).

Two daemons sharing one data directory coordinate over the file system: an atomic
inbox -> claimed rename means each job is processed by exactly one node, never
twice — the distributed property an enterprise deployment needs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jaros.core.decision_gate import reset_validators
from jaros.daemon import Daemon
from jaros.execution import executor


@pytest.fixture(autouse=True)
def _isolate():
    executor.reset_handlers()
    reset_validators()
    yield
    executor.reset_handlers()
    reset_validators()


def _submit(data: Path, job_id: str, kind: str = "advance", inp=None) -> None:
    (data / "inbox").mkdir(parents=True, exist_ok=True)
    (data / "inbox" / f"{job_id}.json").write_text(
        json.dumps({"id": job_id, "kind": kind, "input": inp or {}}), encoding="utf-8"
    )


def test_two_nodes_process_each_job_exactly_once(tmp_path: Path):
    # Two daemons on the SAME shared volume = two nodes.
    a = Daemon(tmp_path)
    b = Daemon(tmp_path)
    for i in range(6):
        _submit(tmp_path, f"job{i}")

    for _ in range(80):
        a.tick()
        b.tick()
        if a.processed + b.processed >= 6:
            break

    # Exactly-once: every job processed, none twice.
    assert a.processed + b.processed == 6
    outbox = list((tmp_path / "outbox").glob("*.json"))
    assert len(outbox) == 6
    ids = {json.loads(o.read_text(encoding="utf-8"))["id"] for o in outbox}
    assert ids == {f"job{i}" for i in range(6)}
    # No job left stranded in the claim area.
    assert list((tmp_path / "claimed").glob("*.json")) == []


def test_boot_reclaims_orphaned_claim(tmp_path: Path):
    # Simulate a node that crashed after claiming a job (it sits in claimed/).
    (tmp_path / "claimed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "claimed" / "stuck.json").write_text(
        json.dumps({"id": "stuck", "kind": "advance", "input": {}}), encoding="utf-8"
    )

    d = Daemon(tmp_path)  # boot reclaim moves it back to inbox
    assert (tmp_path / "inbox" / "stuck.json").exists()

    for _ in range(40):
        d.tick()
        if d.processed >= 1:
            break
    assert d.processed >= 1
    assert (tmp_path / "outbox" / "stuck.json").exists()
