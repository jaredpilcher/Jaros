"""Tests for the lightweight agent thread (EXT-003 / REQ-1, REQ-4).

Covers the cheap spawn/run/teardown lifecycle and fault containment: a throwing
agent is contained (the process survives), ends ``failed`` with the error
recorded, and fires its ``on_failed`` hook.
"""

from __future__ import annotations

import threading

from jaros.core.decision import create_decision
from jaros.runtime.agent_thread import AgentThread
from jaros.runtime.lifecycle import AgentState, RunnableAgent


def test_spawn_allocates_only_a_thread_no_service():
    agent = AgentThread.spawn("a1", lambda: None)

    assert agent.id == "a1"
    assert agent.state is AgentState.SPAWNED
    # Spawning allocates only an in-process thread — and it is not yet running.
    assert isinstance(agent._thread, threading.Thread)
    assert not agent._thread.is_alive()
    # Structural conformance to the runtime interface.
    assert isinstance(agent, RunnableAgent)


def test_run_executes_body_once_and_captures_decisions():
    calls: list[int] = []

    def body():
        calls.append(1)
        return [create_decision(id="d1", source="a1", type="noop", payload={})]

    agent = AgentThread.spawn("a1", body)
    agent.start()
    agent.teardown()

    assert calls == [1]
    assert agent.state is AgentState.TORNDOWN
    assert [d.id for d in agent.decisions] == ["d1"]


def test_teardown_is_idempotent_and_deterministic():
    agent = AgentThread.spawn("a1", lambda: None)
    agent.start()
    agent.teardown()
    first_state = agent.state
    # Calling teardown repeatedly is safe and does not change the outcome.
    agent.teardown()
    agent.teardown()

    assert first_state is AgentState.TORNDOWN
    assert agent.state is AgentState.TORNDOWN
    assert agent._thread is None


def test_unhandled_exception_is_contained_and_reported():
    fired: list[tuple[str, str]] = []

    def on_failed(a, exc):
        fired.append((a.id, str(exc)))

    def boom():
        raise RuntimeError("kaboom")

    agent = AgentThread.spawn("bad", boom, on_failed=on_failed)
    agent.start()
    agent.teardown()

    # The process clearly survived (we are still executing); agent is failed.
    assert agent.state is AgentState.FAILED
    assert isinstance(agent.error, RuntimeError)
    assert str(agent.error) == "kaboom"
    assert fired == [("bad", "kaboom")]


def test_failed_state_is_preserved_through_teardown():
    def boom():
        raise ValueError("x")

    agent = AgentThread.spawn("bad", boom)
    agent.start()
    agent.teardown()

    # Teardown reaps but must not mask the terminal failure outcome.
    assert agent.state is AgentState.FAILED
    assert agent._thread is None
