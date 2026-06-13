# Design — Jaros Prime Directive

This document describes the system-wide architecture the intent demands. It is
intentionally high-level: it constrains *how* every feature spec must fit
together, not the internals of any single feature. Each feature spec (`EXT-00x`)
realizes one tenet of the intent and must remain consistent with this design.

This directive is a **target**. Where the current system or a feature spec does
not yet satisfy a tenet below, it is the spec and the code that must change to
match the directive — not the directive that bends to the code.

## Purpose

Jaros exists to make agent systems **reproducible, testable, and capability-safe
by construction — with zero infrastructure.** Every architectural choice below is
a means to that end, not an end in itself. The system is the runtime an agent
reaches for the day it leaves the demo: when non-determinism has made it
impossible to reproduce, and ambient power has made it unsafe to ship.

It delivers this through two properties that must fall out of the architecture:

- **Deterministic replay.** Because the LLM emits only inert `Decision` data and
  a deterministic executor performs all effects, recording the decision log and
  replaying it must reconstruct an agent run to byte-identical state. This is
  record-and-replay of non-determinism, not state-snapshot rewind.
- **Capability-safety.** Because agents hold only the scoped handles the harness
  grants, a misbehaving agent cannot reach what it was never given. Blast radius
  is bounded structurally, and every action is an auditable record.

## What Jaros Is — and Is Not

These boundaries are load-bearing. They tell every feature spec where to invest
and, equally, where *not* to overbuild.

**Jaros is:**

- A **zero-infrastructure runtime** — no server, no database, no broker; just
  files and threads. It runs anywhere files work.
- A **determinism-and-replay engine** for agents — reproduce the exact run from
  the recorded decision log.
- A **capability-safe execution model** — least-privilege handles, default-deny
  mediation, an auditable record of every action.
- The **graduation layer** between a prototype (LangGraph, CrewAI) and
  heavyweight durable-execution infrastructure (Temporal, Dapr).

**Jaros is not:**

- **Not a hardened security sandbox.** Capability scoping is structural
  least-privilege for correctness and blast-radius control — not an adversarial
  boundary against hostile code sharing the interpreter. Real isolation is
  delegated to the host (process, container, VPC). Specs must not market or rely
  on in-process guards as an adversarial security boundary.
- **Not a cluster-scale distributed system.** The shared-file-system control
  plane is single-node-first, with bounded multi-node coordination over the
  shared file system. It does not replace Temporal or Dapr at cluster scale, and
  specs must not add cluster-scale machinery (consensus services, brokers) that
  would break the zero-infrastructure tenet.
- **Not an agent-authorization gateway or governance product.** It does not
  compete with policy gateways (AWS Bedrock AgentCore, Permit.io); it is a
  runtime that happens to be auditable.
- **Not a prototyping framework** optimized for hello-world ergonomics. Its value
  is reproducibility and safety, felt when an agent ships — not the first ten
  lines.
- **Not "unbreakable."** It is durable, crash-recoverable, and replayable —
  claims it can keep.

## Architectural Overview

Jaros is split into two planes that must never merge:

- **The Reasoning Plane** — non-deterministic. AI agents (running as lightweight
  threads) think and propose decisions. The LLM lives here as an interchangeable
  application.
- **The Execution Plane** — deterministic. A durable, crash-recoverable,
  deterministically replayable state machine and its harness validate and execute
  decisions, persist state, and route all communication. It is single-node-first,
  with bounded multi-node coordination over the shared file system.

The only paths between an agent and the rest of the system are **rigid queues**
and the **shared file system**. There are no direct agent-to-agent calls.

## Plane Separation (EXT-001, EXT-004)

```text
            REASONING PLANE (non-deterministic)
   +-------------------------------------------------+
   |   Agent Thread        Agent Thread     ...      |
   |   +-----------+       +-----------+              |
   |   |  reason   |       |  reason   |              |
   |   |  (LLM as  |       |  (LLM as  |              |
   |   | pluggable |       | pluggable |              |
   |   |    app)   |       |    app)   |              |
   |   +-----+-----+       +-----+-----+              |
   +---------|-------------------|-------------------+
             | decisions only    | decisions only
             v                   v
   ==================== HARNESS BOUNDARY ====================
             |  (validate · constrain · mediate · record)
             v
   +-------------------------------------------------+
   |          EXECUTION PLANE (deterministic)        |
   |                                                 |
   |   Durable, Replayable State Machine             |
   |        (crash-recoverable · deterministic)      |
   +-------------------------------------------------+
```

Decisions flow down; nothing in the Execution Plane reaches up to invoke
reasoning inline.

## The LLM Decides *What*, Not *How*

A frequent misreading of this design is "the LLM can't make decisions." It can —
that *is* the reasoning. The precise rule is:

