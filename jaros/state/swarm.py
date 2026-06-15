"""Swarm replay & attribution (EXT-015 / REQ-2, REQ-3).

A swarm is a hive of agent threads (EXT-003) whose every accepted decision is
already recorded, with its ``source``, to one durable, hash-chained log
(EXT-001/EXT-002/EXT-015-REQ-4). So swarm replay is not a new mechanism — it is
the existing record-and-replay applied to the *whole* log, plus **attribution**:
reading provenance off the log to name the exact agent and decision behind any
failure or divergence. The single-agent ``jaros replay`` (EXT-008) is the ``N=1``
special case of this.

Like EXT-008, replay re-uses the runtime's own handlers
(:func:`jaros.execution.handlers.register_runtime_handlers`) over an **isolated
sandbox**, constructs **no** ``LlmClient``, makes zero model calls, and writes
nothing to the live data dir. Decisions are applied one at a time so a single
member's failing handoff is *attributed* rather than aborting the replay.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jaros.core.decision import Decision

# #EXT-015-REQ-2 Start
# #EXT-015-REQ-3 Start


@dataclass(frozen=True)
class AgentTally:
    """How many decisions a single ``source`` agent contributed to the run."""

    source: str
    decisions: int


@dataclass(frozen=True)
class Attribution:
    """The exact agent + decision behind a failure or divergence (recorded fact).

    ``kind`` is ``"failure"`` (a replayed decision was refused or its handler
    raised) or ``"divergence"`` (a transition differed from the live run on
    replay — a non-deterministic handler). ``index`` is the 1-based decision
    position in the log, ``id``/``source`` identify the decision and the agent
    that produced it, and ``reason`` explains it.
    """

    kind: str
    index: int
    id: str
    source: str
    reason: str


@dataclass(frozen=True)
class SwarmReplayResult:
    """Result of replaying a whole swarm's decision log and attributing failure."""

    decisions: int
    by_agent: list[AgentTally]
    final_state: str | None
    byte_identical: bool
    model_calls: int  # always 0 — replay constructs no LlmClient
    chain_ok: bool
    chain_reason: str | None
    attribution: Attribution | None
    ok: bool


# #EXT-015-REQ-1 Start
def summary_by_agent(decisions: list[Decision]) -> list[AgentTally]:
    """Per-agent provenance: group the recorded log by ``source`` for a
    deterministic "who did how much" view across the whole swarm (REQ-1)."""
    counts: dict[str, int] = {}
    for d in decisions:
        counts[d.source] = counts.get(d.source, 0) + 1
    return [AgentTally(src, counts[src]) for src in sorted(counts)]
# #EXT-015-REQ-1 End


def _first_diff_line(a: bytes, b: bytes) -> int:
    """Return the 1-based line number where two newline-delimited blobs first differ."""
    la = a.split(b"\n")
    lb = b.split(b"\n")
    for i in range(max(len(la), len(lb))):
        ai = la[i] if i < len(la) else None
        bi = lb[i] if i < len(lb) else None
        if ai != bi:
            return i + 1
    return 0


def _decision_for_transition(
    decisions: list[Decision], results: list[Any], transition_index: int
) -> tuple[int, Decision] | None:
    """Find the (1-based index, decision) whose handler produced ``transition_index``."""
    for i, (d, r) in enumerate(zip(decisions, results), start=1):
        out = getattr(r, "output", None)
        if isinstance(out, dict) and transition_index in (out.get("logIndices") or []):
            return i, d
    return None


def attribute(
    decisions: list[Decision],
    results: list[Any],
    sandbox_bytes: bytes,
    live_bytes: bytes,
) -> Attribution | None:
    """Name the exact decision + agent behind a failure or divergence, or ``None``.

    Attribution is derived purely from the recorded log and the replay results —
    never inferred by a separate tracer model (EXT-015 / REQ-3).
    """
    # Failure: the first replayed decision that was refused or whose handler raised.
    for i, (d, r) in enumerate(zip(decisions, results), start=1):
        if not getattr(r, "applied", False):
            reason = getattr(r, "reason", None) or "decision failed on replay"
            return Attribution("failure", i, d.id, d.source, reason)
    # Divergence: the first transition that differs from the live run on replay.
    if sandbox_bytes != live_bytes:
        line = _first_diff_line(sandbox_bytes, live_bytes)
        hit = _decision_for_transition(decisions, results, line)
        if hit is not None:
            i, d = hit
            return Attribution(
                "divergence", i, d.id, d.source,
                f"transition {line} differs from the live run (non-deterministic handler)",
            )
        return Attribution(
            "divergence", 0, "?", "?",
            f"transition {line} differs from the live run on replay",
        )
    return None


