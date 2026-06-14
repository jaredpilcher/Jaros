"""The Architectural Harness: mediation + rule validation (EXT-005 / REQ-1,2,5).

The harness is the unyielding mediator every agent runs inside. Agents hold no
ambient power; the only way an agent causes a side effect is by handing the
harness an *action* via :meth:`Harness.request`. The harness validates that
action against its architecturally-defined rules and performs it **only** via
the capability handles it granted that agent.

Guarantees:

- **Mediation (REQ-1)**: every side effect flows through :meth:`request`, which
  validates before acting. Disallowed actions are refused and recorded with no
  effect.
- **Non-bypassable / fail-closed (REQ-2)**: unknown action types, actions the
  agent lacks the capability for, or unknown agents are denied by default. The
  rule set is frozen at construction; there is no agent-reachable mutation path.
- **Capability scoping (REQ-3)**: :meth:`spawn` hands an agent only its
  :class:`~jaros.harness.capabilities.Grants` — no global queue/fs/network refs.
  :meth:`teardown` revokes them.
- **Developer-configurable (REQ-5)**: ``Harness(rules=...)`` accepts an override
  rule set at boot; absent one, the built-in defaults apply. The result is
  frozen after construction.

Security boundary (REQ-6): the harness's default-deny mediation and capability
scoping are **structural least-privilege** and auditability properties — not an
adversarial sandbox. Isolation against hostile code is delegated to the host
(process, container, VPC).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jaros.harness.capabilities import (
    Capability,
    FsRead,
    FsWrite,
    Grants,
    GrantSpec,
    QueueReceive,
    QueueSend,
    grant,
    revoke,
)
from jaros.harness.rules import (
    DEFAULT_RULES,
    describe_rules as _describe_rules,
    freeze_rules,
)


# #EXT-005-REQ-1 Start
@dataclass(frozen=True, slots=True)
class Action:
    """An inert request to perform one harness-mediated side effect.

    ``type`` names the action (e.g. ``"fs.write"``); the remaining fields carry
    the action's arguments. Agents construct these; they never perform the
    effect themselves.
    """

    type: str
    path: str | None = None
    data: str | None = None
    message: Any = None


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Outcome of a mediated :meth:`Harness.request`.

    ``allowed`` is ``True`` only if the action passed validation and was
    performed. On denial, ``allowed`` is ``False``, ``value`` is ``None`` and
    ``reason`` explains the refusal. No side effect occurs on denial.
    """

    allowed: bool
    value: Any = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AgentContext:
    """What an agent receives from :meth:`Harness.spawn`.

    It carries the agent's id and *only* its granted handles — no reference to
    the harness's global queues, file system, network, or other agents.
    """

    agent_id: str
    grants: Grants
# #EXT-005-REQ-1 End


