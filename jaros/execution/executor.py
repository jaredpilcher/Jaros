"""The deterministic executor (EXT-001 / REQ-4, REQ-6, REQ-7).

The executor is the only thing that acts on a Decision, and only after the gate
accepts it. It dispatches an accepted decision to a handler registered for the
decision's ``kind``; unknown kinds are refused with a reason and cause no side
effect. This module MUST NOT import ``jaros.llm`` or ``reasoning_boundary`` —
the boundary is enforced structurally by ``scripts/check_planes.py``.

The accepted decision is the *sole* replayable non-deterministic input to a run
(EXT-001 / REQ-7): :func:`apply` surfaces it on :class:`ExecutionResult` and
offers an ``on_accept`` hook that fires after the gate accepts and **before** the
handler runs, so the durable decision log (EXT-002 / REQ-6) can record each
accepted decision before its effects are observable. ``apply`` performs no model
call, so a run can be re-executed from recorded decisions alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from jaros.core.decision import Decision
from jaros.core.decision_gate import validate_decision

logger = logging.getLogger(__name__)


# #EXT-001-REQ-4 Start
@dataclass(frozen=True)
class ExecutionResult:
    """Outcome of an :func:`apply` call.

    Attributes:
        applied: True iff a handler ran and acted on the decision.
        reason: Why the decision was refused (None when ``applied`` is True).
        output: Whatever the handler returned (None when not applied).
    """

    applied: bool
    reason: str | None = None
    output: Any = None
    # The gate-accepted decision (EXT-001 / REQ-7), surfaced so a caller can
    # record it durably for replay. None when the decision was refused.
    accepted: "Decision | None" = None
# #EXT-001-REQ-4 End


# #EXT-001-REQ-6 Start
# A handler is a deterministic function of the validated decision plus
# execution-plane collaborators (state machine, granted handles). It is never
# given the LLM/reasoning side.
Handler = Callable[..., Any]

_handlers: dict[str, Handler] = {}


def register_handler(kind: str, fn: Handler) -> Handler:
    """Register the handler that the executor dispatches to for ``kind``.

    Returns ``fn`` so it may also be used as a decorator factory's target.
    """
    _handlers[kind] = fn
    return fn


def reset_handlers() -> None:
    """Clear all registered handlers. Intended for test isolation."""
    _handlers.clear()


def apply(
    d: Decision,
    *,
    on_accept: "Callable[[Decision], None] | None" = None,
    **collaborators: Any,
) -> ExecutionResult:
    """Validate ``d`` via the gate, then dispatch to its ``kind`` handler.

    On gate rejection the reason is logged and a non-applied result is returned
    with no state mutation. If the decision's ``kind`` has no registered handler
    the decision is refused with a clear reason and no side effect. Otherwise the
    handler is invoked with the validated decision and any execution-plane
    ``collaborators`` (state machine, granted handles) — never the reasoning side.

    ``on_accept`` (EXT-001 / REQ-7) fires once with the gate-accepted decision
    *before* the handler runs, so a caller can durably record it for replay
    (EXT-002 / REQ-6) before its effects are observable. The accepted decision is
    also surfaced on the returned :class:`ExecutionResult`.
    """
    result = validate_decision(d)
    if not result.ok:
        logger.warning("decision %r rejected by gate: %s", getattr(d, "id", "?"), result.reason)
        return ExecutionResult(applied=False, reason=result.reason)

    validated = result.value
    assert validated is not None

    handler = _handlers.get(validated.kind)
    if handler is None:
        reason = f"no handler registered for kind {validated.kind!r}"
        logger.warning("decision %r refused: %s", validated.id, reason)
        return ExecutionResult(applied=False, reason=reason, accepted=validated)

    # Record the accepted decision durably before any effect is observable.
    if on_accept is not None:
        on_accept(validated)

    output = handler(validated, **collaborators)
    return ExecutionResult(applied=True, output=output, accepted=validated)
# #EXT-001-REQ-6 End
