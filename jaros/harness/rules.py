"""Architecturally-defined rule set for the harness (EXT-005 / REQ-4).

Rules map an *action type* (e.g. ``"fs.write"``, ``"queue.send"``) to the
capability the requesting agent must hold for that action to be permitted. The
rule set is declared here, in the harness layer — never supplied or negotiated
by agents. It is deep-frozen at import so there is no agent-facing mutation API.

Changing a rule is a harness-side source change, reviewable independently of any
agent. :func:`describe_rules` returns an immutable snapshot for audit.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from jaros.harness.capabilities import (
    Capability,
    FsRead,
    FsWrite,
    QueueReceive,
    QueueSend,
)

# #EXT-005-REQ-4 Start
#: Canonical action types the harness understands.
ACTION_QUEUE_SEND = "queue.send"
ACTION_QUEUE_RECEIVE = "queue.receive"
ACTION_FS_WRITE = "fs.write"
ACTION_FS_READ = "fs.read"


# The default rule set: action type -> required capability kind. Declared as
# code, deep-frozen below so it cannot be mutated at runtime by anyone.
_DEFAULT_RULES: dict[str, type[Capability]] = {
    ACTION_QUEUE_SEND: QueueSend,
    ACTION_QUEUE_RECEIVE: QueueReceive,
    ACTION_FS_WRITE: FsWrite,
    ACTION_FS_READ: FsRead,
}

#: The active default rule set, deep-frozen (read-only mapping) at import time.
DEFAULT_RULES: Mapping[str, type[Capability]] = MappingProxyType(dict(_DEFAULT_RULES))


def freeze_rules(rules: Mapping[str, type[Capability]]) -> Mapping[str, type[Capability]]:
    """Return a deep-frozen, read-only snapshot of ``rules``.

    The returned mapping is a :class:`~types.MappingProxyType` over a private
    copy, so the caller cannot mutate the rules through the returned object nor
    through the dict that was passed in.
    """
    return MappingProxyType(dict(rules))


def describe_rules(
    rules: Mapping[str, type[Capability]] | None = None,
) -> Mapping[str, str]:
    """Return an immutable, audit-friendly snapshot of the active rule set.

    Maps each action type to the *name* of its required capability. If ``rules``
    is omitted, the built-in :data:`DEFAULT_RULES` are described.
    """
    src = DEFAULT_RULES if rules is None else rules
    return MappingProxyType(
        {action: cap.__name__ for action, cap in src.items()}
    )
# #EXT-005-REQ-4 End
