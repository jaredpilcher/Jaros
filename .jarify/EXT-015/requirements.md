---
id: EXT-015
title: Swarm Replay & Attribution
status: covered
priority: high
implementation:
  - file: jaros/state/swarm.py
    ranges:
      - - 1
        - 233
  - file: jaros/state/decision_log.py
    ranges:
      - - 228
        - 276
  - file: jaros/cli.py
    ranges:
      - - 292
        - 368
---

# Swarm Replay & Attribution

The apex deliverable of the Prime Directive. Extends single-run deterministic
replay (EXT-002 / REQ-6) to a multi-agent run: replay the whole hive to
byte-identical state, attribute any failure to the exact agent and decision, and
make the per-agent record tamper-evident. Realizes Prime Directive tenet
[PRIME-001 / P5] (swarm reproducibility & accountability). Builds on EXT-001 (the
`Decision` contract carries `source`), EXT-002 (durable decision log + replay), and
EXT-003 (agents as threads). It adds **no** infrastructure and **no** direct
agent-to-agent channel — coordination stays mediated through the deterministic
plane, which is what makes the swarm reproducible.

### [REQ-1] Per-Agent Provenance & Global Order

A multi-agent run records every accepted decision, in one global order, tagged with
the agent that produced it — so attribution is a recorded fact, not inference.

#### Acceptance Criteria
- [x] Every accepted `Decision` from any agent is appended to a single decision log
      in commit order, before its effects are observable (one ordered log per node).
- [x] Each record preserves the decision's `source` agent and `id`; `read_decisions`
      returns them in the original order across agents.
- [x] Concurrent agents never interleave a single record or lose ordering: appends
      are serialized so the log is a faithful, replayable transcript of the swarm.

### [REQ-2] Swarm Replay (whole hive → byte-identical)

Replaying the one decision log re-executes every member's decisions in recorded
order through the deterministic executor, reconstructing the swarm's run exactly.

#### Acceptance Criteria
- [x] A function (e.g. `replay_swarm`) re-applies all recorded decisions, in order,
      via the runtime's own handlers (`register_runtime_handlers`) over an isolated
      sandbox — constructing **no** `LlmClient` and making zero model calls.
- [x] The reconstructed state is **byte-identical** to the live run, and reproducible
      across repeated replays (ties to `check_determinism`).
- [x] Replay writes nothing to the live data dir (side effects sandboxed), so it is
      safe and idempotent — the single-agent case (EXT-008 `jaros replay`) is the
      `N=1` special case of this.

### [REQ-3] Failure Attribution (which agent, which decision)

At any divergence or failure, the system names the exact decision and the agent that
produced it.

#### Acceptance Criteria
- [x] On a byte-divergence between replays (or vs the live log), the report names the
      first diverging decision's `index`, `id`, and `source` agent.
- [x] When a replayed decision is refused/raises, the report names that decision and
      its `source` agent (and the reason) — not just a stack trace.
- [x] Attribution is derived from the recorded log (provenance), never inferred by a
      separate tracer model.

### [REQ-4] Tamper-Evident, Hash-Chained Decision Log

The per-agent account is made trustworthy: the log is append-only and each record is
chained to the previous one.

#### Acceptance Criteria
- [x] Each `DecisionRecord` includes the hash of the previous record (a hash chain);
      the existing per-record SHA-256 is retained.
- [x] A verification pass detects any insertion, deletion, reorder, or edit anywhere
      in the log (not only a torn trailing record), and reports the broken position.
- [x] The chain is computed deterministically and cross-platform (canonical JSON,
      `\n` line endings) so the log — and thus replay — stays byte-identical across OSes.

### [REQ-5] Surface Attribution (CLI + JSON + console)

The swarm replay and its attribution are reachable from the host control plane and
the console.

#### Acceptance Criteria
- [x] `jaros replay` reports a per-agent summary (decisions per `source`) and, on
      divergence/failure, the attributed agent + decision; `--json` includes
      `{decisions, byAgent, modelCalls:0, finalState, byteIdentical, attribution, ok}`.
- [x] Exit codes match EXT-008: `0` reproducible, `1` divergence (with attribution),
      `2` nothing to replay.
- [x] The console Replay view shows the per-agent breakdown and highlights the
      attributed agent/decision on a divergence (no new server; host-side bridge).

### [REQ-6] Swarm Reference Demo

A runnable, multi-agent example proves the apex purpose end to end.

#### Acceptance Criteria
- [x] A small hive (e.g. planner → worker → reviewer) runs end-to-end and records one
      ordered, per-agent decision log.
- [x] `jaros replay` reproduces the hive to byte-identical state with zero model
      calls, and — for a seeded bad handoff — pinpoints the member that produced it.
- [x] The demo needs no infrastructure (files + threads), and is the launch's headline
      "replay a swarm, find the culprit" proof.
