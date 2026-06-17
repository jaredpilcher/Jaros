"""Durable, Replayable State Machine (EXT-002).

An explicitly-modeled, durable, crash-recoverable, deterministically replayable
state machine: all system progress is a sequence of validated transitions, each
durably logged before it is observable. The durable log records the accepted
decisions, so a run can be re-executed to byte-identical state — recovery is a
special case of replay. Distribution is single-node-first, with bounded
multi-node coordination over the shared file system (no cluster-scale
replication, consensus service, or broker).

- :mod:`jaros.state.model` — the single source of truth for states/transitions.
- :mod:`jaros.state.machine` — transition enforcement and atomic commit.
- :mod:`jaros.state.log` — durable, append-only transition log.
- :mod:`jaros.state.recover` — crash recovery by deterministic replay.
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
from jaros.state.coordination import FileCoordinator
from jaros.state.decision_log import (
    GENESIS_PREV,
    ChainResult,
    DecisionLog,
    DecisionRecord,
    read_decisions,
    record_decision,
    replay,
    verify_chain,
)
from jaros.state.recover import RecoveryError, recover, recover_via_replay
from jaros.state.swarm import (
    AgentTally,
    Attribution,
    SwarmReplayResult,
    attribute,
    replay_swarm,
    summary_by_agent,
)

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
    "recover_via_replay",
    # decision log + replay
    "DecisionLog",
    "DecisionRecord",
    "record_decision",
    "read_decisions",
    "replay",
    # tamper-evident chain (EXT-015)
    "verify_chain",
    "ChainResult",
    "GENESIS_PREV",
    # swarm replay + attribution (EXT-015)
    "replay_swarm",
    "attribute",
    "summary_by_agent",
    "SwarmReplayResult",
    "Attribution",
    "AgentTally",
    # coordination
    "FileCoordinator",
]
