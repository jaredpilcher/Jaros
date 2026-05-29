"""Tests for the bounded concurrent agent pool (EXT-003 / REQ-2, REQ-4).

Covers: the pool never exceeds its bound (backpressure queues excess spawns),
active agents and states are observable via snapshot, a peer failure is reported
and contained while siblings keep running, and drain reaps everything.
"""

from __future__ import annotations

import threading

from jaros.runtime.agent_pool import AgentPool
from jaros.runtime.agent_thread import AgentThread
from jaros.runtime.lifecycle import AgentState


def _gated_agent(agent_id: str, gate: threading.Event, started: threading.Event):
    """Build a factory whose agent blocks on ``gate`` after signalling start."""

    def body():
        started.set()
        gate.wait(timeout=5)

    def factory():
        return AgentThread.spawn(agent_id, body)

    return factory


def test_pool_respects_bound_with_backpressure():
    bound = 2
    pool = AgentPool(bound=bound)
    gate = threading.Event()
    started = [threading.Event() for _ in range(5)]

    for i in range(5):
        pool.submit(_gated_agent(f"a{i}", gate, started[i]))

    # Wait for the first `bound` agents to actually be running.
    for ev in started[:bound]:
        assert ev.wait(timeout=5)

    # Never more than `bound` running concurrently; the rest are queued.
    assert len(pool.active()) == bound
    assert pool.pending == 5 - bound
    # Queued agents have not started.
    assert not started[bound].is_set()

    # Release the gate; backpressure drains as slots free.
    gate.set()
    pool.drain()

    assert len(pool.active()) == 0
    assert pool.pending == 0
    states = {s.id: s.state for s in pool.snapshot()}
    assert len(states) == 5
    assert all(st is AgentState.TORNDOWN for st in states.values())


def test_snapshot_lists_active_agents_and_states():
    pool = AgentPool(bound=3)
    gate = threading.Event()
    started = [threading.Event() for _ in range(3)]

    for i in range(3):
        pool.submit(_gated_agent(f"s{i}", gate, started[i]))
    for ev in started:
        assert ev.wait(timeout=5)

    snap = {s.id: s.state for s in pool.snapshot()}
    assert set(snap) == {"s0", "s1", "s2"}
    assert all(st is AgentState.RUNNING for st in snap.values())

    gate.set()
    pool.drain()


def test_peer_failure_is_contained_and_siblings_keep_running():
    failures: list[tuple[str, str]] = []
    pool = AgentPool(
        bound=3,
        on_agent_failed=lambda a, exc: failures.append((a.id, str(exc))),
    )

    sibling_gate = threading.Event()
    sibling_started = threading.Event()
    sibling_done = threading.Event()

    def failing_factory():
        def body():
            raise RuntimeError("peer boom")

        return AgentThread.spawn("bad", body)

    def sibling_factory():
        def body():
            sibling_started.set()
            sibling_gate.wait(timeout=5)
            sibling_done.set()

        return AgentThread.spawn("good", body)

    pool.submit(sibling_factory)
    assert sibling_started.wait(timeout=5)
    pool.submit(failing_factory)

    # The failure is reported via on_agent_failed; process clearly survives.
    # Wait (bounded) for the failed agent to run and be reaped.
    for _ in range(500):
        if failures:
            break
        threading.Event().wait(0.01)

    assert failures == [("bad", "peer boom")]
    # Sibling is unaffected and still running (it is blocked on its gate).
    assert sibling_started.is_set()
    assert not sibling_done.is_set()
    assert "good" in {a.id for a in pool.active()}

    # Now let the sibling finish and drain.
    sibling_gate.set()
    pool.drain()
    assert sibling_done.is_set()

    states = {s.id: s.state for s in pool.snapshot()}
    assert states["bad"] is AgentState.FAILED
    assert states["good"] is AgentState.TORNDOWN


def test_invalid_bound_rejected():
    import pytest

    with pytest.raises(ValueError):
        AgentPool(bound=0)
