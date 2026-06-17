"""Example agent: ``echo``.

Drop this file into the shared-FS ``agents/`` folder; the daemon imports and
registers it at runtime with no restart (EXT-007 / REQ-3). The agent reasons
(here, trivially) and emits a single inert ``advance`` Decision that drives a
job PENDING -> RUNNING -> DONE, attaching an echoed note from the job input.

An agent module must expose a module-level ``KIND: str`` and a
``build(llm) -> ReasoningBoundary``.
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision


KIND = "echo"


class EchoBoundary:
    """Reasoning boundary whose sole output is inert ``Decision`` data."""

    def __init__(self, llm) -> None:
        self._llm = llm

    def decide(self, context) -> list:
        msg = context.get("msg", "") if isinstance(context, dict) else ""
        return [
            create_decision(
                id=f"echo-{uuid.uuid4().hex}",
                source="echo",
                kind="advance",
                payload={"events": ["start", "complete"], "note": f"echo: {msg}"},
            )
        ]


def build(llm) -> EchoBoundary:
    return EchoBoundary(llm)
