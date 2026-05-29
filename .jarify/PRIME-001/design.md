# Design — Jaros Prime Directive

This document describes the system-wide architecture the intent demands. It is intentionally high-level: it constrains *how* every feature spec must fit together, not the internals of any single feature. Each feature spec (`EXT-00x`) realizes one tenet of the intent and must remain consistent with this design.

## Architectural Overview

Jaros is split into two planes that must never merge:

- **The Reasoning Plane** — non-deterministic. AI agents (running as lightweight threads) think and propose decisions. The LLM lives here as an interchangeable application.
- **The Execution Plane** — deterministic. An unbreakable, distributed state machine and its harness validate and execute decisions, persist state, and route all communication.

The only paths between an agent and the rest of the system are **rigid queues** and the **shared file system**. There are no direct agent-to-agent calls.

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
             |  (validate · constrain · mediate)
             v
   +-------------------------------------------------+
   |          EXECUTION PLANE (deterministic)        |
   |                                                 |
   |     Unbreakable Distributed State Machine       |
   |        (durable, crash-recoverable)             |
   +-------------------------------------------------+
```

Decisions flow down; nothing in the Execution Plane reaches up to invoke reasoning inline.

## Communication Fabric (EXT-006)

Agents never talk to each other directly. Every exchange is through a queue or the shared file system, both governed by the harness.

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

The harness is the unyielding mediator. Agents run *inside* it; they cannot redefine its rules.

```text
   +=========================== HARNESS ===========================+
   |                                                               |
   |   spawn/teardown   validate I/O   enforce transitions         |
   |        |                |                |                    |
   |        v                v                v                    |
   |   [ lightweight agent threads ]   [ queue + FS access ]       |
   |                                                               |
   |   Rules are architectural (code/config) — not negotiable      |
   |   by agents at runtime.                                       |
   +===============================================================+
```

## Distributed State Machine (EXT-002, EXT-003)

State is explicit, durable, and distributed. Agents are cheap threads attached to the machine — not services.

```text
   +-------------------+        transition (validated)
   |   State: PENDING  | ---------------------------+
   +-------------------+                            v
            ^                              +-------------------+
            | recover from durable log     |  State: RUNNING  |
            |                              +-------------------+
   +-------------------+                            |
   |  Durable State    | <--------------------------+
   |  Store (replicated)|        persist every transition
   +-------------------+
            |
            +--> invalid transition? REJECTED (machine never enters undefined state)
```

## Specification Map

Each tenet of the intent is decomposed into exactly one feature specification. Every spec below must stay consistent with this design and with the Prime Directive intent.

```text
   PRIME-001 (intent)
       |
       +-- REQ-1 decouple reasoning/execution ......... EXT-001  Reasoning / Execution Boundary
       +-- REQ-2 unbreakable distributed state machine  EXT-002  Distributed State Machine
       +-- REQ-3 agents as lightweight threads ........ EXT-003  Agent Thread Runtime
       +-- REQ-4 LLM is an interchangeable app ........ EXT-004  Interchangeable LLM Adapter
       +-- REQ-5 unyielding architectural harness ..... EXT-005  Architectural Harness
       +-- REQ-6 queues + shared FS only .............. EXT-006  Communication Fabric
```

| Prime tenet | Spec | Owns |
| --- | --- | --- |
| REQ-1 Decouple reasoning from execution | EXT-001 | Inert `Decision` contract, reasoning boundary, validation gate |
| REQ-2 Unbreakable distributed state machine | EXT-002 | Explicit transition model, durable log, recovery, replication |
| REQ-3 Agents as lightweight threads | EXT-003 | Cheap agent lifecycle, bounded pool, fault containment |
| REQ-4 LLM is an interchangeable application | EXT-004 | Single `LlmClient` interface, pluggable adapters, config swap |
| REQ-5 Unyielding architectural harness | EXT-005 | Mediated actions, non-bypassable rules, capability-scoped handles |
| REQ-6 Communication via queues + shared FS | EXT-006 | Rigid queues, shared FS layout, exclusivity enforcement |

## Design Invariants (must hold for every feature spec)

- Reasoning emits data only; the harness performs all side effects.
- The model is reachable through one interface and is swappable with zero harness changes.
- Agents are threads with cheap lifecycle — never per-agent services.
- The only inter-agent channels are rigid queues and the shared file system.
- Every state transition is explicit, validated, and durable.
