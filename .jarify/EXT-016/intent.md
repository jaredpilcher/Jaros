# Intent

Use an AI **supervisor at build time** to author and mutate the deterministic
system — agents, tools, executor handlers, harness rules, evals — until it solves a
perceived problem; verify it by evals + deterministic replay; then **freeze**
("lock") the deterministic execution into a **sealed, hash-verified, replayable,
attributable** production artifact. After the freeze, production behaves *exactly*
that way: the deterministic plane is immutable, the LLM is demoted to proposing
inert decisions (or removed), and every run is reproducible and attributable.

This is the safe way to do self-improvement: **mutate under test at design time;
fix and seal for production.** The freeze is the safety boundary — nothing
"improves" itself in prod without going back through the build-and-verify gate.

Two modes:

- **Build Mode** — mutable. The supervisor may author/change agents, tools,
  handlers, rules, and evals; the full eval + replay + determinism toolchain is
  available to prove a candidate works.
- **Locked Mode** — immutable. The deterministic artifact set is frozen and sealed
  with a manifest hash; no authoring of the deterministic plane is permitted; only
  inert decisions flow through the frozen executor.

Promotion from Build to Locked is a **gate**: evals pass, replay is byte-identical,
and the determinism check is clean. This realizes the Prime Directive's
reproducibility/accountability tenets (P1, P2, P5) at the *system-construction*
level — and is the practical, EU-AI-Act-shaped "this is the exact verified system
we deployed," without crypto or blockchain.

**Status: planned / future.** Recorded as a north-star direction. It is *not* in the
current build queue (the apex swarm work and launch come first). It composes
existing primitives — the agent-kit (authoring, EXT-014), evals (EXT-013), replay &
attribution (EXT-008/EXT-015), the determinism guardrail, the frozen harness rules
(EXT-005), and the tamper-evident chain (EXT-015) — plus one new idea: the
**seal/manifest** and the **Build→Locked** mode switch.