> **The LLM decides WHAT to propose. The deterministic system decides HOW — and
> whether — it runs.**

The LLM absolutely makes judgment calls. What it cannot do is perform a side
effect directly, mutate system state, control the flow of execution, or decide
whether its own decision is carried out. A `Decision` (EXT-001) **is** the LLM's
decision — captured as inert, serializable data. The model says *"I think we
should do X"*; that proposal crosses a validation gate; only then does the
deterministic Execution Plane decide whether and how to actually do X, and it may
reject it outright.

The LLM is an **advisor** writing recommendations on slips of paper. A
deterministic **clerk** (the harness + state machine) reads each slip, checks it
against the rulebook, and either executes it exactly or rejects it. The advisor
makes real judgments but never touches the levers, never controls the machinery,
and never decides if the advice is followed. Its entire interface with the world
is **data in → data out**.

```text
  typical agent:   LLM ── tool call ──► side effect happens   (LLM drives execution)

  jaros:           LLM ── Decision (data) ──► [gate] ──► executor   (executor drives execution)
                                                 │
                                                 └─► may REJECT; LLM has no say
```

This separation is *why* the purpose holds:

- **Reproducibility** is possible because the only non-determinism (the model's
  output) is captured as inert `Decision` data; replaying the recorded decisions
  through the deterministic executor reconstructs the run exactly.
- The LLM is **interchangeable** (EXT-004) precisely because it holds no control —
  swap the model and nothing about how the system runs changes.
- The **state machine stays deterministic** (EXT-002) because transitions are
  invoked by the executor, never by the model.
- The **harness can bound agents** (EXT-005) because an agent can only ever hand
  over a slip of paper, not pull a lever.

The non-determinism is allowed to influence *what* happens, but is structurally
barred from *executing* it.

## Reproducibility by Replay (EXT-001, EXT-002)

Reproducibility is a first-class goal, not a side effect of durability. The
durable log must capture enough to **re-execute a run deterministically**, not
merely to recover the last state:

- Every accepted `Decision` is recorded as inert data, in order, before its
  effects are observable.
- Replaying the recorded decisions through the deterministic executor must yield
  byte-identical state — the recorded model outputs stand in for the
  non-deterministic reasoning, exactly as record-and-replay injects logged
  non-deterministic inputs.
- A run is therefore debuggable and testable with ordinary software-engineering
  tools: pin the decision log, replay, reproduce, fix, re-run identically.

```text
   record:   reasoning ─► Decision(data) ─► [gate] ─► executor ─► state
                              │
                              └─► append to durable decision log

   replay:   decision log ─────────────────► executor ─► identical state
             (no model call; recorded decisions are the inputs)
```

## Communication Fabric (EXT-006)

Agents never talk to each other directly. Every exchange is through a queue or
the shared file system, both governed by the harness.

```text
   Agent A (thread)                         Agent B (thread)
        |                                        ^
        | enqueue                                | dequeue
        v                                        |
   +---------------------- RIGID QUEUES ----------------------+
   |   [ task-q ] -> [ work-q ] -> [ result-q ] -> ...        |
   +---------------------------------------------------------+
        |                                        ^
        | write                                  | read
        v                                        |
   +------------------- SHARED FILE SYSTEM -------------------+
   |   /state   /inbox   /outbox   /artifacts                 |
   +---------------------------------------------------------+

   (No direct A -> B in-memory / RPC / network channel exists.)
```

## The Harness (EXT-005)

The harness is the unyielding mediator. Agents run *inside* it; they cannot
redefine its rules. It grants only capability-scoped handles and records every
action it mediates.

```text
   +=========================== HARNESS ===========================+
   |                                                               |
   |   spawn/teardown   validate I/O   enforce transitions         |
   |        |                |                |                    |
   |        v                v                v                    |
   |   [ lightweight agent threads ]   [ scoped capability handles ]|
   |                                                               |
   |   Rules are architectural (code/config) — not negotiable      |
   |   by agents at runtime. Default-deny: no grant, no access.    |
   +===============================================================+
```

Capability-safety here is **structural least-privilege**: an agent reaches only
what it was granted, so a bug or bad decision cannot touch the rest of the
system. It is not an adversarial sandbox; isolation against hostile code is the
host's job (process, container, VPC).

## Durable, Replayable State Machine (EXT-002, EXT-003)

State is explicit, durable, and deterministically replayable. Agents are cheap
threads attached to the machine — not services. Distribution is bounded:
coordination across nodes happens over the shared file system, single-node-first.

```text
   +-------------------+        transition (validated)
   |   State: PENDING  | ---------------------------+
   +-------------------+                            v
            ^                              +-------------------+
            | recover by deterministic     |  State: RUNNING  |
            | replay of the durable log    +-------------------+
            |                                       |
   +-------------------+                            |
   |  Durable Log       | <--------------------------+
   |  (append-only)     |        persist every transition
   +-------------------+
            |
            +--> invalid transition? REJECTED (machine never enters undefined state)
```

