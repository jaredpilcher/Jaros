"""Tests for the durable harness audit log (EXT-005 / REQ-7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jaros.comms.fs import SharedFileSystem
from jaros.core.decision_gate import reset_validators
from jaros.daemon import Daemon
from jaros.execution import executor
from jaros.harness import Action, GrantSpec, Harness, read_audit


def test_audit_records_allowed_and_denied(tmp_path: Path):
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    audit = tmp_path / "state" / "audit.log"
    h = Harness(audit_path=audit)
    h.spawn("a", GrantSpec(role="FsWriteRole", fs=fs))

    ok = h.request("a", Action(type="fs.write", path="artifacts/x.txt", data="hi"))
    assert ok.allowed
    denied = h.request("a", Action(type="mystery"))  # unknown action -> fail closed
    assert not denied.allowed

    entries = read_audit(audit)
    assert len(entries) == 2
    assert entries[0]["allowed"] is True and entries[0]["action"] == "fs.write"
    assert entries[1]["allowed"] is False and entries[1]["action"] == "mystery"
    assert entries[1]["reason"]


def test_no_audit_path_writes_nothing(tmp_path: Path):
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    h = Harness()  # auditing disabled
    h.spawn("a", GrantSpec(role="FsWriteRole", fs=fs))
    h.request("a", Action(type="mystery"))
    assert not (tmp_path / "state" / "audit.log").exists()


def test_daemon_writes_audit_for_mediated_writes(tmp_path: Path):
    executor.reset_handlers()
    reset_validators()
    try:
        d = Daemon(tmp_path)
        (tmp_path / "inbox" / "j.json").write_text(
            json.dumps({"id": "j", "agent": "advance", "input": {}}), encoding="utf-8"
        )
        for _ in range(40):
            d.tick()
            if d.processed >= 1:
                break
        assert d.processed >= 1
        entries = read_audit(tmp_path / "state" / "audit.log")
        # The daemon writes each job result to outbox via a harness-mediated fs.write.
        assert any(e["action"] == "fs.write" and e["allowed"] for e in entries)
    finally:
        executor.reset_handlers()
        reset_validators()
