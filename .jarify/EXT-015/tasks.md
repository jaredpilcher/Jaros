# Implementation Tasks — Swarm Replay & Attribution

### [TASK-1] Guarantee per-agent provenance & global order for multi-agent runs

Make the single decision log a faithful, replayable transcript of the whole hive.

#### Steps
1. Confirm the daemon records **every** accepted decision from **every** agent to the
   one `state/decisions.log` in commit order (via the `on_accept` hook), serialized so
   concurrent agents never interleave a record or lose ordering.
2. Ensure `Decision.source` is always populated with the producing agent's id and is
   preserved through `record_decision` / `read_decisions`.
3. Add tests: a multi-agent run (≥3 agents, concurrent) yields a log whose order and
   per-`source` tagging exactly match the commit order.

#### Implements
- [REQ-1] Per-Agent Provenance & Global Order

### [TASK-2] Make the decision log tamper-evident (hash chain)

Chain each record to the previous so the per-agent account is trustworthy.

#### Steps
1. In `jaros/state/decision_log.py`, add `prev` (previous record's checksum) to
   `DecisionRecord`; fold `prev` into `compute_checksum({index, prev, decision})`.
   Genesis record uses a fixed sentinel (e.g. 64 zeros). Keep canonical JSON + `\n`.
2. Add `verify_chain(log)` that walks records confirming `index` continuity and
   `record.prev == previous.checksum`; return the first broken position (or OK).
3. Tests: a clean log verifies; an inserted/deleted/reordered/edited record is caught
   at the right position; cross-platform bytes unchanged.

#### Implements
- [REQ-4] Tamper-Evident, Hash-Chained Decision Log

### [TASK-3] Implement `replay_swarm` + `attribute`

Replay the whole log and locate the culprit on divergence/failure.

#### Steps
1. Create `jaros/state/swarm.py` with `replay_swarm(decision_log, *, handlers_setup)`
   that reuses EXT-008's sandbox approach (`register_runtime_handlers` over a temp
   `SharedFileSystem`+`TransitionLog`, `replay(...)`), constructing no `LlmClient`.
2. Add `attribute(...)`: on byte-divergence (vs a second replay or the live
   `transitions.log`) return the first diverging `{index, id, source}`; on a refused/
   raising decision return that record + reason; add `summary_by_agent(log)`.
3. Tests: byte-identical happy path; a seeded non-deterministic handler → attributed
   to the right `index`/`source`; a refused decision → attributed with reason.

#### Implements
- [REQ-2] Swarm Replay (whole hive → byte-identical)
- [REQ-3] Failure Attribution (which agent, which decision)

### [TASK-4] Surface attribution in the CLI and console

Make swarm replay + blame reachable from the host control plane and the console.

#### Steps
1. Extend `cmd_replay` in `jaros/cli.py` to add a per-agent summary and, on
   divergence/failure, the attributed agent + decision; extend `--json` to
   `{decisions, byAgent, modelCalls:0, finalState, byteIdentical, attribution, ok}`;
   keep exit codes `0`/`1`/`2`.
2. Update the console Replay view (host-side bridge, no new server) to show the
   per-agent breakdown and highlight the attributed agent/decision on a divergence.
3. Update `tests/test_cli_replay.py` for the new fields and the attribution path.

#### Implements
- [REQ-5] Surface Attribution (CLI + JSON + console)

### [TASK-5] Build the swarm reference demo

A runnable multi-agent example that proves the apex purpose.

#### Steps
1. Add a small hive (e.g. `planner → worker → reviewer`) under `examples/swarm/` with
   each agent as a `ReasoningBoundary` emitting decisions tagged by `source`.
2. Add a seam to seed a "bad handoff" by one member; a deterministic eval and an
   integration script (`tests/integration/run_swarm_replay_demo.py`).
3. Show `jaros replay` reproducing the hive byte-identically and pinpointing the
   culprit member; wire it into the README/launch as the headline "replay a swarm,
   find the culprit" demo.

#### Implements
- [REQ-6] Swarm Reference Demo

### [TASK-6] Verify guardrails and update the index

Keep the architecture honest and the traceability current.

#### Steps
1. Run the full suite + all architecture checks (`check_planes`, `check_no_server`,
   `check_comms`, `check_zero_infra`, `check_determinism`) — swarm replay must add no
   server, no broker, no agent-to-agent channel, and stay deterministic.
2. Populate `.jarify/EXT-015/index.json` with the real `REQ → file:lineRange` mappings
   once implemented, and flip `status` in `requirements.md` from `planned` to
   `covered`.

#### Implements
- [REQ-1] … [REQ-6] (traceability for all requirements)
