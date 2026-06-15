"""Swarm member: ``reviewer`` — reviews the drafted reply and finalizes.

Calls the node's LLM (via the one ``LlmClient`` interface) to review the reply,
then emits an inert ``advance`` Decision finalizing the ticket. Its ``source``
("reviewer") is recorded with the decision, so the swarm stays attributable.
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision
from jaros.llm import LlmRequest

KIND = "reviewer"


class ReviewerBoundary:
    def __init__(self, llm) -> None:
        self._llm = llm

    def decide(self, context) -> list:
        ticket = context.get("ticket", "") if isinstance(context, dict) else str(context)
        review = self._llm.complete(LlmRequest(prompt=f"review the reply for: {ticket}")).text
        return [create_decision(
            id=f"rev-{uuid.uuid4().hex}",
            source=KIND,
            kind="advance",
            payload={"events": ["start", "complete"], "note": f"review: {review[:60]}"},
        )]


def build(llm) -> ReviewerBoundary:
    return ReviewerBoundary(llm)
