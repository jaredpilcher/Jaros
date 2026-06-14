"""Read-only plugin agent: ``system-health``.

Proposes a `sys.info` decision — a host platform snapshot. The agent only emits
inert data; the read happens in the read-only `sys.info` tool. Pair with
`examples/readonly/tools/sys_info_tool.py`.
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision

KIND = "system-health"


class SystemHealthBoundary:
    def __init__(self, llm) -> None:
        self._llm = llm

    def decide(self, context) -> list:
        return [create_decision(
            id=f"health-{uuid.uuid4().hex}",
            source=KIND,
            kind="sys.info",
            payload={},
        )]


def build(llm) -> SystemHealthBoundary:
    return SystemHealthBoundary(llm)
