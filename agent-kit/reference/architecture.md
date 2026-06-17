# Reference — architecture

The four ideas every Jaros artifact must respect. (Full intent lives in
`.jarify/PRIME-001/`.)

## 1. The Reasoning Plane emits inert data; the Execution Plane runs it

An **agent** reasons and returns `Decision` objects — immutable, JSON-serializable
data carrying `id`, `source`, `type`, and a `payload`. A decision holds **no**
callbacks, closures, or handles. The agent performs **no** side effect.

The model decides **WHAT** — and that choice must *drive* the decision: parse the
model's answer into the `type`, `payload`, or `events` the executor acts on, so a
different answer yields a different outcome. (Burying the model's text in a
cosmetic `note` while behaviour stays hardcoded means the model decided nothing.)
The deterministic Execution Plane then decides **HOW** — it validates the decision
(the gate) and dispatches it by `type` to a handler/tool that performs the effect.
Because the decision (with the model's choice in it) is recorded, replay
reconstructs the same outcome with no model call. This split is the whole game:

```text
  job input ──► Agent.decide() ──► [Decision data] ──► gate.validate() ──► tool.execute()
                (Reasoning Plane)                       (Execution Plane, deterministic)
```

## 2. Reproducible by replay

The only non-deterministic input to a run is the model's output — and it is
captured as inert `Decision` data in `state/decisions.log`. Re-applying that log
through the same deterministic handlers reconstructs the run **byte-identically,
with zero model calls** (`jaros replay`). For this to hold, **every `execute()`
must be deterministic**: no clock, no RNG, no network, no ambient I/O that varies.

## 3. Capability-safe by construction

Agents hold only the scoped capabilities the harness grants; every mediated action
is default-deny. An agent or tool cannot reach what it was not given. The safest
tool is **read-only** (reads, never writes). Real isolation against hostile code is
the host's job (process / container / VPC) — design for least privilege.

## 4. Zero infrastructure

No server, no database, no message broker. The shared file system is the only
substrate: jobs arrive in `inbox/`, agents load from `agents/`, tools from
`tools/`, results land in `outbox/`, and durable state lives in `state/`. Do not
introduce a network dependency, a DB client, or a broker — guardrails in
`scripts/` reject it.

## Where things live in a data dir

```text
<data-dir>/
├── inbox/        jobs to process            (jaros submit writes here)
├── outbox/       results the daemon wrote
├── agents/       your agent *.py            (loaded at runtime, no restart)
├── tools/        your custom tool *.py
├── evals/        your eval *.json
├── schedules/    your schedule *.json
└── state/        decisions.log, transitions.log, audit.log  (durable, replayable)
```

See also: [public-api.md](public-api.md) · [workflow.md](workflow.md)
