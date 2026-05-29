"""Tests for the explicit state/transition model (EXT-002 / REQ-1)."""

from __future__ import annotations

from jaros.state.model import (
    EVENTS,
    INITIAL_STATE,
    STATES,
    TRANSITIONS,
    is_event,
    is_state,
    list_transitions,
)


def test_initial_state_is_declared():
    assert INITIAL_STATE in STATES


def test_transition_table_only_references_declared_states_and_events():
    # Every transition's from-state, event, and to-state must be declared.
    for from_state, events in TRANSITIONS.items():
        assert from_state in STATES
        for event, to_state in events.items():
            assert event in EVENTS, f"undeclared event {event!r}"
            # No transition may lead to an undeclared state.
            assert to_state in STATES, f"transition to undeclared state {to_state!r}"


def test_every_state_has_a_transition_entry():
    # The table is the single source of truth: every state appears in it.
    for state in STATES:
        assert state in TRANSITIONS


def test_is_state_and_is_event_guards():
    assert is_state("PENDING")
    assert not is_state("NOPE")
    assert not is_state(None)
    assert is_event("start")
    assert not is_event("explode")
    assert not is_event(42)


def test_list_transitions_is_deterministic_and_complete():
    triples = list_transitions()
    # Each declared transition appears exactly once as a (from, event, to) triple.
    expected = {
        (s, e, t)
        for s, events in TRANSITIONS.items()
        for e, t in events.items()
    }
    assert set(triples) == expected
    assert len(triples) == len(expected)
    # Deterministic ordering: stable across repeated calls.
    assert triples == list_transitions()
