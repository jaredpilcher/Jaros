"""Introspection + replay helper the console bridge shells out to.

Keeps `jaros` itself the single source of truth: the console renders the real
state model and harness rules, and the "Replay" action actually re-executes the
recorded decision log through the deterministic executor — no model call.

Usage:
    python jaros_introspect.py model
    python jaros_introspect.py harness
    python jaros_introspect.py replay <data_dir>
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


# #EXT-010-REQ-6 Start
def do_model() -> dict:
    from jaros.state.model import (
        EVENTS,
        INITIAL_STATE,
        STATES,
        list_transitions,
    )

    return {
        "states": list(STATES),
        "events": list(EVENTS),
        "initial": INITIAL_STATE,
        "transitions": [
            {"from": f, "event": e, "to": t} for (f, e, t) in list_transitions()
        ],
    }


def do_harness() -> dict:
    from jaros.harness.capabilities import BUILTIN_ROLES
    from jaros.harness.rules import DEFAULT_RULES

    return {
        "rules": {action: cap.__name__ for action, cap in DEFAULT_RULES.items()},
        "roles": {
            role: [c.__name__ for c in caps] for role, caps in BUILTIN_ROLES.items()
        },
    }
# #EXT-010-REQ-6 End


# #EXT-010-REQ-5 Start
def do_replay(data_dir: str) -> dict:
    from jaros.execution import executor
    from jaros.execution.tools import load_custom_tools, reset_tools_registry
    from jaros.state import (
        DecisionLog,
        TransitionLog,
        commit,
        recover,
        replay,
    )
    from jaros.state.model import INITIAL_STATE

    data = Path(data_dir)
    decision_log = DecisionLog(data / "state")
    recorded = decision_log.length()

    # Re-register the deterministic handlers a daemon would have, into a FRESH
    # transition log, then replay the recorded decisions through the executor.
    def advance_handler(decision, *, log):
        payload = decision.payload if isinstance(decision.payload, dict) else {}
        events = payload.get("events") or ["start", "complete"]
        state = INITIAL_STATE
        for event in events:
            state = commit(log, state, event).state
        return {"finalState": state}

    executor.reset_handlers()
    reset_tools_registry()
    executor.register_handler("advance", advance_handler)
    executor.register_handler("fs.write", lambda d, **k: {"path": (d.payload or {}).get("path")})
    try:
        load_custom_tools(data / "tools")  # so custom-tool decisions replay too
    except Exception:
        pass

    fresh = TransitionLog(Path(tempfile.mkdtemp(prefix="jaros-replay-")))
    results = replay(decision_log, executor.apply, log=fresh)
    final_state = recover(fresh)

    # Byte-identical check against the original durable transition log, if present.
    original = data / "state" / "transitions.log"
    byte_identical = False
    try:
        if original.exists():
            byte_identical = fresh.path.read_bytes() == original.read_bytes()
    except Exception:
        byte_identical = False

    return {
        "decisions": recorded,
        "applied": sum(1 for r in results if getattr(r, "applied", False)),
        "finalState": final_state,
        "byteIdentical": byte_identical,
        "modelCalls": 0,
        "ok": True,
    }
# #EXT-010-REQ-5 End


def main(argv: list[str]) -> int:
    if not argv:
        print(json.dumps({"error": "missing command"}))
        return 2
    cmd = argv[0]
    try:
        if cmd == "model":
            out = do_model()
        elif cmd == "harness":
            out = do_harness()
        elif cmd == "replay":
            if len(argv) < 2:
                print(json.dumps({"error": "replay requires <data_dir>"}))
                return 2
            out = do_replay(argv[1])
        else:
            print(json.dumps({"error": f"unknown command {cmd!r}"}))
            return 2
    except Exception as exc:  # surface a clean error to the bridge
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}", "ok": False}))
        return 1
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
