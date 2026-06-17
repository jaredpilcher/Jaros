# Design — Build Mode & Locked Mode (Supervised Authoring + Freeze)

A **future** spec. The runtime already separates non-deterministic reasoning from a
deterministic execution plane and can author (agent-kit), evaluate (evals), and
reproduce/attribute (replay) a system. EXT-016 adds a *lifecycle* around that: an AI
supervisor mutates the deterministic system at **build time**, a gate proves it, and
a **freeze** seals it for **production** — where it is immutable, reproducible, and
attributable. It is mostly composition; the one new primitive is the **seal /
manifest** and the **Build → Locked** mode switch.

## The lifecycle

```text
   BUILD MODE (mutable)                         LOCKED MODE (immutable)
   ┌───────────────────────────────┐  gate    ┌──────────────────────────────┐
   │ supervisor authors / mutates: │  ┌────┐   │ deterministic plane FROZEN   │
   │  agents · tools · handlers ·  │  │PASS│   │  - no authoring (fail-closed)│
   │  harness rules · validators · │─►│    │──►│  - only inert decisions flow │
   │  state model · evals          │  │evals│  │  - LLM demoted to proposals  │
   │                               │  │ +   │   │    (or removed)             │
   │ verify: jaros eval +          │  │replay│  │ reproducible + attributable │
   │         jaros replay (==) +   │  │ +   │   │ (EXT-008 / EXT-015)         │
   │         check_determinism     │  │det. │   │ sealed by a manifest hash    │
   └───────────────────────────────┘  └────┘   └──────────────────────────────┘
          (staging data dir)        promote+seal      (production data dir)
```

The gate is mechanical: evals green, a recorded run replays byte-identically, and
the determinism check is clean. A human approves before the freeze (AI-authored,
human-approved).

## What "freeze" means concretely

The deterministic artifact set is enumerated and content-hashed into one manifest:

- the registered executor **handlers** + custom **tools**;
- the **harness rule set** (already frozen at construction, EXT-005);
- the decision-gate **validators**;
- the **state model** (states + transitions);
- the **agent set** (the boundaries permitted to run).

The manifest hash (canonical serialization, reusing EXT-015's hashing) names the
exact deployed configuration. On boot in Locked Mode the runtime recomputes the hash
over what it loaded and refuses to start on a mismatch — so prod can *prove* it runs
the approved system, with no server, database, or broker.

## Reuse map (this is mostly composition)

| Need | Existing primitive |
| --- | --- |
| Author / mutate the system | EXT-014 agent-kit (Jaros is AI-authorable) |
| Evaluate a candidate | EXT-013 evals + `jaros eval` |
| Prove reproducibility/determinism | EXT-008/EXT-015 replay + `check_determinism` |
| Attribute behavior | EXT-015 swarm attribution |
| Immutability of the harness rules | EXT-005 (rules frozen at construction) |
| Tamper-evident hashing | EXT-015 hash chain |
| New: seal/manifest + Build↔Locked mode | EXT-016 |

## Invariants

- Build Mode is mutable and runs only against a staging data dir; Locked Mode is
  immutable. A supervisor can never mutate a Locked system.
- Promotion requires the mechanical gate (evals + byte-identical replay + clean
  determinism check) and a human approval; the gate inputs are recorded.
- A Locked system refuses (fail-closed) any attempt to author/register/mutate the
  deterministic plane, and verifies its manifest hash on boot.
- Freeze adds no infrastructure (zero-infra, P3) and no crypto/blockchain — it is
  practical, auditable accountability.
- Jaros supplies the *freeze + verification + reproducibility + attribution* — not
  the supervisor's problem-solving intelligence.

## Competitive note (why this is the lane)

Generation is crowded (ADAS / Meta Agent Search; self-improving coding agents).
DSPy compiles to a deterministic, reloadable artifact — but freezes the *prompt
program*; at runtime the LLM still drives (no deterministic executor, no replay, no
attribution; "recompile on drift"). EXT-016 freezes the **deterministic execution
itself** into a sealed, **replayable, attributable, tamper-evident** prod artifact,
and frames the freeze as the **safety boundary** for self-improvement — a position
the 2026 literature (which mitigates self-improvement with observability + human
oversight) does not occupy.