# #EXT-005-REQ-2 Start
class Harness:
    """Mediates and validates every agent action; rules are not agent-mutable."""

    def __init__(
        self,
        rules: Mapping[str, type[Capability]] | None = None,
        audit_path: str | "Path | None" = None,
    ) -> None:
        """Construct the harness.

        Args:
            rules: Optional rule set (action type -> required capability) to use
                instead of / in addition to the built-in defaults. When omitted,
                the built-in :data:`~jaros.harness.rules.DEFAULT_RULES` apply.
                Provided rules override defaults per action type, and may add new
                action types or tighten existing ones (REQ-5).
            audit_path: Optional path to a durable, append-only audit log. When
                set, every mediated action (allowed and denied) is recorded there
                (REQ-7) — the auditable record the Prime Directive demands (P2).

        The effective rule set is deep-frozen after construction; there is no
        agent-reachable API to mutate it at runtime.
        """
        # #EXT-005-REQ-5 Start
        effective: dict[str, type[Capability]] = dict(DEFAULT_RULES)
        if rules is not None:
            effective.update(rules)
        # Frozen snapshot — the canonical, agent-immutable active rule set.
        self._rules: Mapping[str, type[Capability]] = freeze_rules(effective)
        # #EXT-005-REQ-5 End

        self._grants: dict[str, Grants] = {}
        self._denied: list[tuple[str, str, str]] = []  # (agent_id, action_type, reason)
        self._audit_path: Path | None = Path(audit_path) if audit_path else None

    # -- lifecycle ----------------------------------------------------------

    def spawn(self, agent_id: str, grant_spec: GrantSpec) -> AgentContext:
        """Register an agent and hand it ONLY its granted handles.

        Returns an :class:`AgentContext` containing the agent's
        :class:`~jaros.harness.capabilities.Grants` and nothing else — no global
        queue/fs/network references.
        """
        grants = grant(grant_spec)
        self._grants[agent_id] = grants
        return AgentContext(agent_id=agent_id, grants=grants)

    def teardown(self, agent_id: str) -> None:
        """Revoke the agent's capabilities and forget it. Idempotent."""
        grants = self._grants.pop(agent_id, None)
        if grants is not None:
            revoke(grants)

    # -- mediation ----------------------------------------------------------

    def request(self, agent_id: str, action: Action) -> ActionResult:
        """Validate ``action`` against the active rules and perform it if allowed.

        Default-deny: an unknown agent, an unknown action type, or an action the
        agent lacks the required capability handle for is refused and recorded,
        with no side effect.
        """
        grants = self._grants.get(agent_id)
        if grants is None:
            return self._deny(agent_id, action.type, "unknown agent")
        if grants.revoked:
            return self._deny(agent_id, action.type, "agent capabilities revoked")

        required = self._rules.get(action.type)
        if required is None:
            # Unknown / disallowed action type -> fail closed.
            return self._deny(agent_id, action.type, "no rule permits this action")

        # Resolve the granted handle for the required capability. If the agent
        # was not granted it, deny — no side effect.
        try:
            result = self._perform(agent_id, action, required, grants)
            self._audit(agent_id, action.type, True, None)
            return result
        except _CapabilityNotGranted as exc:
            return self._deny(agent_id, action.type, str(exc))

    def _perform(
        self,
        agent_id: str,
        action: Action,
        required: type[Capability],
        grants: Grants,
    ) -> ActionResult:
        if required is QueueSend:
            handle = grants.queue_send
            if handle is None:
                raise _CapabilityNotGranted("agent lacks QueueSend capability")
            handle.send(action.message)
            return ActionResult(allowed=True, value=None)
        if required is QueueReceive:
            handle = grants.queue_receive
            if handle is None:
                raise _CapabilityNotGranted("agent lacks QueueReceive capability")
            return ActionResult(allowed=True, value=handle.receive())
        if required is FsWrite:
            handle = grants.fs_write
            if handle is None:
                raise _CapabilityNotGranted("agent lacks FsWrite capability")
            handle.write(action.path, action.data)  # type: ignore[arg-type]
            return ActionResult(allowed=True, value=None)
        if required is FsRead:
            handle = grants.fs_read
            if handle is None:
                raise _CapabilityNotGranted("agent lacks FsRead capability")
            return ActionResult(allowed=True, value=handle.read(action.path))  # type: ignore[arg-type]
        # A rule referenced a capability the harness cannot perform -> fail closed.
        raise _CapabilityNotGranted(
            f"no handler for required capability {required.__name__}"
        )

    def _deny(self, agent_id: str, action_type: str, reason: str) -> ActionResult:
        self._denied.append((agent_id, action_type, reason))
        self._audit(agent_id, action_type, False, reason)
        return ActionResult(allowed=False, value=None, reason=reason)

    # -- audit --------------------------------------------------------------

    # #EXT-005-REQ-7 Start
    def _audit(self, agent_id: str, action_type: str, allowed: bool, reason: str | None) -> None:
        """Append one durable audit record for a mediated action (allowed/denied).

        Best-effort and append-only: a failure to write the audit log must never
        break mediation. No-op when no ``audit_path`` was configured.
        """
        if self._audit_path is None:
            return
        entry = {
            "ts": round(time.time(), 3),
            "agent": agent_id,
            "action": action_type,
            "allowed": allowed,
            "reason": reason,
        }
        try:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._audit_path, "a", encoding="utf-8", newline="") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
        except OSError:
            pass
    # #EXT-005-REQ-7 End

    def describe_rules(self) -> Mapping[str, str]:
        """Return an immutable snapshot of the active configured rule set."""
        return _describe_rules(self._rules)

    @property
    def denied(self) -> tuple[tuple[str, str, str], ...]:
        """Immutable record of refused actions, for audit/tests."""
        return tuple(self._denied)


# #EXT-005-REQ-7 Start
def read_audit(audit_path: str | Path) -> list[dict[str, Any]]:
    """Read the durable harness audit log (newline-delimited JSON), in order.

    Tolerates a torn trailing line; returns an empty list when the log is absent.
    """
    path = Path(audit_path)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
# #EXT-005-REQ-7 End


class _CapabilityNotGranted(Exception):
    """Internal: the agent does not hold the capability a rule requires."""
# #EXT-005-REQ-2 End
