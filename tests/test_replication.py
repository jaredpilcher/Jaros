"""Tests for log replication across nodes (EXT-002 / REQ-5)."""

from __future__ import annotations

from jaros.state.log import LogEntry, TransitionLog
from jaros.state.recover import recover
from jaros.state.replication import ReplicatedLog


def _mk(tmp_path, name):
    return TransitionLog(tmp_path / name, "t.log")


def _entry(index, event, state):
    return LogEntry.make(index=index, event=event, state=state)


def test_append_mirrors_to_every_replica(tmp_path):
    primary = _mk(tmp_path, "a")
    r1 = _mk(tmp_path, "b")
    r2 = _mk(tmp_path, "c")
    rep = ReplicatedLog(primary, [r1, r2])
    rep.ensure()

    rep.append(_entry(1, "start", "RUNNING"))
    rep.append(_entry(2, "complete", "DONE"))

    for log in (primary, r1, r2):
        entries = list(log.read())
        assert [e.index for e in entries] == [1, 2]
        assert [e.state for e in entries] == ["RUNNING", "DONE"]
    assert rep.has_converged()
    assert rep.converged_prefix() == 2


def test_single_replica_loss_loses_nothing(tmp_path):
    primary = _mk(tmp_path, "a")
    r1 = _mk(tmp_path, "b")
    rep = ReplicatedLog(primary, [r1])
    rep.ensure()
    rep.append(_entry(1, "start", "RUNNING"))
    rep.append(_entry(2, "complete", "DONE"))

    # Lose the primary node entirely (delete its log dir contents).
    primary.path.unlink()
    assert primary.length() == 0

    # The surviving replica still holds every committed transition.
    assert recover(r1) == "DONE"
    assert [e.index for e in r1.read()] == [1, 2]


def test_reconcile_brings_lagging_replica_into_convergence(tmp_path):
    primary = _mk(tmp_path, "a")
    r1 = _mk(tmp_path, "b")
    rep = ReplicatedLog(primary, [r1])
    rep.ensure()
    rep.append(_entry(1, "start", "RUNNING"))

    # Simulate r1 being the lost node that missed later appends: write directly
    # to the primary only.
    primary.append(_entry(2, "complete", "DONE"))
    assert not rep.has_converged()
    assert rep.converged_prefix() == 1

    rep.reconcile()

    assert rep.has_converged()
    assert [e.index for e in r1.read()] == [1, 2]
    assert recover(r1) == "DONE"


def test_no_replicas_trivially_converged(tmp_path):
    primary = _mk(tmp_path, "a")
    rep = ReplicatedLog(primary)
    rep.ensure()
    rep.append(_entry(1, "start", "RUNNING"))
    assert rep.has_converged()
    assert rep.converged_prefix() == 1
