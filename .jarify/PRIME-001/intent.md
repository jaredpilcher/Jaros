# Intent

Jaros aims to be the **zero-infrastructure runtime that makes agent systems
reproducible, testable, and capability-safe by construction.** It is the runtime
an agent reaches for the day it leaves the demo — when non-determinism has made
it impossible to reproduce, and ambient power has made it unsafe to ship — and it
must deliver that without a server, a database, or a broker: just files and
threads.

To achieve this, Jaros decouples non-deterministic AI reasoning from
deterministic system execution. The LLM is treated as an interchangeable
application that may only **propose** inert, serializable `Decision` data; a
deterministic execution plane — a durable, crash-recoverable, deterministically
replayable state machine governed by an architectural harness — decides whether
and how each decision runs, and may reject it. Agents run as lightweight
computing threads, not microservices. All communication flows exclusively through
rigid queues and a shared file system; there are no direct agent-to-agent calls.

Two properties are the point; every architectural choice exists to serve them:

- **Reproducibility by replay.** Because reasoning emits only inert data and a
  deterministic executor performs every effect, recording the decision log and
  replaying it must reconstruct an entire agent run to byte-identical state. This
  is record-and-replay of non-determinism — not state-snapshot rewind.
- **Capability-safety by construction.** Because agents hold only the scoped
  handles the harness grants, a misbehaving agent cannot reach what it was never
  given. Blast radius is bounded structurally, and every action leaves an
  auditable record.

## What Jaros aims to be

- A **zero-infrastructure runtime** — no server, no database, no broker; it runs
  anywhere files work.
- A **determinism-and-replay engine** for agents — reproduce the exact run from
  the recorded decision log.
- A **capability-safe execution model** — least-privilege handles, default-deny
  mediation, an auditable record of every action.
- The **graduation layer** between a prototype (LangGraph, CrewAI) and
  heavyweight durable-execution infrastructure (Temporal, Dapr).

## What Jaros is not

Holding these boundaries is part of the directive; claiming more than the
architecture can deliver is itself a defect.

- **Not a hardened security sandbox.** Capability scoping is structural
  least-privilege for correctness and blast-radius control — not an adversarial
  boundary against hostile code sharing the interpreter. Real isolation is
  delegated to the host (process, container, VPC).
- **Not a cluster-scale distributed system.** The shared-file-system control
  plane is single-node-first, with bounded multi-node coordination; it does not
  aim to replace Temporal or Dapr at cluster scale.
- **Not an agent-authorization gateway or governance product.** It does not
  compete with policy gateways (AWS Bedrock AgentCore, Permit.io); it is a
  runtime that happens to be auditable.
- **Not a prototyping framework** optimized for hello-world ergonomics. Its value
  is reproducibility and safety, felt when an agent ships — not in the first ten
  lines.
- **Not "unbreakable."** It aims to be durable, crash-recoverable, and
  replayable — claims it can keep.
