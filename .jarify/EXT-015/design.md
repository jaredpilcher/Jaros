# Design — Swarm Replay & Attribution

A swarm is already a hive of agent threads (EXT-003) whose every accepted decision
is already recorded, with its `source`, to one durable log (EXT-001/EXT-002). So
swarm replay is not a new mechanism — it is the existing record-and-replay applied
to the *whole* log, plus two additions: **attribution** (read provenance off the
log) and a **hash chain** (make the account tamper-evident). No new infrastructure,
no agent-to-agent channel.

## One ordered log is the whole swarm

```text
   Agent A   Agent B   Agent C   ...        (a hive of threads, EXT-003)
       \        |        /
        \       |       /   decisions only (each tagged with its source)
         v      v      v
   ===================== HARNESS BOUNDARY (EXT-005) =====================
         |  validate · mediate · RECORD (ordered · per-agent · hash-chained)
         v
   +---------------------------------------------------------------+
   |   one durable decision log  ── replay_swarm ──►  byte-identical|
   |   (EXT-002)                                       swarm state +|
   |                                                  per-agent blame|
   +---------------------------------------------------------------+
```

Coordination is mediated, never peer-to-peer — that is the price of, and reason
for, reproducibility: the whole hive's decisions land in *one* replayable transcript.

## Replay is the N=1 case generalized

`jaros replay` (EXT-008) already replays one run's decisions into a sandbox and
checks byte-identity. Swarm replay reuses that path verbatim — `replay(decision_log,
executor.apply, log=sandbox_log)` over the runtime handlers — because a multi-agent
run is simply a longer decision log whose records carry different `source` values.
The single agent is the swarm of one.

```text
   record:  A,B,C reason ─► Decision(data, source=…) ─► [gate] ─► executor ─► state
                                   │
                                   └─► append to ONE hash-chained decision log

   replay:  decision log ──────────────────────────► executor ─► identical state
            (no model call; recorded decisions are the inputs)

   attribute: on divergence/failure at record N
            ─► report { index: N, id, source }  ← which agent, which decision
```

## Attribution by recorded fact

Attribution is a query over the log, not an inference:

- **Divergence:** replay twice (or vs the live `transitions.log`); the first record
  whose effect differs is the culprit — report its `index`, `id`, `source`.
- **Failure:** a replayed decision that the gate refuses or whose handler raises is
  the culprit — report it plus the reason.
- **Per-agent summary:** group the log by `source` for a "who did how much" view.

`jaros/state/swarm.py` houses `replay_swarm(...)` and `attribute(...)`; the CLI and
console call them. `Decision.source` already carries the identity, so this is
additive — no change to the reasoning boundary or the harness.

## Tamper-evident hash chain

`DecisionRecord` gains `prev` (the previous record's checksum); `checksum` covers
`{index, prev, decision}`. Reading verifies the chain end-to-end and reports the
first broken link — detecting insertion, deletion, reorder, or edit, not only a torn
tail. The chain is computed over canonical JSON with `\n` endings so the log stays
byte-identical across OSes (matching EXT-002's cross-platform guarantee). This is the
practical, EU-AI-Act-Article-12-shaped accountability — without crypto or blockchain.

> **Log format note.** Adding `prev` to the checksum changes the `decisions.log`
> record format. A `decisions.log` written *before* EXT-015 will not pass
> `verify_chain` (its records have no `prev`); the log is per-run, so start a fresh
> data dir rather than mixing formats. Appends stay O(1): `DecisionLog` caches the
> last checksum + count in memory and updates them on append, so a hive of thousands
> of decisions never re-reads the whole log per record (`read`/`verify_chain` still
> do a full read, which is correct there).

## Invariants

- One node, one ordered, hash-chained decision log; a swarm replays as that one log.
- Attribution comes from recorded `source` provenance — never a separate tracer model.
- Swarm replay reuses the runtime handlers and an isolated sandbox; it constructs no
  `LlmClient`, makes zero model calls, and mutates nothing in the live data dir.
- No agent-to-agent channel and no cluster-scale machinery is added; coordination
  stays mediated through the deterministic plane (single-node-first, bounded
  multi-node over the shared FS).
- Jaros supplies reproducibility and accountability for the swarm — not its
  coordination intelligence.
