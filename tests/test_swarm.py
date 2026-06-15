"""Tests for swarm replay & attribution + the tamper-evident chain (EXT-015).

Proves the apex purpose: a multi-agent run records one ordered, per-agent,
hash-chained decision log; replaying it reconstructs the whole hive to
byte-identical state with zero model calls; and any failure is attributed to the
exact agent + decision — by recorded fact, not inference.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jaros.comms.fs import SharedFileSystem
from jaros.core import create_decision
from jaros.core.decision_gate import reset_validators
from jaros.execution import executor
from jaros.execution.handlers import register_runtime_handlers
from jaros.execution.tools import reset_tools_registry
from jaros.harness import GrantSpec, Harness
from jaros.state import (
    DecisionLog,
    TransitionLog,
    record_decision,
    replay_swarm,
    summary_by_agent,
    verify_chain,
)


@pytest.fixture(autouse=True)
def _isolate():
    executor.reset_handlers(); reset_validators(); reset_tools_registry()
    yield
    executor.reset_handlers(); reset_validators(); reset_tools_registry()


def _adv(source: str, n: int):
    return create_decision(id=f"{source}-{n}", source=source, kind="advance",
                           payload={"events": ["start", "complete"], "note": f"{source} {n}"})


def _handoff(source: str, n: int, ok: bool):
    return create_decision(id=f"{source}-h{n}", source=source, kind="swarm.handoff",
                           payload={"draft": f"draft {n}", "ok": ok})


# ---- tamper-evident hash chain (REQ-4) --------------------------------------

def _record(data: Path, decisions):
    dl = DecisionLog(data / "state")
    dl.ensure()
    for d in decisions:
        record_decision(dl, d)
    return dl


def test_chain_verifies_clean_log(tmp_path: Path):
    _record(tmp_path, [_adv("a", 1), _adv("b", 2), _adv("c", 3)])
    res = verify_chain(DecisionLog(tmp_path / "state"))
    assert res.ok and res.length == 3 and res.position is None


def test_record_decision_links_prev(tmp_path: Path):
    dl = _record(tmp_path, [_adv("a", 1), _adv("b", 2)])
    recs = list(dl.read())
    from jaros.state import GENESIS_PREV
    assert recs[0].prev == GENESIS_PREV
    assert recs[1].prev == recs[0].checksum  # chained to the previous record


@pytest.mark.parametrize("attack", ["edit", "delete", "reorder", "insert"])
def test_chain_detects_tampering(tmp_path: Path, attack: str):
    dl = _record(tmp_path, [_adv("a", 1), _adv("b", 2), _adv("c", 3)])
    lines = dl.path.read_text(encoding="utf-8").splitlines()
    if attack == "edit":
        lines[1] = lines[1].replace("b 2", "b HACKED")
    elif attack == "delete":
        del lines[1]
    elif attack == "reorder":
        lines[1], lines[2] = lines[2], lines[1]
    elif attack == "insert":
        lines.insert(1, lines[1])
    dl.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = verify_chain(DecisionLog(tmp_path / "state"))
    assert not res.ok and res.position is not None and res.reason


# ---- provenance + summary (REQ-1) -------------------------------------------

def test_summary_by_agent_counts_and_orders():
    decisions = [_adv("planner", 1), _adv("worker", 1), _adv("worker", 2), _adv("reviewer", 1)]
    tallies = summary_by_agent(decisions)
    assert [(t.source, t.decisions) for t in tallies] == [
        ("planner", 1), ("reviewer", 1), ("worker", 2),  # sorted by source, counted
    ]


# ---- swarm replay + attribution (REQ-2, REQ-3) ------------------------------

def _run_swarm(data: Path, decisions, stage_handoff_tool: bool = True) -> None:
    """Record + execute a multi-agent run exactly as the daemon would.

    Each decision is gate-accepted, recorded (on_accept), then executed against a
    live transition log — producing the live ``decisions.log`` + ``transitions.log``
    that ``replay_swarm`` reconstructs.
    """
    fs = SharedFileSystem(data)
    fs.ensure_layout()
    (data / "tools").mkdir(parents=True, exist_ok=True)
    if stage_handoff_tool:
        import shutil
        src = Path("examples/swarm/tools/handoff_tool.py").resolve()
        shutil.copy(src, data / "tools" / "handoff_tool.py")
    live_log = TransitionLog(data / "state")
    decision_log = DecisionLog(data / "state")
    harness = Harness()
    harness.spawn("writer", GrantSpec(role="FsWriteRole", fs=fs))
    register_runtime_handlers(harness=harness, writer_agent="writer", tools_dir=data / "tools")
    for d in decisions:
        try:
            executor.apply(d, on_accept=lambda x: record_decision(decision_log, x), log=live_log)
        except Exception:
            pass  # a handler raised (e.g. a bad handoff) — the daemon contains it; decision is recorded


def test_swarm_replays_byte_identical_no_model_calls(tmp_path: Path):
    decisions = [_adv("planner", 1), _handoff("worker", 1, ok=True), _adv("reviewer", 1),
                 _adv("planner", 2), _handoff("worker", 2, ok=True), _adv("reviewer", 2)]
    _run_swarm(tmp_path, decisions)
    res = replay_swarm(tmp_path)
    assert res.ok is True
    assert res.byte_identical is True
    assert res.model_calls == 0
    assert res.chain_ok is True
    assert res.attribution is None
    assert {t.source: t.decisions for t in res.by_agent} == {"planner": 2, "worker": 2, "reviewer": 2}


def test_swarm_attributes_bad_handoff_to_the_exact_agent(tmp_path: Path):
    decisions = [_adv("planner", 1), _handoff("worker", 1, ok=True), _adv("reviewer", 1),
                 _handoff("worker", 2, ok=False)]  # the seeded bad handoff
    _run_swarm(tmp_path, decisions)
    res = replay_swarm(tmp_path)
    # Reproduces byte-identically (the failed handoff writes no transitions) ...
    assert res.byte_identical is True and res.ok is True and res.model_calls == 0
    # ... and the failure is attributed to the exact agent + decision, by recorded fact.
    assert res.attribution is not None
    assert res.attribution.kind == "failure"
    assert res.attribution.source == "worker"
    assert res.attribution.id == "worker-h2"
    assert "reject" in res.attribution.reason.lower() or "handoff" in res.attribution.reason.lower()


def test_long_swarm_log_verifies_and_replays(tmp_path: Path):
    # A long multi-agent run (O(1) appends): the cached-tail chaining must still
    # produce a valid hash chain and a byte-identical swarm replay.
    sources = ["planner", "worker", "reviewer"]
    decisions = [_adv(sources[i % 3], i) for i in range(150)]
    _run_swarm(tmp_path, decisions, stage_handoff_tool=False)
    from jaros.state import DecisionLog, read_decisions, verify_chain
    dl = DecisionLog(tmp_path / "state")
    assert len(read_decisions(dl)) == 150
    chain = verify_chain(dl)
    assert chain.ok and chain.length == 150
    res = replay_swarm(tmp_path)
    assert res.ok is True and res.byte_identical is True and res.model_calls == 0
    assert res.decisions == 150
    assert {t.source: t.decisions for t in res.by_agent} == {"planner": 50, "worker": 50, "reviewer": 50}


def test_decisionlog_caches_tail_for_o1_appends(tmp_path: Path):
    # record_decision must not re-read the whole log per append; it uses the cached
    # tail. The cache stays correct: prev links chain and indices stay continuous.
    from jaros.state import DecisionLog, GENESIS_PREV, record_decision
    dl = DecisionLog(tmp_path / "state")
    dl.ensure()
    r1 = record_decision(dl, _adv("a", 1))
    r2 = record_decision(dl, _adv("b", 2))
    assert r1.prev == GENESIS_PREV and r1.index == 1
    assert r2.prev == r1.checksum and r2.index == 2
    assert dl._count == 2 and dl._last_checksum == r2.checksum  # cache stayed current
    # A freshly-constructed log over the same file lazily reloads the tail correctly.
    dl2 = DecisionLog(tmp_path / "state")
    r3 = record_decision(dl2, _adv("c", 3))
    assert r3.index == 3 and r3.prev == r2.checksum


def test_swarm_attributes_divergence_to_a_decision(tmp_path: Path):
    decisions = [_adv("planner", 1), _adv("worker", 1)]
    _run_swarm(tmp_path, decisions, stage_handoff_tool=False)
    # Corrupt the live transition log so replay diverges from it.
    live = tmp_path / "state" / "transitions.log"
    with open(live, "a", encoding="utf-8") as fh:
        fh.write('{"index":99,"event":"x","state":"DONE","checksum":"z"}\n')
    res = replay_swarm(tmp_path)
    assert res.byte_identical is False and res.ok is False
    assert res.attribution is not None and res.attribution.kind == "divergence"
