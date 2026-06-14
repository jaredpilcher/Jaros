"""Reusable runtime executor handlers (EXT-007 / REQ-2, EXT-008 / REQ-6).

The daemon and ``jaros replay`` register the **same** handlers, so a replay
re-uses the exact production code path — the byte-identical guarantee is
faithful, not a re-implementation that could silently drift.

The state-driving ``advance`` handler is a **pure function of the decision and
the ``log`` collaborator**: it commits each event to whatever transition log it
is handed (the daemon passes its live log; replay passes a sandbox log) and
returns the final state. ``fs.write`` writes via the given harness + writer, so
replay's writes land in a sandbox.

Imports only the Execution / Harness / State planes — never the Reasoning Plane
(enforced by ``scripts/check_planes.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jaros.core.decision import Decision
from jaros.execution import executor
from jaros.harness import Action
from jaros.state import commit
from jaros.state.model import INITIAL_STATE


# #EXT-008-REQ-6 Start
def make_advance_handler():
    """The deterministic state-driving handler — a pure function of (decision, log)."""

    def advance_handler(decision: Decision, *, log, **_: Any) -> dict[str, Any]:
        payload = decision.payload if isinstance(decision.payload, dict) else {}
        events = payload.get("events") or ["start", "complete"]
        note = payload.get("note")
        state = INITIAL_STATE
        indices: list[int] = []
        for event in events:
            result = commit(log, state, event)
            state = result.state
            indices.append(result.index)
        return {
            "decision": decision.id,
            "source": decision.source,
            "kind": decision.kind,
            "finalState": state,
            "events": list(events),
            "logIndices": indices,
            "note": note,
        }

    return advance_handler


def make_fs_write_handler(harness, writer_agent: str):
    """An ``fs.write`` handler that writes via the given harness + writer agent."""

    def fs_write_handler(decision: Decision, **_: Any) -> dict[str, Any]:
        payload = decision.payload if isinstance(decision.payload, dict) else {}
        path = payload.get("path")
        data = payload.get("data", "")
        if not path:
            raise RuntimeError("Missing path in fs.write decision payload")
        ar = harness.request(writer_agent, Action(type="fs.write", path=path, data=data))
        if not ar.allowed:
            raise RuntimeError(f"Harness denied fs.write: {ar.reason}")
        return {"path": path, "bytes": len(data)}

    return fs_write_handler


def register_runtime_handlers(*, harness, writer_agent: str, tools_dir: str | Path | None = None) -> None:
    """Register the runtime's deterministic handlers (+ any custom tools).

    The same call wires the daemon and ``jaros replay``; the caller supplies the
    collaborators (live or sandbox). ``advance`` drives the state machine through
    the ``log`` collaborator passed at ``apply`` time; ``fs.write`` writes via
    ``harness``/``writer_agent``. Custom tools under ``tools_dir`` are loaded so
    replay re-applies tool decisions identically.
    """
    executor.register_handler("advance", make_advance_handler())
    executor.register_handler("fs.write", make_fs_write_handler(harness, writer_agent))
    if tools_dir is not None:
        from jaros.execution.tools import load_custom_tools

        load_custom_tools(Path(tools_dir))
# #EXT-008-REQ-6 End
