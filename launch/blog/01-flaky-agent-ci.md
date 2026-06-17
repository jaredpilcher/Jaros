---
title: "Your AI agent passes locally and fails in CI. Here's why — and how to make runs reproducible."
description: "Agents are non-deterministic, so the bug you can't reproduce is the bug you can't fix. A look at why, and a runtime that records every decision and replays the run to byte-identical state."
canonical_url: "https://YOUR-SITE/blog/flaky-agent-ci"
tags: [ai-agents, llm, testing, reproducibility, open-source]
---

# Your AI agent passes locally and fails in CI. Here's why — and how to fix it.

You built an agent. It works on your machine. You write a test, it passes. You push,
and CI goes red — on the *same input*. You re-run CI, and now it's green. You ship,
and a week later a user hits a failure you have never once been able to reproduce.

If you've shipped an LLM agent, you know this feeling. It's not your fault, and it's
not a flaky test in the usual sense. It's structural.

## The problem: the model drives execution

In almost every agent framework, the loop looks like this:

```
the model emits a tool call  ──►  the side effect happens
```

The LLM is *in the control path*. A tool call **is** an action. That means the only
non-deterministic thing in your system — the model — is also the thing pulling the
levers. Change one token of the model's output and step 3 calls a different tool,
which feeds different data into step 4, and by step 10 the two runs are unrecognizable.

This is fine for a demo. In production it's a liability, because it breaks the one
assumption all of software engineering is built on:

> Given the same input, a function returns the same output — so I can reproduce a
> failure, step through it, fix it, and prove it's fixed.

When that breaks, your whole testing toolkit breaks with it. You can't write a
regression test for a bug you can't reproduce. You can't bisect. "It only happens
sometimes" becomes a permanent resident of your issue tracker. The 2026 consensus
is blunt about it: teams are being forced to invest in evaluation and reliability
precisely because production agents are too non-deterministic to trust by default.

The usual answer is **observability** — trace everything, add evals, watch the
failures roll in. That helps you *see* the non-determinism. It doesn't *remove* it.
You're still debugging a system that won't run the same way twice.

## A different answer: take the model out of the control path

What if the model could only ever *propose*, and a deterministic system decided
whether and how to act?

```
the model emits a Decision (inert data)  ──►  [gate]  ──►  a deterministic executor acts
                                                  │
                                                  └─► may reject; the model has no say
```

The model still makes the judgment calls — that's the reasoning, and it's the whole
point of using an LLM. But its entire interface to the world is **data in, data
out**. It writes a recommendation on a slip of paper; a deterministic clerk reads
the slip, checks it against the rules, and either runs it exactly or rejects it.

Here's what that buys you, and it's the thing I couldn't get any other way:

**Every run is reproducible.** The only non-deterministic input — the model's
output — is captured as inert `Decision` data and written to a durable log *before*
any effect happens. Replay that log through the deterministic executor and you
reconstruct the run to **byte-identical state, with zero model calls.** Crash
recovery is just a special case of replay.

That means a flaky production incident becomes a normal debugging session: **pin the
decision log, replay it, step through it, fix it, re-run it identically.** No "it
only happens sometimes."

I built a small open-source runtime around this idea called **[Jaros](https://github.com/jaredpilcher/Jaros)**.
Here's the property, as a number you can run yourself:

```
recorded agent run, replayed 5x into fresh isolated state
  model calls on replay : 0
  distinct state hashes : 1   (1 == byte-identical)
  => REPRODUCIBLE       : True

the same logic in a typical model-drives loop, run 5x
  distinct outputs      : 5
  => REPRODUCIBLE       : False
```

(That's `python launch/benchmark/run_reproducibility_benchmark.py` in the repo — it
uses the real record/replay APIs, not a mock.)

## What this is — and isn't

I'll be precise, because over-claiming in this space is epidemic:

- It is a **zero-infrastructure runtime** — no server, no database, no broker. Files
  and threads. It runs offline, with no API key, on the default adapter.
- It makes runs **reproducible by replay** and agents **capability-safe** (an agent
  holds only the handles you grant it, so a bad decision can't touch what you didn't
  give it — and every action is audited).
- It is **not** a hardened security sandbox, **not** a cluster-scale distributed
  system, **not** an agent-authorization gateway, and **not** "unbreakable." It
  claims only what it can keep: durable, crash-recoverable, replayable,
  capability-bounded.

And it doesn't stop at one agent. Every agent writes to **one ordered, hash-chained
decision log**, tagged with the agent that made each decision — so you can replay a
whole **swarm** to byte-identical state *and* attribute any failure to the exact agent
and decision that caused it. "Which agent broke it?" stops being a guess off surface
logs and becomes a lookup against a tamper-evident record (the kind of who-did-what
audit trail regulated teams increasingly need — e.g. EU AI Act Article 12). At swarm
scale, that accountability is the whole game.

Think of it as the **graduation layer** between a prototype (LangGraph, CrewAI) and
heavyweight durable-execution infrastructure (Temporal, Dapr): the reproducibility
and accountability you need *the day you ship a swarm*, without standing up a cluster.

There's one honest caveat, and stating it is the point: replay is byte-identical
**because the executor handlers are deterministic.** Jaros makes that checkable and
checks it in CI, so a handler that sneaks in a clock or RNG read fails the build
rather than silently breaking the guarantee.

## Try it (5 minutes, no API key)

```bash
pip install jaros            # runs offline; no key, no database, no server
jaros init --with-examples   # scaffold a data dir + bundled example agents
jaros serve                  # boot the OS (opens the web console; --no-console for headless)
# in a second terminal:
jaros submit greeter --input '{"name":"Jaros"}'
jaros replay                 # replay the run to byte-identical state, 0 model calls
```

Full quickstart, the benchmark, and the architecture are in the repo:
**https://github.com/jaredpilcher/Jaros**

If your agents are flaky in CI and you've been told "that's just how LLMs are" — I
don't think it has to be. I'd genuinely like to hear what breaks when you point it
at your agent; open an issue or find me and I'll help.
