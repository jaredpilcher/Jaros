"""The determinism guardrail runs in CI (EXT-001 / REQ-7).

Ensures the determinism check is *checked by default*: the core replay path must
be deterministic, and a deliberately non-deterministic handler must be caught.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from jaros.core.decision_gate import reset_validators
from jaros.execution import executor

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_determinism.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_determinism", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_determinism"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _isolate():
    executor.reset_handlers(); reset_validators()
    yield
    executor.reset_handlers(); reset_validators()


def test_core_replay_path_is_deterministic():
    assert _load().check() == []


def test_guardrail_would_catch_nondeterminism():
    """A handler that depends on call count is flagged by replays_agree."""
    from jaros.core.decision import create_decision
    from jaros.execution import replays_agree
    from jaros.state import DecisionLog, TransitionLog, commit, record_decision, replay
    from jaros.state.model import INITIAL_STATE
    import tempfile

    calls = {"n": 0}

    def flaky(decision, *, log):
        calls["n"] += 1
        # A non-deterministic event choice -> divergent transition logs.
        event = "start" if calls["n"] % 2 else "fail"
        commit(log, INITIAL_STATE, event)
        return {"n": calls["n"]}

    executor.register_handler("advance", flaky)
    dlog = DecisionLog(Path(tempfile.mkdtemp()) / "state")
    record_decision(dlog, create_decision(id="d", source="x", kind="advance", payload={}))

    def replay_once() -> bytes:
        log = TransitionLog(Path(tempfile.mkdtemp()))
        replay(dlog, executor.apply, log=log)
        return log.path.read_bytes()

    assert replays_agree(replay_once, runs=2) is False
