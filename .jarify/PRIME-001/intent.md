# Intent

Jaros aims to be the **runtime that makes a *swarm* of AI agents reproducible and
accountable — with zero infrastructure.**

The field is moving from one "super-agent" to **swarms of many small, specialized
agents**, and cheap small models make hives of hundreds or thousands economical.
But at swarm scale the two hard problems *compound*: non-determinism means you
cannot **reproduce** a failure, and shared autonomy means you cannot say **which
agent caused it**. When a swarm "does something wrong," replaying the request never
reproduces it, and the logs show only surface chatter — not which agent's decision
was to blame. That is the defining unsolved problem of multi-agent systems, and it
is the problem Jaros exists to solve.

Jaros makes a hive of agents **replayable to byte-identical state** and **every
outcome attributable to the exact agent and decision that caused it** — and it
bounds each agent so one bad member can't reach what it was never given. A single
agent is simply the **swarm of one**: the same mechanism at N=1.

To achieve this, Jaros decouples non-deterministic AI reasoning from deterministic
system execution. Each agent — a lightweight computing thread, not a microservice —
may only **propose** inert, serializable `Decision` data; a deterministic execution
plane governed by an architectural harness decides whether and how each decision
runs, and may reject it. Every accepted decision is recorded, in order, **tagged
with its source agent**, to a durable, tamper-evident log. All communication flows
through rigid queues and a shared file system; there are no direct agent-to-agent
calls — coordination is **mediated**, which is exactly what makes the swarm
reproducible.

Three properties are the point; every architectural choice exists to serve them:

- **Reproducibility by replay.** Recording the decision log and replaying it
  reconstructs an entire run — single agent or whole swarm — to byte-identical
  state, with no model call. Record-and-replay of non-determinism, not
  state-snapshot rewind.
- **Accountability by provenance.** Every decision carries its source agent and is
  recorded to a tamper-evident log, so any outcome is attributable to the exact
  agent and decision that produced it — by recorded fact, not post-hoc inference.
- **Capability-safety by construction.** Each agent holds only the scoped handles
  the harness grants, so a misbehaving member of the swarm cannot reach what it was
  never given. Blast radius is bounded structurally.

## What Jaros aims to be

- The **reproducible, accountable substrate for micro-agent swarms** — a flight
  recorder for a hive of agents: replay the swarm, attribute any failure to the
  exact agent and decision.
- A **zero-infrastructure runtime** — no server, no database, no broker; a hive of
  agents runs as cheap threads. It runs anywhere files work.
- A **determinism-and-replay engine** — reproduce the exact run from the recorded
  decision log.
- A **capability-safe, provenance-tracked execution model** — least-privilege
  handles, default-deny mediation, and a tamper-evident, per-agent-attributable
  record of every action.
- The **graduation layer** between a prototype (LangGraph, CrewAI) and heavyweight
  durable-execution infrastructure (Temporal, Dapr).

## What Jaros is not

Holding these boundaries is part of the directive; claiming more than the
architecture can deliver is itself a defect.

- **Not a swarm-orchestration / coordination framework.** Jaros is the substrate a
  swarm runs *on* — it makes coordination reproducible and accountable; it does not
  supply the coordination *intelligence* (task decomposition, supervisor logic,
  emergent strategy). It composes *under* an orchestrator (OpenAI Agents SDK,
  CrewAI, LangGraph); it does not replace one.
- **Not a planet-scale or peer-gossip swarm runtime.** A hive of many agents on a
  node, with bounded multi-node coordination over the shared file system — **not**
  Ray/Akka cluster scale, and **not** free-form agent-to-agent gossip. Coordination
  is mediated through the deterministic plane on purpose; that mediation is what
  makes it reproducible.
- **Not a hardened security sandbox.** Capability scoping is structural
  least-privilege and blast-radius control — not an adversarial boundary against
  hostile code sharing the interpreter. Real isolation is delegated to the host
  (process, container, VPC).
- **Not a cryptographic / blockchain "verifiable execution" system.** Its
  tamper-evident decision log and deterministic replay give practical, auditable
  accountability — not trustless on-chain proof. (That per-agent record *does* align
  with emerging accountability expectations such as EU AI Act Article-12-style
  logging — a tailwind and a future commercial layer, not the core product's claim.)
- **Not an agent-authorization gateway or governance product.** It does not compete
  with policy gateways (AWS Bedrock AgentCore, Permit.io); it is a runtime that
  happens to be auditable.
- **Not a prototyping framework** optimized for hello-world ergonomics. Its value is
  reproducibility and accountability, felt when a swarm ships — not in the first ten
  lines.
- **Not "unbreakable."** It aims to be durable, crash-recoverable, replayable, and
  attributable — claims it can keep.
