"""Tests for handler determinism verification (EXT-001 / REQ-7, EXT-002 / REQ-6).

The byte-identical replay guarantee depends on executor handlers being
deterministic. These tests prove that precondition is *checkable*: deterministic
handlers make isolated replays agree, and a non-deterministic handler is
detected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jaros.core.decision import create_decision
from jaros.core.decision_gate import reset_validators
from jaros.execution import digest, executor, replays_agree
from jaros.state import DecisionLog, record_decision, replay


@pytest.fixture(autouse=True)
def _isolate():
    executor.reset_handlers(); reset_validators()
    yield
    executor.reset_handlers(); reset_validators()


def test_digest_is_canonical_and_discriminating():
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
    assert digest({"a": 1}) != digest({"a": 2})


def test_deterministic_handler_replays_agree(tmp_path: Path):
    executor.register_handler("act", lambda d, **_: {"v": d.payload.get("n")})
    dlog = DecisionLog(tmp_path / "state")
    for i in range(3):
        record_decision(dlog, create_decision(id=f"d{i}", source="a", kind="act", payload={"n": i}))

    def replay_once():
        return [digest(r.output) for r in replay(dlog, executor.apply)]

    assert replays_agree(replay_once, runs=3) is True


def test_nondeterministic_handler_is_detected(tmp_path: Path):
    calls = {"n": 0}

    def bad(d, **_):
        calls["n"] += 1
        return {"v": calls["n"]}  # depends on call count -> non-deterministic

    executor.register_handler("act", bad)
    dlog = DecisionLog(tmp_path / "state")
    record_decision(dlog, create_decision(id="d0", source="a", kind="act", payload={}))

    def replay_once():
        return [digest(r.output) for r in replay(dlog, executor.apply)]

    assert replays_agree(replay_once, runs=2) is False
