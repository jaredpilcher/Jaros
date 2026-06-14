"""TEMPLATE — a Jaros agent.

An agent is a `ReasoningBoundary`: it reasons over a job's input `context` and
returns a list of inert `Decision` objects. It NEVER performs a side effect —
its only output is data. The matching side effect lives in a tool (see
`tool.py`) whose `NAME` equals the decision's `kind`.

To use this template:
  1. Copy it to `<data-dir>/agents/word_count_agent.py` (rename as you like).
  2. Change `KIND`, the decision `kind`/`source`, and the `payload` you emit.
  3. If the `kind` names a custom action, ship a matching tool (see `tool.py`).
The daemon imports every `*.py` in `agents/` on its next tick — no restart.

Contract (required by `jaros.registry.load_agents`):
  - a module-level `KIND: str`
  - a `build(llm) -> ReasoningBoundary` factory
  - the boundary exposes `decide(context) -> list[Decision]`
"""

from __future__ import annotations

import uuid

from jaros.core import create_decision

# The job kind this agent answers. `jaros submit word-count ...` routes here.
KIND = "word-count"


class WordCountBoundary:
    def __init__(self, llm) -> None:
        # `llm` is the shared LlmClient. A real agent calls `self._llm.complete(...)`
        # to decide WHAT to do; the result is captured as inert payload data so the
        # run stays reproducible by replay. This template needs no model call.
        self._llm = llm

    def decide(self, context) -> list:
        # `context` is the job's parsed JSON input. Read what you need from it.
        path = context.get("path", "README.md") if isinstance(context, dict) else "README.md"
        return [
            create_decision(
                id=f"wc-{uuid.uuid4().hex}",   # unique per decision
                source=KIND,                    # the emitting agent
                kind="text.wordcount",          # MUST match the tool's NAME
                payload={"path": path},         # inert, JSON-serializable data only
            )
        ]


def build(llm) -> WordCountBoundary:
    return WordCountBoundary(llm)
