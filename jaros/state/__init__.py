"""Distributed State Machine (EXT-002).

An explicitly-modeled, durable, distributed state machine: all system progress
is a sequence of validated transitions, each durably logged before it is
observable, recoverable by replay, and replicated to survive node loss.

- :mod:`jaros.state.model` — the single source of truth for states/transitions.
- :mod:`jaros.state.machine` — transition enforcement and atomic commit.
- :mod:`jaros.state.log` — durable, append-only transition log.
- :mod:`jaros.state.recover` — crash recovery by deterministic replay.
- :mod:`jaros.state.replication` — mirror-before-ack log replication.
"""

from __future__ import annotations

from jaros.state.log import LogEntry, TransitionLog
from jaros.state.machine import (
    CommitResult,
    InvalidStateError,
    UndefinedTransitionError,
    assert_valid_state,
    commit,
    transition,
)
from jaros.state.model import (
    EVENTS,
    INITIAL_STATE,
    STATES,
    TRANSITIONS,
    is_event,
    is_state,
    list_transitions,
)
from jaros.state.recover import RecoveryError, recover
from jaros.state.replication import ReplicatedLog, ReplicationError

__all__ = [
    # model
    "STATES",
    "EVENTS",
    "INITIAL_STATE",
    "TRANSITIONS",
    "is_state",
    "is_event",
    "list_transitions",
    # machine
    "transition",
    "assert_valid_state",
    "commit",
    "CommitResult",
    "UndefinedTransitionError",
    "InvalidStateError",
    # log
    "TransitionLog",
    "LogEntry",
    # recover
    "recover",
    "RecoveryError",
    # replication
    "ReplicatedLog",
    "ReplicationError",
]
