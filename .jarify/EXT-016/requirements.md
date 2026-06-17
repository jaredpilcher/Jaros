---
id: EXT-016
title: Build Mode & Locked Mode — Supervised Authoring + Freeze
status: planned
priority: medium
implementation: []
---

# Build Mode & Locked Mode — Supervised Authoring + Freeze

A **future** direction (north star), recorded so it is not lost. Use a build-time
supervisor agent to author/mutate the deterministic system, verify it, then
**freeze** it into a sealed, replayable, attributable production artifact. Realizes
Prime Directive tenets P1 (reproducible by replay), P2 (capability-safe), and P5
(swarm reproducibility & accountability) at the *system-construction* level. Builds
on EXT-005 (frozen harness rules), EXT-008/EXT-015 (replay + attribution), EXT-013
(evals), EXT-014 (the agent-kit / AI-authorability), and the EXT-015 hash chain.

> **Differentiation (validated 2026):** the *generation* side is crowded (ADAS /
> Meta Agent Search; self-improving coding agents). DSPy *compiles → a deterministic,
> reloadable artifact* — but freezes the **prompt program**, and at runtime the LLM
> still drives (no deterministic executor, no replay, no attribution). EXT-016
> freezes the **deterministic execution itself** and seals it into a **replayable,
> attributable, tamper-evident** prod artifact — the unoccupied lane.

### [REQ-1] Build Mode — Mutable Supervised Authoring

In Build Mode a supervisor may author and mutate the deterministic system to solve
a perceived problem, with the full verification toolchain available.

#### Acceptance Criteria
- [ ] A supervisor (an agent, or a human-driven loop) can create/modify agents,
      tools, executor handlers, harness rules, and eval cases via the agent-kit
      authoring surface — in a throwaway/staging data dir, never a Locked system.
- [ ] Every candidate change is testable in place with `jaros eval` and
      `jaros replay` (byte-identical) without leaving Build Mode.
- [ ] Build Mode performs no irreversible action; it only produces a *candidate*
      artifact set for the promotion gate.

### [REQ-2] Promotion Gate

A candidate is promotable only when it is proven reproducible, deterministic, and
correct by the existing guardrails.

#### Acceptance Criteria
- [ ] Promotion requires: the eval suite passes (`jaros eval` exit 0), a recorded
      run replays **byte-identically** (`jaros replay`), and the determinism check
      (`check_determinism`) is clean.
- [ ] The gate is mechanical and auditable: its inputs (eval results, replay hash,
      determinism result) are recorded, so "why was this approved" is answerable.
- [ ] A human approval step is supported (AI-authored, human-approved) before freeze.

### [REQ-3] Freeze & Seal (the Manifest)

Promotion freezes the deterministic artifact set and seals it with a verifiable
manifest.

#### Acceptance Criteria
- [ ] The frozen set is enumerated: registered handlers/tools, harness rule set,
      gate validators, the state model, and the agent set — with a content hash of
      each and a single manifest hash over all of them.
- [ ] The manifest is durable and tamper-evident (reusing the EXT-015 hashing), so
      the exact deployed configuration is identifiable and verifiable later.
- [ ] Freezing is deterministic and cross-platform (canonical serialization), so the
      same artifact set yields the same manifest hash on any OS.

### [REQ-4] Locked Mode — Immutable Production

In Locked Mode the deterministic plane is immutable; only inert decisions flow.

#### Acceptance Criteria
- [ ] In Locked Mode, any attempt to author/register/mutate a handler, tool, rule,
      validator, or the state model is **refused** (fail-closed) and recorded.
- [ ] The reasoning plane (if present) may only emit inert `Decision` data; the LLM
      may be demoted to proposals or removed entirely without changing behavior.
- [ ] A Locked run is reproducible and attributable exactly as EXT-008/EXT-015
      guarantee — the frozen system replays byte-identically and blames the exact
      agent/decision on any failure.

### [REQ-5] Verifiable Deployment

A deployed system can prove it is running the exact approved, frozen artifact.

#### Acceptance Criteria
- [ ] On boot in Locked Mode, the runtime recomputes the manifest hash over the
      loaded artifact set and verifies it matches the sealed manifest; a mismatch
      fails closed (refuses to start) with a clear report.
- [ ] The manifest + verification require no external server, database, or broker
      (zero-infrastructure, P3) and no crypto/blockchain — practical, auditable
      accountability, not trustless proof.

### [REQ-6] The Supervisor Loop (build-time agent)

An optional supervisor agent drives Build Mode toward a passing candidate.

#### Acceptance Criteria
- [ ] Given a problem statement / target evals, the supervisor authors and iterates
      a candidate artifact set (perceive → author/mutate → eval → replay → repeat).
- [ ] The supervisor runs only in Build Mode, against a staging data dir; it cannot
      touch a Locked system.
- [ ] Its entire authoring trace is itself recorded (decisions + provenance), so the
      *construction* of the frozen system is as reproducible and attributable as its
      execution.
