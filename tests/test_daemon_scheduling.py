"""Integration test: the daemon dispatches due schedules into the inbox (EXT-011 / REQ-4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jaros.core.decision_gate import reset_validators
from jaros.daemon import Daemon
from jaros.execution import executor


@pytest.fixture(autouse=True)
def _isolate_executor():
    executor.reset_handlers()
    reset_validators()
    yield
    executor.reset_handlers()
    reset_validators()


def _write_schedule(data: Path, name: str, body: dict) -> None:
    (data / "schedules").mkdir(parents=True, exist_ok=True)
    (data / "schedules" / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def test_due_schedule_dispatches_job(tmp_path: Path):
    _write_schedule(tmp_path, "heartbeat", {"id": "heartbeat", "kind": "advance", "input": {}, "every_seconds": 1})
    d = Daemon(tmp_path)

    d.tick()  # first tick: schedule has no prior state -> fires immediately

    # The dispatch is synchronous within the tick; a job descriptor was written
    # and the schedule counter incremented.
    assert d.scheduled >= 1
    all_jobs = list((tmp_path / "inbox").glob("*.json")) + list((tmp_path / "processed").glob("*.json"))
    assert any(j.name.startswith("heartbeat-") for j in all_jobs)


def test_status_reports_schedules(tmp_path: Path):
    _write_schedule(tmp_path, "nightly", {"id": "nightly", "kind": "advance", "input": {}, "cron": "0 0 * * *"})
    d = Daemon(tmp_path)
    d.tick()
    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    ids = [s["id"] for s in status.get("schedules", [])]
    assert "nightly" in ids
    assert "scheduled" in status


def test_disabled_schedule_not_dispatched(tmp_path: Path):
    _write_schedule(tmp_path, "off", {"id": "off", "kind": "advance", "input": {}, "every_seconds": 1, "enabled": False})
    d = Daemon(tmp_path)
    d.tick()
    assert d.scheduled == 0
