"""Tests for the Jaros Runtime Daemon (EXT-007 / REQ-1,2,4,5).

The daemon's ``run()`` loops forever, so it is never called here; behavior is
driven through ``tick()`` and helpers using ``tmp_path`` as the data dir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jaros.core.decision_gate import reset_validators
from jaros.daemon import Daemon
from jaros.execution import executor


@pytest.fixture(autouse=True)
def _isolate_executor():
    """Reset module-global executor handlers / gate validators around each test."""
    executor.reset_handlers()
    reset_validators()
    yield
    executor.reset_handlers()
    reset_validators()


def _submit_job(data: Path, job_id: str, kind: str, job_input: object) -> None:
    (data / "inbox" / f"{job_id}.json").write_text(
        json.dumps({"id": job_id, "kind": kind, "input": job_input}),
        encoding="utf-8",
    )


def _status(data: Path) -> dict:
    return json.loads((data / "status.json").read_text(encoding="utf-8"))


def test_boot_creates_layout_and_status(tmp_path: Path):
    d = Daemon(tmp_path)
    for name in ("inbox", "outbox", "plugins", "processed", "failed", "state"):
        assert (tmp_path / name).is_dir()
    d.tick()
    status = _status(tmp_path)
    assert status["processed"] == 0
    assert status["failed"] == 0
    assert status["tick"] >= 1


def test_tick_processes_job_writes_outbox_and_moves_to_processed(tmp_path: Path):
    d = Daemon(tmp_path)
    _submit_job(tmp_path, "job1", "advance", {"task": "demo"})

    d.tick()

    # outbox result written
    outbox = tmp_path / "outbox" / "job1.json"
    assert outbox.is_file()
    result = json.loads(outbox.read_text(encoding="utf-8"))
    assert result["id"] == "job1"
    assert result["result"]["finalState"] == "DONE"

    # job moved to processed/, gone from inbox/
    assert (tmp_path / "processed" / "job1.json").is_file()
    assert not (tmp_path / "inbox" / "job1.json").exists()

    # status reflects the processed job
    status = _status(tmp_path)
    assert status["processed"] == 1
    assert status["failed"] == 0
    assert status["state"] == "DONE"
    assert status["lastResult"]["finalState"] == "DONE"


def test_durable_log_records_transitions(tmp_path: Path):
    d = Daemon(tmp_path)
    _submit_job(tmp_path, "j", "advance", None)
    d.tick()
    # PENDING -> start -> RUNNING -> complete -> DONE  (two committed entries)
    entries = list(d.log.read())
    assert [e.state for e in entries] == ["RUNNING", "DONE"]


def test_erroring_job_goes_to_failed_and_daemon_survives(tmp_path: Path):
    d = Daemon(tmp_path)
    # Unknown kind -> registry.resolve raises -> failed/
    _submit_job(tmp_path, "bad", "does-not-exist", None)
    d.tick()

    assert (tmp_path / "failed" / "bad.json").is_file()
    assert (tmp_path / "failed" / "bad.json.reason").is_file()
    reason = (tmp_path / "failed" / "bad.json.reason").read_text(encoding="utf-8")
    assert "does-not-exist" in reason
    assert not (tmp_path / "inbox" / "bad.json").exists()

    status = _status(tmp_path)
    assert status["failed"] == 1
    assert status["processed"] == 0

    # Daemon survives: a subsequent good job still processes.
    _submit_job(tmp_path, "good", "advance", None)
    d.tick()
    assert (tmp_path / "outbox" / "good.json").is_file()
    status = _status(tmp_path)
    assert status["processed"] == 1
    assert status["failed"] == 1


def test_status_reflects_counts_after_multiple_ticks(tmp_path: Path):
    d = Daemon(tmp_path)
    _submit_job(tmp_path, "a", "advance", None)
    _submit_job(tmp_path, "b", "advance", None)
    _submit_job(tmp_path, "c", "does-not-exist", None)
    d.tick()
    status = _status(tmp_path)
    assert status["processed"] == 2
    assert status["failed"] == 1
    assert (tmp_path / "outbox" / "a.json").is_file()
    assert (tmp_path / "outbox" / "b.json").is_file()


def _write_plugin(data: Path, name: str, kind: str) -> None:
    (data / "plugins" / f"{name}.py").write_text(
        "from jaros.core import create_decision\n"
        "import uuid\n"
        f"KIND = {kind!r}\n"
        "def build(llm):\n"
        "    class _B:\n"
        "        def decide(self, context):\n"
        "            return [create_decision(id='p-'+uuid.uuid4().hex,\n"
        f"                source={kind!r}, kind='advance',\n"
        "                payload={'events': ['start', 'complete'], 'note': 'via-plugin'})]\n"
        "    return _B()\n",
        encoding="utf-8",
    )


def test_plugin_dropped_into_plugins_becomes_usable(tmp_path: Path):
    d = Daemon(tmp_path)
    assert not d.registry.has("custom")

    _write_plugin(tmp_path, "custom_plugin", "custom")
    # A job for the plugin kind, processed in the same tick that scans plugins.
    _submit_job(tmp_path, "p1", "custom", {"x": 1})
    d.tick()

    assert d.registry.has("custom")
    outbox = tmp_path / "outbox" / "p1.json"
    assert outbox.is_file()
    result = json.loads(outbox.read_text(encoding="utf-8"))
    assert result["result"]["note"] == "via-plugin"
    assert result["result"]["finalState"] == "DONE"


def test_heartbeat_line_printed(tmp_path: Path, capsys):
    d = Daemon(tmp_path)
    d.tick()
    out = capsys.readouterr().out
    assert "JAROS_HEARTBEAT" in out


def test_stop_and_teardown_release_grants(tmp_path: Path):
    d = Daemon(tmp_path)
    d.tick()
    d.stop()
    d._teardown()
    # status still written after teardown
    assert (tmp_path / "status.json").is_file()
