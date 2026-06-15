"""Swarm member: ``planner`` — classifies an incoming support ticket.

Part of the EXT-015 swarm reference demo (a support-ticket triage hive:
planner -> worker -> reviewer). The planner calls the node's LLM through the one
``LlmClient`` interface (whatever provider config selects — a deterministic mock
by default, a real small model via ``ollama``) to decide *what* the plan is, then
emits an inert ``advance`` Decision carrying that plan as data. It performs no
side effect; its ``source`` ("planner") is recorded with the decision so the
whole swarm is attributable.
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision
from jaros.llm import LlmRequest

KIND = "planner"


class PlannerBoundary:
    def __init__(self, llm) -> None:
        self._llm = llm

    def decide(self, context) -> list:
        ticket = context.get("ticket", "") if isinstance(context, dict) else str(context)
        plan = self._llm.complete(LlmRequest(prompt=f"classify support ticket: {ticket}")).text
        return [create_decision(
            id=f"plan-{uuid.uuid4().hex}",
            source=KIND,
            kind="advance",
            payload={"events": ["start", "complete"], "note": f"plan: {plan[:60]}"},
        )]


def build(llm) -> PlannerBoundary:
    return PlannerBoundary(llm)
