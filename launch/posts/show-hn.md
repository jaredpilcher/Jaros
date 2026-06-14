# Hacker News — Show HN

The title is 80% of the outcome. It must be concrete, honest, and free of hype
words ("revolutionary", "unbreakable", "world's first" — all kill credibility on
HN). Lead with the *capability*, not the category.

## Title options (pick one, ≤ 80 chars)

1. **Show HN: Jaros – replay an AI agent run to byte-identical state (no model call)**
2. **Show HN: Jaros – make agent runs reproducible by recording every decision**
3. **Show HN: Jaros – a zero-infra runtime that makes AI agents reproducible in CI**

> Recommended: **#1.** It names the one thing nothing else does and invites "wait,
> how?" — which is exactly the click you want.

## URL

Link to the **repo** (https://github.com/jaredpilcher/Jaros), not the blog. HN
prefers the source. Put the blog link in your first comment.

## First comment (post it immediately after submitting)

> Author here. I kept hitting the same wall: an agent passes locally, fails in CI on
> the same input, then passes on re-run — and I could never reproduce the production
> failures to fix them. The root cause is structural: in most frameworks the model
> *drives* execution (a tool call is a side effect), so the only non-deterministic
> thing in the system is also in the control path.
>
> Jaros flips that. The LLM can only emit inert `Decision` data; a deterministic
> executor performs every effect, and each accepted decision is recorded to a durable
> log before anything happens. So you can replay the log and reconstruct the run to
> byte-identical state with **zero model calls** — crash recovery is just a special
> case of replay. A flaky incident becomes: pin the decision log, replay, step
> through, fix, re-run identically.
>
> It's a zero-infra Python runtime — no server/DB/broker, runs offline with no API
> key (there's even a build check that fails if any module imports a database driver
> or broker). MIT licensed.
>
> The honest caveat: byte-identical replay holds because the executor *handlers* are
> deterministic — so I made that a checked invariant (`check_determinism.py` fails CI
> if the core path stops being reproducible), rather than something you have to
> trust.
>
> It's explicitly **not** a hardened sandbox, not cluster-scale, not a governance
> gateway, and not "unbreakable." It's the graduation layer between a LangGraph/CrewAI
> prototype and Temporal/Dapr-scale infra. Repo has a runnable benchmark and a
> web console with one-click replay. Happy to answer anything — and if you point it
> at your own agent, I'd love to hear where it breaks.

## Reply templates (stay humble, concrete, non-defensive)

**"Isn't this just LangGraph time-travel / checkpointing?"**
> Related but a different promise. Checkpoint+time-travel rewinds to a saved state
> and **re-executes** the nodes — LLM/IO fire again and can differ. Jaros records the
> decisions and **re-injects** them, so replay is byte-identical with no model call.
> Rewind-and-re-execute vs record-and-replay. Wrote up the distinction here: [blog 02].

**"What about non-deterministic handlers?"**
> Exactly the right question — that's the load-bearing caveat. Replay is byte-identical
> *because* handlers are deterministic. I don't assume it: `replays_agree`,
> `Expect.deterministic` eval cases, and a `check_determinism.py` CI gate fail the
> build if the core path stops reproducing. If you write a handler that reads a clock,
> the tooling tells you.

**"Isn't this just Temporal/DBOS?"**
> Same family (record non-determinism, replay deterministically), different point on
> the curve. Those are durable-execution infra — a cluster + a database. Jaros is the
> zero-infra, agent-native version: files + threads, nothing to stand up. It's not
> trying to replace them at cluster scale (that's in the README's "is not").

**"How is this secure if it's in-process Python?"**
> It isn't an adversarial sandbox and I don't claim it is. Capability handles are
> structural least-privilege — they bound blast radius (an agent reaches only what you
> granted, every action audited), not defend against hostile code in the same
> interpreter. Real isolation is the host's job (process/container/VPC). That boundary
> is written into the directive on purpose.

**"Why not just pin the model / set temperature 0?"**
> Helps, but doesn't get you there — tool outputs, retries, timing, and provider drift
> are still live, and temp-0 isn't guaranteed reproducible across versions. Recording
> the *decisions* sidesteps all of it: you replay what actually happened, not what you
> hope happens again.

## HN etiquette (don't get flagged)

- **Never** ask for upvotes anywhere (instant ban risk).
- Post **Tue–Thu, ~8–9am ET.** Don't post during a major launch news cycle.
- Reply to everyone, fast, for the first 6 hours. Engagement keeps you on the page.
- If it flops, that's normal — you can resubmit *with a different angle* (the
  benchmark post) in a couple of weeks. Don't resubmit the same link repeatedly.
