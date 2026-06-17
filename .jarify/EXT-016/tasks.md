# Implementation Tasks — Build Mode & Locked Mode (planned / future)

> Recorded for the roadmap. **Not** in the current build queue — the apex swarm work
> (EXT-015) and the launch come first. Sequence when this becomes active.

### [TASK-1] Define the artifact set + seal/manifest

#### Steps
1. Enumerate the deterministic artifact set: registered handlers/tools, harness rule
   set, gate validators, state model, agent set.
2. Add a deterministic, cross-platform content hash per artifact and a single
   `manifest` hash over all of them (reuse EXT-015's canonical hashing).
3. Persist the sealed manifest under `state/` (durable, tamper-evident).

#### Implements
- [REQ-3] Freeze & Seal (the Manifest)

### [TASK-2] Add the Build ↔ Locked mode switch

#### Steps
1. Add a runtime mode flag (Build vs Locked), persisted in the data dir.
2. In Locked Mode, make handler/tool/rule/validator/state-model registration
   fail-closed (refused + recorded); permit only inert decision flow.
3. On boot in Locked Mode, recompute the manifest hash and refuse to start on a
   mismatch, with a clear report.

#### Implements
- [REQ-4] Locked Mode — Immutable Production
- [REQ-5] Verifiable Deployment

### [TASK-3] Implement the promotion gate

#### Steps
1. A `jaros promote` (or equivalent) that runs the eval suite, a byte-identical
   replay, and the determinism check, records their results, and — on pass + human
   approval — seals the manifest and switches the (copied) system to Locked Mode.
2. Never mutate the staging system in place; produce a fresh Locked artifact.

#### Implements
- [REQ-2] Promotion Gate

### [TASK-4] Build-Mode authoring surface for a supervisor

#### Steps
1. Expose the agent-kit authoring operations (create/modify agent, tool, eval) as a
   programmatic surface a supervisor agent can drive, scoped to a staging data dir.
2. Record the supervisor's authoring trace (decisions + provenance) so the
   construction is itself reproducible/attributable.

#### Implements
- [REQ-1] Build Mode — Mutable Supervised Authoring
- [REQ-6] The Supervisor Loop (build-time agent)

### [TASK-5] A reference supervisor + locked-deployment demo

#### Steps
1. A small worked example: a supervisor authors a tiny agent+tool+eval to solve a
   stated problem, passes the gate, freezes, and the Locked system replays
   byte-identically with the LLM removed.
2. Verify all guardrails still pass; populate `index.json` and flip `status` to
   `covered` once built.

#### Implements
- [REQ-1] … [REQ-6] (end-to-end proof + traceability)
