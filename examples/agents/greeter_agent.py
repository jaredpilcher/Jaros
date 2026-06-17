"""Example agent: ``greeter``.

Demonstrates an agent that proposes a *custom tool* action. It emits an inert
Decision of kind ``demo.greet`` (see ``examples/tools/greet_tool.py``); the
daemon's gate runs the tool's ``validate()`` and the executor dispatches to the
tool's ``execute()``. The agent never performs the side effect itself — its only
output is data.

Drop this file into the shared-FS ``agents/`` folder and the matching tool into
``tools/``.
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision


KIND = "greeter"


class GreeterBoundary:
    def __init__(self, llm) -> None:
        self._llm = llm

    def decide(self, context) -> list:
        name = context.get("name", "world") if isinstance(context, dict) else "world"
        return [
            create_decision(
                id=f"greet-{uuid.uuid4().hex}",
                source="greeter",
                kind="demo.greet",
                payload={"name": name},
            )
        ]


def build(llm) -> GreeterBoundary:
    return GreeterBoundary(llm)
