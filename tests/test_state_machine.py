"""Tests for transition enforcement and atomic commit (EXT-002 / REQ-2, REQ-3)."""

from __future__ import annotations

import pytest

from jaros.state.log import TransitionLog
from jaros.state.machine import (
    InvalidStateError,
    UndefinedTransitionError,
    assert_valid_state,
    commit,
    transition,
)
from jaros.state.model import INITIAL_STATE


def test_valid_transition_returns_next_state():
    assert transition("PENDING", "start") == "RUNNING"
    assert transition("RUNNING", "complete") == "DONE"
    assert transition("RUNNING", "block") == "BLOCKED"
    assert transition("BLOCKED", "unblock") == "RUNNING"


def test_transition_never_yields_undeclared_state():
    # Every reachable next-state is a declared state (no transition to undeclared).
    assert_valid_state(transition("PENDING", "start"))
    assert_valid_state(transition("FAILED", "reset"))


def test_undefined_transition_raises_and_does_not_mutate():
    state = "DONE"  # terminal: no events defined
    with pytest.raises(UndefinedTransitionError):
        transition(state, "start")
    # No mutation: the caller's state object is untouched (strings are immutable,
    # but the call must not have returned a new state silently).
    assert state == "DONE"


def test_undefined_event_on_valid_state_raises():
    with pytest.raises(UndefinedTransitionError):
        transition("PENDING", "complete")


def test_assert_valid_state_rejects_undeclared():
    with pytest.raises(InvalidStateError):
        assert_valid_state("GHOST")
    assert assert_valid_state("RUNNING") == "RUNNING"


def test_commit_logs_then_applies(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    result = commit(log, INITIAL_STATE, "start")
    assert result.state == "RUNNING"
    assert result.index == 1
    # The transition was durably logged.
    entries = list(log.read())
    assert len(entries) == 1
    assert entries[0].event == "start"
    assert entries[0].state == "RUNNING"
    assert entries[0].index == 1


def test_commit_rejects_undefined_without_logging(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    with pytest.raises(UndefinedTransitionError):
        commit(log, "PENDING", "complete")
    # Nothing was logged: the rejection happens before any append.
    assert log.length() == 0


def test_commit_not_applied_on_append_failure(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()

    # Force the durable append to fail; commit must not "apply" (i.e. must not
    # return a CommitResult) when the log cannot persist the entry.
    def boom(_entry):
        raise OSError("disk full")

    log.append = boom  # type: ignore[method-assign]

    with pytest.raises(OSError):
        commit(log, "PENDING", "start")
    # The log was never written; nothing observable changed.
    fresh = TransitionLog(tmp_path, "t.log")
    assert fresh.length() == 0
