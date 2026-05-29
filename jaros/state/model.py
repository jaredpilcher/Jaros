"""Explicit state and transition model (EXT-002 / REQ-1).

This module is the *single source of truth* for the distributed state machine.
The full set of states, the full set of events, the initial state, and the
allowed ``(state, event) -> nextState`` transitions are declared here — never
inferred or scattered across application logic. Every component that needs to
know "what comes next" reads from this table; nothing computes transitions on
its own.

The model is introspectable: :func:`list_transitions` dumps the table as a flat,
deterministically-ordered list of ``(from, event, to)`` triples suitable for
visualisation or assertion.
"""

from __future__ import annotations

# #EXT-002-REQ-1 Start
#: Every declared state. The machine may never enter a state outside this set.
STATES: tuple[str, ...] = (
    "PENDING",
    "RUNNING",
    "BLOCKED",
    "DONE",
    "FAILED",
)

#: Every declared event that can drive a transition.
EVENTS: tuple[str, ...] = (
    "start",
    "block",
    "unblock",
    "complete",
    "fail",
    "reset",
)

#: The state a fresh machine begins in.
INITIAL_STATE: str = "PENDING"

#: The single source of truth: ``TRANSITIONS[state][event] -> next_state``.
#: A ``(state, event)`` pair is permitted if and only if it appears here.
TRANSITIONS: dict[str, dict[str, str]] = {
    "PENDING": {
        "start": "RUNNING",
        "fail": "FAILED",
    },
    "RUNNING": {
        "block": "BLOCKED",
        "complete": "DONE",
        "fail": "FAILED",
    },
    "BLOCKED": {
        "unblock": "RUNNING",
        "fail": "FAILED",
    },
    "FAILED": {
        "reset": "PENDING",
    },
    "DONE": {},
}


def is_state(state: object) -> bool:
    """Return ``True`` iff ``state`` is one of the declared :data:`STATES`."""
    return isinstance(state, str) and state in STATES


def is_event(event: object) -> bool:
    """Return ``True`` iff ``event`` is one of the declared :data:`EVENTS`."""
    return isinstance(event, str) and event in EVENTS


def list_transitions() -> list[tuple[str, str, str]]:
    """Dump the transition table as ``(from, event, to)`` triples.

    Ordering is deterministic: states in :data:`STATES` declaration order, then
    events in :data:`EVENTS` declaration order. Suitable for visualisation,
    diffing, and test assertions.
    """
    triples: list[tuple[str, str, str]] = []
    for state in STATES:
        events = TRANSITIONS.get(state, {})
        for event in EVENTS:
            if event in events:
                triples.append((state, event, events[event]))
    return triples
# #EXT-002-REQ-1 End
