# AGENTS.md

Guidance for AI coding agents working in this repository. (Human contributors:
see [`README.md`](README.md).)

## Start here

**→ Read [`agent-kit/README.md`](agent-kit/README.md).** It is the single entry
point: the mental model, a skill for each thing you can build (agent, tool, eval,
schedule), accurate API reference, and runnable templates.

## What Jaros is

A zero-infrastructure agent OS. No server, no database, no message broker — just
files and threads. A daemon turns inbox jobs into validated, durable state
transitions over a shared file system.

## The rules you must honor

1. **Agents emit inert data; tools run it.** An agent's `decide()` returns
   `Decision` objects (JSON-serializable data only) and performs no side effect.
   The effect lives in a tool whose `NAME` equals the decision's `type`.
2. **`execute()` must be deterministic.** No clock, RNG, network, or ambient
   state. This is what makes every run reproducible by `jaros replay`
   (byte-identical, zero model calls).
3. **Least privilege.** Prefer read-only tools; request a capability only when the
   action truly needs it.
4. **Zero infrastructure.** Do not add a server, database, or broker. Guardrails in
   `scripts/` (run by `pytest`) will reject it.

## How to work

- Build from the templates in [`agent-kit/templates/`](agent-kit/templates/) and
  follow the matching skill in [`agent-kit/skills/`](agent-kit/skills/).
- Install with `pip install -e ".[dev]"`.
- **Verify before you finish:** `jaros eval --data-dir <dir>` must exit 0,
  `jaros replay --data-dir <dir> --json` must show `modelCalls: 0` /
  `byteIdentical: true`, and `pytest` must pass.
- Use a throwaway `--data-dir` for experiments; never write to a data dir a daemon
  you don't own is using.

## Deeper context

- Reference: [`agent-kit/reference/`](agent-kit/reference/)
- Worked examples: [`examples/`](examples/)
- Web console: [`console/`](console/) · [`docs/console.md`](docs/console.md)
- Full intent and specs: [`.jarify/`](.jarify/) (Prime Directive: `PRIME-001`;
  this kit: `EXT-014`)
