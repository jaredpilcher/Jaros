"""Swarm member: ``worker`` — drafts a reply and hands it off to the reviewer.

Calls the node's LLM (via the one ``LlmClient`` interface) to draft a reply, then
emits a ``swarm.handoff`` Decision carrying the draft to the reviewer (the
matching tool is ``examples/swarm/tools/handoff_tool.py``). Submitting a job with
``{"bad": true}`` seeds a **bad handoff** (``ok: false``): the handoff is recorded
(it is structurally valid data) but the reviewer tool rejects it on execution — so
swarm replay attributes the failure to the exact worker that produced it.
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision
from jaros.llm import LlmRequest

KIND = "worker"


class WorkerBoundary:
    def __init__(self, llm) -> None:
        self._llm = llm

    def decide(self, context) -> list:
        ctx = context if isinstance(context, dict) else {}
        ticket = ctx.get("ticket", "")
        draft = self._llm.complete(LlmRequest(prompt=f"draft a reply to: {ticket}")).text
        ok = not bool(ctx.get("bad", False))  # {"bad": true} seeds a bad handoff
        return [create_decision(
            id=f"work-{uuid.uuid4().hex}",
            source=KIND,
            kind="swarm.handoff",
            payload={"draft": draft[:80], "ok": ok},
        )]


def build(llm) -> WorkerBoundary:
    return WorkerBoundary(llm)
