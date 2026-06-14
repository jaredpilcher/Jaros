# X / Twitter — launch thread

X rewards a visual hook and a tight thread. The **replay GIF** is your single best
asset — lead with it on post 1. Don't tag anyone at launch; let it travel on merit,
then reply to people who engage. Pin the thread.

## The thread

**1/ (attach the replay GIF)**
> Your AI agent passes locally, fails in CI on the same input, then passes on re-run.
> You can never reproduce the prod failures.
>
> It's not a flaky test. It's structural — and it's fixable.
>
> I built Jaros: replay an agent run to byte-identical state. 🧵

**2/**
> The root cause: in most frameworks the model *drives* execution. A tool call IS a
> side effect. So the one non-deterministic thing in your system — the LLM — is in the
> control path. Change one token and step 10 is unrecognizable.

**3/**
> Jaros flips it:
>
> model ─► Decision (inert data) ─► [gate] ─► deterministic executor acts
>
> The model proposes. A deterministic system decides whether/how it runs. The model's
> entire interface is data in, data out.

**4/**
> Every accepted decision is recorded to a durable log *before* any effect. So you can
> replay the log and reconstruct the run to BYTE-IDENTICAL state — with **0 model
> calls.** Crash recovery is just a special case of replay.

**5/ (attach benchmark output screenshot)**
> Real numbers from the repo's benchmark:
> • recorded run replayed 5× → 1 distinct state hash (byte-identical), 0 model calls
> • same logic, typical model-drives loop → 5 different outputs
>
> "It only happens sometimes" → "replay the log and step through it."

**6/**
> It's zero-infra: no server, no DB, no broker. Files + threads. Runs OFFLINE, no API
> key. There's literally a build check that fails if any module imports a database
> driver or broker.

**7/**
> Honest about limits (over-claiming is epidemic here):
> ❌ not a hardened sandbox
> ❌ not cluster-scale
> ❌ not a governance gateway
> ❌ not "unbreakable"
> ✅ durable, replayable, capability-bounded — claims it can keep.

**8/**
> The caveat that matters: replay is byte-identical *because handlers are
> deterministic*. I don't assume it — there's a CI check that fails the build if the
> core path stops reproducing. Checked, not trusted.

**9/**
> Think of it as the graduation layer: between a LangGraph/CrewAI prototype and
> Temporal/Dapr-scale infra. The reproducibility + safety you need the day you ship,
> without standing up a cluster.

**10/**
> MIT, Python, 5-min quickstart, runnable benchmark, web console with one-click replay:
> https://github.com/jaredpilcher/Jaros
>
> If your agents are flaky in CI — point this at one and tell me where it breaks. 🙏

## Notes

- Post the thread all at once (don't drip it over hours).
- Repurpose post 1 + the GIF as a standalone post a week later with a different hook.
- A 20–40s screen-recording of the console's one-click replay outperforms the GIF if
  you can make one — show the decision log, hit replay, show "byte-identical, 0 model
  calls." That clip is your most reusable asset across every channel.