## Specification Map

Each tenet of the intent is decomposed into feature specifications. The *purpose
tenets* (P) state the ends; the *mechanism tenets* (REQ) state the means that
realize them. Every spec must stay consistent with this design and the intent.

```text
   PRIME-001 (intent)
       |
       |  PURPOSE (the ends)
       +-- P1 reproducible by replay ........... EXT-001 + EXT-002
       +-- P2 capability-safe by construction .. EXT-005
       +-- P3 zero-infrastructure .............. EXT-006 + EXT-007
       +-- P4 graduation-layer scope ........... whole-system constraint
       |
       |  MECHANISM (the means)
       +-- REQ-1 decouple reasoning/execution .. EXT-001  Reasoning / Execution Boundary
       +-- REQ-2 durable, replayable state ..... EXT-002  Distributed State Machine
       +-- REQ-3 agents as lightweight threads . EXT-003  Agent Thread Runtime
       +-- REQ-4 LLM is an interchangeable app . EXT-004  Interchangeable LLM Adapter
       +-- REQ-5 unyielding architectural harness EXT-005 Architectural Harness
       +-- REQ-6 queues + shared FS only ....... EXT-006  Communication Fabric
```

| Purpose tenet | Realized by | Means |
| --- | --- | --- |
| P1 Reproducible by replay | EXT-001, EXT-002 | Inert `Decision` log re-executed deterministically to identical state |
| P2 Capability-safe by construction | EXT-005 | Least-privilege scoped handles, default-deny mediation, auditable record |
| P3 Zero-infrastructure | EXT-006, EXT-007 | Files + threads only; no server, database, or broker required to run |
| P4 Graduation-layer scope | whole system | Reproducibility and safety for shipping agents — not prototyping ergonomics, not cluster scale |

| Mechanism tenet | Spec | Owns |
| --- | --- | --- |
| REQ-1 Decouple reasoning from execution | EXT-001 | Inert `Decision` contract, reasoning boundary, validation gate |
| REQ-2 Durable, replayable state machine | EXT-002 | Explicit transitions, durable decision log, deterministic replay, recovery |
| REQ-3 Agents as lightweight threads | EXT-003 | Cheap agent lifecycle, bounded pool, fault containment |
| REQ-4 LLM is an interchangeable application | EXT-004 | Single `LlmClient` interface, pluggable adapters, config swap |
| REQ-5 Unyielding architectural harness | EXT-005 | Mediated actions, non-bypassable rules, capability-scoped handles |
| REQ-6 Communication via queues + shared FS | EXT-006 | Rigid queues, shared FS layout, exclusivity enforcement |

## Design Invariants (must hold for every feature spec)

- Reasoning emits data only; the harness performs all side effects.
- Every accepted action is recorded as inert data; replaying the decision log
  reconstructs the run deterministically, to byte-identical state.
- Agents hold only capability-scoped handles — no ambient authority; mediation is
  default-deny.
- The model is reachable through one interface and is swappable with zero harness
  changes.
- Agents are threads with cheap lifecycle — never per-agent services.
- The only inter-agent channels are rigid queues and the shared file system.
- Every state transition is explicit, validated, and durable.
- The runtime requires no external server, database, or broker to run.
- The directive claims only what the architecture delivers: durable, replayable,
  and capability-bounded — never "unbreakable," never an adversarial sandbox,
  never cluster-scale.

## Realization Guidance (for reconciling specs to this directive)

Where today's specs lag the directive, the following are the likely changes a
reconciling pass should make. This is guidance, not an exhaustive backlog.

- **Decision-log replay (P1, EXT-001/EXT-002).** The durable log must record the
  accepted `Decision` payloads — the model's outputs — not only `(event, state)`
  transitions, so a run can be re-executed deterministically rather than merely
  recovered to its last state. Recovery becomes a special case of replay.
- **Capability framing (P2, EXT-005).** State capability scoping as structural
  least-privilege and blast-radius control. Do not assert in-process guards as an
  adversarial security boundary; document host-level isolation as the security
  boundary.
- **Zero-infrastructure (P3, EXT-006/EXT-007).** Add an explicit invariant and an
  architecture check that the runtime starts and runs with no external server,
  database, or message broker — only the local/shared file system and threads.
- **Scope honesty (P4, EXT-002).** Characterize distribution as single-node-first
  with bounded multi-node coordination over the shared file system; do not
  introduce cluster-scale dependencies that would violate P3.
- **Language.** Purge "unbreakable" and unqualified "distributed" from specs and
  docs in favor of "durable, crash-recoverable, deterministically replayable" and
  "single-node-first, bounded multi-node."
