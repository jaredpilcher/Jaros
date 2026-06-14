"""Tests for the `jaros replay` command (EXT-008 / REQ-6).

Proves the differentiator and the safety properties: a recorded run replays
byte-identical with zero model calls, into an isolated sandbox that never touches
the live data dir, with honest exit codes.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from jaros.cli import cmd_replay
from jaros.core.decision_gate import reset_validators
from jaros.daemon import Daemon
from jaros.execution import executor


@pytest.fixture(autouse=True)
def _isolate():
    executor.reset_handlers(); reset_validators()
    yield
    executor.reset_handlers(); reset_validators()


def _record_run(data: Path, n: int = 2) -> None:
    d = Daemon(data)
    for i in range(n):
        (data / "inbox" / f"j{i}.json").write_text(
            json.dumps({"id": f"j{i}", "kind": "advance", "input": {"note": f"r{i}"}}),
            encoding="utf-8",
        )
    for _ in range(60):
        d.tick()
        if d.processed >= n:
            break
    assert d.processed >= n


def _dir_hash(p: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(x for x in p.rglob("*") if x.is_file()):
        h.update(f.relative_to(p).as_posix().encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


def _replay_json(data: Path) -> tuple[int, dict]:
    buf = io.StringIO()
    code = cmd_replay(data, as_json=True, stream=buf)
    return code, json.loads(buf.getvalue())


def test_round_trip_is_byte_identical(tmp_path: Path):
    _record_run(tmp_path)
    code, rep = _replay_json(tmp_path)
    assert code == 0
    assert rep["byteIdentical"] is True
    assert rep["ok"] is True
    assert rep["modelCalls"] == 0
    assert rep["finalState"] == "DONE"


def test_replay_makes_no_model_call(tmp_path: Path, monkeypatch):
    _record_run(tmp_path)
    import jaros.llm

    def _boom(*a, **k):
        raise AssertionError("replay constructed an LlmClient")

    monkeypatch.setattr(jaros.llm, "create_llm_client", _boom)
    assert cmd_replay(tmp_path, as_json=True, stream=io.StringIO()) == 0


def test_replay_does_not_mutate_live_data(tmp_path: Path):
    _record_run(tmp_path)
    before = _dir_hash(tmp_path)
    cmd_replay(tmp_path, as_json=True, stream=io.StringIO())
    assert _dir_hash(tmp_path) == before  # side effects went to the sandbox


def test_empty_log_is_exit_2(tmp_path: Path):
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    assert cmd_replay(tmp_path, stream=buf) == 2
    assert "nothing to replay" in buf.getvalue()


def test_divergence_is_exit_1(tmp_path: Path):
    _record_run(tmp_path)
    # Corrupt the live transition log so it no longer matches a faithful replay.
    with open(tmp_path / "state" / "transitions.log", "a", encoding="utf-8") as fh:
        fh.write('{"index":99,"event":"x"')  # torn extra line -> bytes differ
    code, rep = _replay_json(tmp_path)
    assert code == 1
    assert rep["byteIdentical"] is False
    assert rep["ok"] is False


def test_json_shape(tmp_path: Path):
    _record_run(tmp_path)
    _, rep = _replay_json(tmp_path)
    assert set(rep) >= {"decisions", "modelCalls", "finalState", "byteIdentical", "ok"}
    assert rep["decisions"] == 2
