"""Reproducibility benchmark — Jaros deterministic replay (launch artifact).

Demonstrates the Prime Directive's headline property with numbers you can quote:
a recorded agent run, replayed N times into *fresh, isolated* state, reconstructs
**byte-identical** state every time — with **zero model calls** on replay.

It also shows the contrast: a typical "the-model-drives" agent loop, whose output
is a function of wall-clock/RNG (a stand-in for live tool calls + a non-pinned
model), diverges run to run — the "it only happens sometimes" you can't debug.

Run:  python launch/benchmark/run_reproducibility_benchmark.py
Requires: only `jaros` (no network, no model, no infra).
"""

from __future__ import annotations

import hashlib
import random
import tempfile
import time
from pathlib import Path

from jaros.core.decision import create_decision
from jaros.execution import executor
from jaros.state import (
    DecisionLog,
    TransitionLog,
    commit,
    record_decision,
    replay,
)
from jaros.state.model import INITIAL_STATE

RUNS = 5
MODEL_CALLS_ON_REPLAY = 0  # replay re-applies recorded decisions; the model is never called


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- The deterministic executor handler (Execution Plane) -------------------
# A pure function of the validated decision + the transition log it is given.
def advance(decision, *, log: TransitionLog):
    payload = decision.payload if isinstance(decision.payload, dict) else {}
    state = INITIAL_STATE
    for event in payload.get("events", ["start", "complete"]):
        state = commit(log, state, event).state
    return {"finalState": state}


def record_a_run(workdir: Path) -> DecisionLog:
    """Simulate an agent run: the reasoning emits inert decisions, which we record."""
    dlog = DecisionLog(workdir / "state")
    dlog.ensure()
    # In a real agent these payloads come from the model's proposal; here we fix
    # them so the benchmark is self-contained. The point is what happens *after*:
    # once recorded, the run is reproducible regardless of the model.
    for i in range(3):
        record_decision(
            dlog,
            create_decision(
                id=f"d{i}",
                source="benchmark-agent",
                kind="advance",
                payload={"events": ["start", "block", "unblock", "complete"]},
            ),
        )
    return dlog


def jaros_replay_is_byte_identical() -> tuple[bool, list[str]]:
    """Replay the recorded run RUNS times into fresh state; collect state hashes."""
    executor.reset_handlers()
    executor.register_handler("advance", advance)

    root = Path(tempfile.mkdtemp(prefix="jaros-bench-"))
    dlog = record_a_run(root)

    hashes: list[str] = []
    for r in range(RUNS):
        # Fresh, isolated transition log per replay — no shared state to cheat with.
        fresh = TransitionLog(root / f"replay-{r}", "transitions.log")
        fresh.ensure()
        replay(dlog, executor.apply, log=fresh)  # re-applies recorded decisions; no model call
        hashes.append(_sha(fresh.path))

    return (len(set(hashes)) == 1, hashes)


# --- The contrast: a "model-drives" loop with live non-determinism ----------
def naive_agent_output() -> str:
    """A stand-in for a typical agent step whose result depends on live state
    (timestamps, RNG, un-pinned tool output). Re-running it does NOT reproduce."""
    return f"answer-{random.randint(0, 1_000_000)}-{time.time_ns()}"


def naive_loop_is_reproducible() -> tuple[bool, list[str]]:
    outs = [naive_agent_output() for _ in range(RUNS)]
    digests = [hashlib.sha256(o.encode()).hexdigest()[:12] for o in outs]
    return (len(set(digests)) == 1, digests)


def main() -> int:
    print("=" * 68)
    print("Jaros reproducibility benchmark")
    print("=" * 68)

    ok, hashes = jaros_replay_is_byte_identical()
    print(f"\n[Jaros]  recorded run replayed {RUNS}x into fresh isolated state")
    print(f"         model calls on replay : {MODEL_CALLS_ON_REPLAY}")
    print(f"         distinct state hashes : {len(set(hashes))}  (1 == byte-identical)")
    print(f"         state sha256[:16]     : {hashes[0][:16]}")
    print(f"         => REPRODUCIBLE       : {ok}")

    naive_ok, digests = naive_loop_is_reproducible()
    print(f"\n[Typical 'model-drives' loop] same step run {RUNS}x")
    print(f"         distinct outputs      : {len(set(digests))}  ({digests})")
    print(f"         => REPRODUCIBLE       : {naive_ok}")

    print("\n" + "-" * 68)
    if ok and not naive_ok:
        print("RESULT: Jaros replay is byte-identical; the model-drives loop is not.")
        print("        That difference is the product. 'It only happens sometimes'")
        print("        becomes 'replay the decision log and step through it.'")
        return 0
    print("RESULT: unexpected — investigate before publishing numbers.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