def replay_swarm(data_dir: str | Path) -> SwarmReplayResult:
    """Replay a whole swarm's decision log into a sandbox and attribute any failure.

    Re-applies every recorded decision, in order, through the runtime's own
    handlers over a fresh temp sandbox (no ``LlmClient``, zero model calls,
    nothing written to the live data dir), verifies the log's hash chain, checks
    byte-identity against the live transition log, and computes per-agent
    provenance + attribution. The single-agent run is simply ``N=1``.
    """
    from jaros.comms.fs import SharedFileSystem
    from jaros.core.decision_gate import reset_validators
    from jaros.execution import executor
    from jaros.execution.handlers import register_runtime_handlers
    from jaros.execution.tools import reset_tools_registry
    from jaros.harness import GrantSpec, Harness
    from jaros.state import (
        DecisionLog,
        TransitionLog,
        read_decisions,
        recover,
        verify_chain,
    )

    data_dir = Path(data_dir)
    decision_log = DecisionLog(data_dir / "state")
    decisions = read_decisions(decision_log)

    chain = verify_chain(decision_log)

    if not decisions:
        return SwarmReplayResult(
            decisions=0, by_agent=[], final_state=None, byte_identical=False,
            model_calls=0, chain_ok=chain.ok, chain_reason=chain.reason,
            attribution=None, ok=False,
        )

    sandbox = Path(tempfile.mkdtemp(prefix="jaros-swarm-replay-"))
    try:
        sandbox_fs = SharedFileSystem(sandbox)
        sandbox_fs.ensure_layout()
        sandbox_log = TransitionLog(sandbox / "state")
        sandbox_harness = Harness()
        writer = "replay-writer"
        sandbox_harness.spawn(writer, GrantSpec(role="FsWriteRole", fs=sandbox_fs))

        # Rebuild a clean, isolated execution environment so the same custom tools
        # re-register over the sandbox (load_custom_tools is path-idempotent, so a
        # prior load in this process must be cleared for the handlers to be present).
        executor.reset_handlers()
        reset_validators()
        reset_tools_registry()
        register_runtime_handlers(
            harness=sandbox_harness, writer_agent=writer, tools_dir=data_dir / "tools"
        )

        # Apply one decision at a time so a single member's failing handoff is
        # attributed, not allowed to abort the whole swarm replay.
        results: list[Any] = []
        for decision in decisions:
            try:
                results.append(executor.apply(decision, log=sandbox_log))
            except Exception as exc:  # a handler raised — record it as a non-applied result
                results.append(
                    executor.ExecutionResult(
                        applied=False, reason=f"{type(exc).__name__}: {exc}", accepted=decision
                    )
                )

        final_state = recover(sandbox_log)
        sandbox_bytes = sandbox_log.path.read_bytes() if sandbox_log.path.exists() else b""
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    live_log = data_dir / "state" / "transitions.log"
    live_bytes = live_log.read_bytes() if live_log.exists() else b""
    byte_identical = sandbox_bytes == live_bytes

    by_agent = summary_by_agent(decisions)
    attribution = attribute(decisions, results, sandbox_bytes, live_bytes)
    ok = byte_identical and chain.ok

    return SwarmReplayResult(
        decisions=len(decisions),
        by_agent=by_agent,
        final_state=final_state,
        byte_identical=byte_identical,
        model_calls=0,
        chain_ok=chain.ok,
        chain_reason=chain.reason,
        attribution=attribution,
        ok=ok,
    )
# #EXT-015-REQ-3 End
# #EXT-015-REQ-2 End
