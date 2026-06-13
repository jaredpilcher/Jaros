# Design — Agent Evaluation Framework

Evals are deterministic because Jaros is: the agent emits inert `Decision` data
and the executor is deterministic, so an "input → expected decision/result" case
reproduces exactly. The framework is small, pure, and host-side — it imports only
`jaros` + the standard library and adds no infrastructure.

## Flow

```text
   evals/*.json ──► load_cases ──► [ EvalCase, ... ]
                                        │
                          run_suite     ▼   (per case)
                       ┌──────────────────────────────────────────┐
                       │ registry.resolve(kind) ► boundary.decide() │
                       │            │ decisions (inert data)        │
                       │            ▼                                │
                       │ checks: count · kind · source · payload    │
                       │         gate(accept/reject)                 │
                       │         result_contains ► executor.apply()  │  (no model call)
                       └──────────────────────────────────────────┘
                                        │
                                        ▼
                              SuiteReport { total, passed, failed, ok }
```

## Why it reproduces

The only non-determinism in an agent is the model output, captured as `Decision`
data. Run evals against a deterministic LLM adapter (the default echo adapter) and
the decisions are fixed; the gate and executor are deterministic by construction.
So a green eval stays green for the same code + cases — the same guarantee replay
gives a recorded run (EXT-002 / REQ-6).

## Surfaces

```text
   library   jaros.eval.run_case / run_suite        (import + assert in pytest/CI)
   CLI       jaros eval --data-dir D                 (assemble agents+tools, run evals/)
   examples  examples/readonly/evals/readonly.json   (cases for the read-only agents)
```

The CLI assembles a deterministic environment from the data dir (built-in +
plugin agents via the registry, tool handlers via `load_custom_tools`) so
`result_contains` checks execute real tools — read-only, deterministic.

## Prime Directive consistency

- Evals assert on inert `Decision` data and deterministic execution. [P1, REQ-1]
- No infrastructure, no network — files + the standard library. [P3]
- The framework grades structure, not model "quality"; it is reproducible
  software testing, not an LLM-judge. [scope honesty, P4]
