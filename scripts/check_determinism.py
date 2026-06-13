"""Determinism guardrail (EXT-001 / REQ-7, EXT-002 / REQ-6).

The byte-identical replay guarantee depends on executor handlers being
deterministic functions of the decision and state. This guardrail makes that
*checked by default*, not merely checkable: it records a representative run
through the core state-driving handler, replays it several times into fresh
isolated state, and requires byte-identical transition logs every time. A
divergence means non-determinism crept into the core execution path — fail the
build. (Agent authors verify their own handlers the same way via
``jaros.execution.replays_agree`` and ``Expect.deterministic`` eval cases.)

Run as: ``python scripts/check_determinism.py``
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def check() -> list[str]:
    """Return determinism problems with the core replay path (empty if clean)."""
    from jaros.core.decision import create_decision
    from jaros.execution import executor, replays_agree
    from jaros.state import (
        DecisionLog,
        TransitionLog,
        commit,
        record_decision,
        replay,
    )
    from jaros.state.model import INITIAL_STATE

    problems: list[str] = []
    saved = dict(getattr(executor, "_handlers", {}))
    executor.reset_handlers()
    try:
        def advance(decision, *, log):
            payload = decision.payload if isinstance(decision.payload, dict) else {}
            state = INITIAL_STATE
            for event in payload.get("events", ["start", "complete"]):
                state = commit(log, state, event).state
            return {"finalState": state}

        executor.register_handler("advance", advance)

        dlog = DecisionLog(Path(tempfile.mkdtemp(prefix="jaros-determinism-")) / "state")
        for i in range(4):
            record_decision(dlog, create_decision(
                id=f"d{i}", source="core", kind="advance",
                payload={"events": ["start", "complete"]},
            ))

        def replay_once() -> bytes:
            log = TransitionLog(Path(tempfile.mkdtemp(prefix="jaros-det-")))
            replay(dlog, executor.apply, log=log)
            return log.path.read_bytes()

        if not replays_agree(replay_once, runs=3):
            problems.append("core state-driving replay is NOT deterministic across runs")
    finally:
        executor.reset_handlers()
        for kind, fn in saved.items():
            executor.register_handler(kind, fn)
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("Determinism check FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print("Determinism check passed: the core replay path is deterministic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
