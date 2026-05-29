"""Tests for crash recovery by log replay (EXT-002 / REQ-4)."""

from __future__ import annotations

import pytest

from jaros.state.log import LogEntry, TransitionLog
from jaros.state.machine import commit
from jaros.state.model import INITIAL_STATE
from jaros.state.recover import RecoveryError, recover


def test_recover_empty_log_yields_initial_state(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    assert recover(log) == INITIAL_STATE


def test_recover_rebuilds_pre_crash_state(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    state = INITIAL_STATE
    for event in ("start", "block", "unblock", "complete"):
        state = commit(log, state, event).state
    assert state == "DONE"

    # Simulate a crash + restart: a fresh handle replays the durable log.
    recovered = recover(TransitionLog(tmp_path, "t.log"))
    assert recovered == "DONE"
    assert recovered == state  # post-recovery == pre-crash


def test_recover_discards_torn_trailing_entry(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    state = commit(log, INITIAL_STATE, "start").state  # RUNNING
    assert state == "RUNNING"

    # Interrupted commit: a partial final line written but never completed.
    with open(log.path, "a", encoding="utf-8") as fh:
        fh.write('{"index": 2, "event": "comp')  # torn

    # Recovery yields the consistent pre-crash state, not a torn one.
    assert recover(TransitionLog(tmp_path, "t.log")) == "RUNNING"


def test_recover_discards_trailing_entry_with_bad_checksum(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    commit(log, INITIAL_STATE, "start")  # index 1 -> RUNNING

    # Append a complete-but-corrupt trailing entry (checksum mismatch).
    bad = LogEntry(index=2, event="complete", state="DONE", checksum="deadbeef")
    log.append(bad)

    # The corrupt trailing entry is discarded; pre-crash state is restored.
    assert recover(TransitionLog(tmp_path, "t.log")) == "RUNNING"


def test_recover_raises_on_corruption_before_trailing_entry(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    # An index discontinuity in the *middle* (entry 2 missing) is not a torn
    # tail and must not be silently swallowed.
    log.append(LogEntry.make(1, "start", "RUNNING"))
    log.append(LogEntry.make(3, "complete", "DONE"))  # gap: index 2 missing
    log.append(LogEntry.make(4, "fail", "FAILED"))

    with pytest.raises(RecoveryError):
        recover(TransitionLog(tmp_path, "t.log"))
