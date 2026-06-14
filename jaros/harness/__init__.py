"""Architectural Harness (EXT-005).

The unyielding mediator every agent runs inside. The harness — not the agents —
defines and enforces the rules: it grants capability-scoped handles, validates
every action against an architecturally-defined (and developer-configurable)
rule set, and cannot be bypassed or mutated by agents at runtime.
"""

from __future__ import annotations

from jaros.harness.capabilities import (
    Capability,
    CapabilityError,
    FsRead,
    FsReadHandle,
    FsWrite,
    FsWriteHandle,
    Grants,
    GrantSpec,
    QueueReceive,
    QueueReceiveHandle,
    QueueSend,
    QueueSendHandle,
    RevokedCapabilityError,
    grant,
    revoke,
)
from jaros.harness.harness import (
    Action,
    ActionResult,
    AgentContext,
    Harness,
    read_audit,
)
from jaros.harness.rules import DEFAULT_RULES, describe_rules, freeze_rules

__all__ = [
    # capabilities
    "Capability",
    "CapabilityError",
    "RevokedCapabilityError",
    "QueueSend",
    "QueueReceive",
    "FsWrite",
    "FsRead",
    "QueueSendHandle",
    "QueueReceiveHandle",
    "FsWriteHandle",
    "FsReadHandle",
    "GrantSpec",
    "Grants",
    "grant",
    "revoke",
    # rules
    "DEFAULT_RULES",
    "describe_rules",
    "freeze_rules",
    # harness
    "Harness",
    "Action",
    "ActionResult",
    "AgentContext",
    "read_audit",
]
