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
    # Reuse the runtime's swarm replay (EXT-015): replays the whole hive through
    # the real handlers into an isolated sandbox, verifies the tamper-evident
    # chain + byte-identity, and attributes any failure to the exact agent — the
    # same code path the CLI uses, so the console can't drift from it.
    from jaros.state import replay_swarm

    res = replay_swarm(data_dir)
    attribution = None
    if res.attribution is not None:
        a = res.attribution
        attribution = {"kind": a.kind, "index": a.index, "id": a.id, "source": a.source, "reason": a.reason}
    return {
        "decisions": res.decisions,
        "byAgent": {t.source: t.decisions for t in res.by_agent},
        "finalState": res.final_state,
        "byteIdentical": res.byte_identical,
        # A byte-identical reconstruction over the live log is the determinism signal.
        "deterministic": res.byte_identical,
        "chainOk": res.chain_ok,
        "attribution": attribution,
        "modelCalls": 0,
        "ok": res.ok,
    }
# #EXT-010-REQ-5 End


# #EXT-010-REQ-8 Start
def do_evals(data_dir: str) -> dict:
    from jaros.eval import load_cases, run_suite
    from jaros.execution import executor
    from jaros.execution.tools import load_custom_tools, reset_tools_registry
    from jaros.llm import LlmConfig, create_llm_client
    from jaros.registry import AgentRegistry, load_plugins, register_builtins

    data = Path(data_dir)
    executor.reset_handlers()
    reset_tools_registry()
    llm = create_llm_client(LlmConfig(provider="default"))
    registry = AgentRegistry()
    register_builtins(registry, llm)
    load_plugins(registry, data / "plugins", llm)
    load_custom_tools(data / "tools")

    cases = load_cases(data / "evals")
    report = run_suite(cases, registry)
    out = report.to_dict()
    out["ok"] = True
    return out
# #EXT-010-REQ-8 End


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
        elif cmd == "evals":
            if len(argv) < 2:
                print(json.dumps({"error": "evals requires <data_dir>"}))
                return 2
            out = do_evals(argv[1])
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
