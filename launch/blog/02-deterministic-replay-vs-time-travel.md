---
title: "Deterministic replay vs. time-travel: two very different promises about reproducing agent runs"
description: "Checkpointing rewinds to a saved state and re-executes. Record-and-replay re-injects the recorded decisions. Only one reconstructs an agent run byte-for-byte — here's the mechanism, a runnable benchmark, and the one caveat that matters."
canonical_url: "https://YOUR-SITE/blog/deterministic-replay-vs-time-travel"
tags: [ai-agents, llm, reproducibility, determinism, architecture, open-source]
---

# Deterministic replay vs. time-travel

"Reproducible agents" has become a 2026 buzzword, and like most buzzwords it hides
a real distinction. Two mechanisms get called "replay," and they make very different
promises. If you're choosing a runtime for agents you actually have to debug in
production, the difference is the whole ballgame.

## Mechanism 1: checkpoint + time-travel (rewind and re-execute)

The popular approach — LangGraph's time-travel is the cleanest example — snapshots
the graph's **state** at each step. To "replay," you pick a checkpoint and resume
from it. It's genuinely useful for human-in-the-loop, forking alternatives, and
recovery.

But there's a catch that the docs are honest about: resuming **re-executes** the
nodes. LLM calls, API requests, and side effects *fire again* — and may return
different results this time. ([LangGraph time-travel re-executes nodes — write-up](https://dev.to/sreeni5018/debugging-non-deterministic-llm-agents-implementing-checkpoint-based-state-replay-with-langgraph-5171).)
So time-travel makes a workflow *resumable*; it does **not** make a run
*reproducible*. Re-run from the same checkpoint and you can get a different outcome,
because the non-determinism is still live in the path.

## Mechanism 2: record-and-replay (re-inject the recorded inputs)

This is the classic technique from deterministic-replay debuggers: most execution is
already deterministic; you only need to **log the non-deterministic inputs** during
recording, then **re-inject them** during replay. The program re-runs against the
recorded inputs and reconstructs the exact original execution.

For an agent, what's the non-deterministic input? The model's output. So if you can
arrange for the model to emit only **inert data** — a `Decision` — and have a
**deterministic executor** perform every effect, then recording the stream of
decisions is enough to replay the entire run with **no model call at all.**

That's the architecture [Jaros](https://github.com/jaredpilcher/Jaros) is built on,
and it's why its replay is a different promise.

## The mechanism, concretely

The model never drives execution. It proposes:

```
record:   reasoning ─► Decision(data) ─► [gate] ─► executor ─► state
                            │
                            └─► append to durable decision log (before any effect)

replay:   decision log ─────────────────► executor ─► identical state
          (no model call; the recorded decisions are the inputs)
```

In code it's about as small as it sounds:

```python
from jaros.execution import executor
from jaros.state import DecisionLog, TransitionLog, record_decision, replay

# during the live run, each accepted decision is recorded before its effects:
record_decision(decision_log, decision)

# later — in CI, in a debugger, on another machine — replay it:
fresh = TransitionLog(path); fresh.ensure()
results = replay(decision_log, executor.apply, log=fresh)
# `fresh` is now byte-identical to the original run's state. No model was called.
```

## The benchmark (runnable, real numbers)

`python launch/benchmark/run_reproducibility_benchmark.py` records a run and replays
it 5× into fresh, isolated state:

```
[Jaros]  recorded run replayed 5x into fresh isolated state
         model calls on replay : 0
         distinct state hashes : 1   (1 == byte-identical)
         => REPRODUCIBLE       : True

[Typical 'model-drives' loop] same step run 5x
         distinct outputs      : 5
         => REPRODUCIBLE       : False
```

It uses the real `record_decision` / `replay` / executor APIs — if a handler were
non-deterministic, the hashes would diverge and the benchmark would say so.

## The one caveat that actually matters

Byte-identical replay holds **because the executor handlers are deterministic
functions of the decision plus state.** A handler that reaches for the wall clock, a
random source, or external mutable I/O breaks the guarantee — replay would no longer
reconstruct the same state.

The wrong move is to hide this. The right move is to make it **checkable and
checked**:

- `jaros.execution.replays_agree(...)` re-runs a replay into fresh state and requires
  agreement.
- Eval cases can assert `deterministic: true`, catching a non-deterministic handler
  in your own test suite.
- `scripts/check_determinism.py` runs in CI and **fails the build** if the core
  execution path stops being byte-identical.

So the honest claim is precise: *Jaros replay is byte-identical for deterministic
handlers, and it makes handler determinism a checked invariant rather than an
assumption.* That's a stronger position than "trust us," and it's the kind of claim
you can put your name on.

## Why this composes with the rest

Reproducibility isn't a lone trick; it's what makes the other things real:

- **Testable agents.** Deterministic execution is the precondition for the 2026
  reliability playbook — a golden dataset, graders, and a **CI gate that blocks
  regressions**. You can't gate what you can't reproduce.
- **Capability-safety.** Agents hold only the scoped handles the harness grants;
  every mediated action is written to a durable audit log. A bad decision can't reach
  what it was never given, and you can replay *and* audit exactly what happened.
- **Zero infrastructure.** All of this is files and threads — no server, no database,
  no broker (there's a build check that fails if any module imports one).

## Where it fits

| | Prototype frameworks | **Jaros** | Durable-execution infra |
| --- | --- | --- | --- |
| Stand-up cost | none | **none** — files + threads | servers, brokers, DBs |
| "Replay" | state rewind, re-executes | **record-and-replay, byte-identical** | journal replay (heavy) |
| Safety model | ambient tool access | **capability-scoped, default-deny** | varies |
| Reach for it… | the first ten lines | **the day you ship** | cluster scale |

Jaros is MIT-licensed and runs offline with no API key:
**https://github.com/jaredpilcher/Jaros**. If you try the replay on your own agent,
I want to hear where it holds and where it doesn't.
