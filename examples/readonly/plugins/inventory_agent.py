"""Read-only plugin agent: ``inventory``.

Proposes a `fs.stat` decision to inventory a directory (default ``.``).
Read-only — lists entries and sizes via the `fs.stat` tool.
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision

KIND = "inventory"


class InventoryBoundary:
    def __init__(self, llm) -> None:
        self._llm = llm

    def decide(self, context) -> list:
        path = context.get("path", ".") if isinstance(context, dict) else "."
        return [create_decision(
            id=f"inv-{uuid.uuid4().hex}",
            source=KIND,
            kind="fs.stat",
            payload={"path": path},
        )]


def build(llm) -> InventoryBoundary:
    return InventoryBoundary(llm)
