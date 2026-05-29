"""Transition enforcement and atomic commit (EXT-002 / REQ-2, REQ-3).

The machine permits *only* transitions declared in :mod:`jaros.state.model`.
Any other ``(state, event)`` pair is rejected with a typed
:class:`UndefinedTransitionError` and causes no mutation, so the machine can
never enter an undefined state.

:func:`commit` ties enforcement to durability: it validates the transition,
durably appends it to the log, and *only then* applies it. If the append fails,
the transition is not applied — the commit is atomic (log-then-apply).
"""

from __future__ import annotations

from dataclasses import dataclass

from jaros.state.log import LogEntry, TransitionLog
from jaros.state.model import TRANSITIONS, is_state


# #EXT-002-REQ-2 Start
class UndefinedTransitionError(ValueError):
    """Raised when a ``(state, event)`` pair is not in the transition table.

    The machine performs no mutation when this is raised, preserving the
    invariant that the current state is always a declared state.
    """


class InvalidStateError(ValueError):
    """Raised when a value is not one of the declared states."""


def assert_valid_state(state: str) -> str:
    """Assert ``state`` is a declared state; return it unchanged.

    Used as an entry/exit invariant so the machine can never operate on a state
    outside the model.

    Raises:
        InvalidStateError: if ``state`` is not a declared state.
    """
    if not is_state(state):
        raise InvalidStateError(f"not a declared state: {state!r}")
    return state


def transition(state: str, event: str) -> str:
    """Return the next state for ``(state, event)`` per the model.

    Raises:
        InvalidStateError: if ``state`` is not a declared state.
        UndefinedTransitionError: if no transition is declared for the pair.
            No mutation is performed in this case.
    """
    assert_valid_state(state)
    targets = TRANSITIONS.get(state, {})
    if event not in targets:
        raise UndefinedTransitionError(
            f"no transition for state={state!r} event={event!r}"
        )
    next_state = targets[event]
    # Invariant: the table can only ever point at declared states.
    return assert_valid_state(next_state)
# #EXT-002-REQ-2 End


# #EXT-002-REQ-3 Start
@dataclass(frozen=True)
class CommitResult:
    """The outcome of a successful :func:`commit`.

    ``state`` is the new current state after the transition was durably logged
    and applied; ``index`` is the 1-based position of the appended log entry.
    """

    state: str
    index: int


def commit(log: TransitionLog, state: str, event: str) -> CommitResult:
    """Validate, durably log, then apply a transition — atomically.

    Order of operations (atomic log-then-apply):

    1. Validate the ``(state, event)`` pair against the model. An undefined
       pair raises :class:`UndefinedTransitionError` and nothing is logged or
       applied.
    2. Durably append the resulting transition to ``log`` (flush + fsync).
    3. Only if the append succeeds, return the new state as applied.

    If step 2 raises (e.g. disk/append failure), the exception propagates and
    the transition is *not* applied — the caller's state is unchanged.

    Returns:
        CommitResult: the new state and the appended entry's 1-based index.

    Raises:
        UndefinedTransitionError: for an undefined transition (no mutation).
        Exception: whatever the log's append raises on failure (no mutation).
    """
    # 1. Validate first — undefined pairs never touch the log.
    next_state = transition(state, event)

    # 2. Durably log before applying. The index is 1-based and follows the
    #    current log length.
    index = log.length() + 1
    entry = LogEntry.make(index=index, event=event, state=next_state)
    log.append(entry)  # on failure this raises and we never reach step 3

    # 3. Append succeeded -> the transition is now committed and observable.
    return CommitResult(state=next_state, index=index)
# #EXT-002-REQ-3 End
