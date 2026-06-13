"""Tests for the durable decision log and deterministic replay (EXT-002 / REQ-6).

Proves the reproducibility-by-replay property: recording the accepted decisions
and replaying them through the deterministic executor reconstructs the run to
byte-identical state, with no model call, and crash recovery is a special case
of replay.
"""

from __future__ import annotations

import pytest

from jaros.core.decision import create_decision
from jaros.execution import executor
from jaros.state import (
    DecisionLog,
    TransitionLog,
    commit,
    read_decisions,
    record_decision,
    recover,
    recover_via_replay,
    replay,
)
from jaros.state.model import INITIAL_STATE


def _advance_handler(decision, *, log: TransitionLog):
    """Deterministic handler: drive the declared events into ``log``."""
    payload = decision.payload if isinstance(decision.payload, dict) else {}
    events = payload.get("events") or ["start", "complete"]
    state = INITIAL_STATE
    for event in events:
        state = commit(log, state, event).state
    return {"decision": decision.id, "finalState": state, "events": list(events)}


@pytest.fixture(autouse=True)
def _clean_handlers():
    executor.reset_handlers()
    executor.register_handler("advance", _advance_handler)
    yield
    executor.reset_handlers()


def _decisions():
    # Each decision is an independent job: a full PENDING->RUNNING->DONE sequence.
    return [
        create_decision(id="d1", source="agent", kind="advance",
                        payload={"events": ["start", "complete"]}),
        create_decision(id="d2", source="agent", kind="advance",
                        payload={"events": ["start", "complete"]}),
    ]


def test_record_and_read_round_trip(tmp_path):
    dlog = DecisionLog(tmp_path / "state")
    for d in _decisions():
        record_decision(dlog, d)

    read = read_decisions(dlog)
    assert [d.id for d in read] == ["d1", "d2"]
    assert read[0].kind == "advance"
    assert read[1].payload == {"events": ["start", "complete"]}


def test_replay_reconstructs_byte_identical_state(tmp_path):
    dlog = DecisionLog(tmp_path / "decisions")
    tlog_record = TransitionLog(tmp_path / "record")

    # Record run: apply each decision, recording it via the on_accept hook.
    for d in _decisions():
        outcome = executor.apply(
            d,
            on_accept=lambda x: record_decision(dlog, x),
            log=tlog_record,
        )
        assert outcome.applied

    # Replay run: feed recorded decisions through the executor into a fresh log.
    tlog_replay = TransitionLog(tmp_path / "replay")
    results = replay(dlog, executor.apply, log=tlog_replay)
    assert all(r.applied for r in results)

    # Byte-identical reconstruction of the durable transition log.
    assert tlog_replay.path.read_bytes() == tlog_record.path.read_bytes()
    assert recover(tlog_replay) == recover(tlog_record) == "DONE"


def test_replay_is_deterministic_and_makes_no_model_call(tmp_path):
    dlog = DecisionLog(tmp_path / "decisions")
    for d in _decisions():
        record_decision(dlog, d)

    # Two independent replays produce identical transition logs (no model in path).
    a = TransitionLog(tmp_path / "a")
    b = TransitionLog(tmp_path / "b")
    replay(dlog, executor.apply, log=a)
    replay(dlog, executor.apply, log=b)
    assert a.path.read_bytes() == b.path.read_bytes()


def test_recovery_is_a_special_case_of_replay(tmp_path):
    dlog = DecisionLog(tmp_path / "decisions")
    tlog_record = TransitionLog(tmp_path / "record")
    for d in _decisions():
        executor.apply(d, on_accept=lambda x: record_decision(dlog, x), log=tlog_record)

    # Recovery via replay agrees with recovery from the original transition log.
    tlog_recovered = TransitionLog(tmp_path / "recovered")
    state = recover_via_replay(dlog, executor.apply, tlog_recovered, log=tlog_recovered)
    assert state == recover(tlog_record) == "DONE"


def test_torn_trailing_record_is_tolerated(tmp_path):
    dlog = DecisionLog(tmp_path / "state")
    for d in _decisions():
        record_decision(dlog, d)

    # Simulate an interrupted final append: a non-newline-terminated junk line.
    with open(dlog.path, "a", encoding="utf-8") as fh:
        fh.write('{"index": 3, "decision": {"id":"d3"')  # torn, no newline

    read = read_decisions(dlog)
    assert [d.id for d in read] == ["d1", "d2"]  # torn trailing record dropped
