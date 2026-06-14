# Lobsters · dev.to · LinkedIn

The remaining channels. Lower volume than HN/Reddit/X, but each reaches a distinct,
valuable audience.

---

## Lobsters (Day 2)

Senior, low-noise, allergic to marketing. **Requires an invite** to post — if you're
not a member, ask someone who is, or skip it for now. Submit the **blog**, not the
repo, and tag accurately (`ai`, `programming`, `practices`).

- Don't editorialize the title; use the blog's real title.
- The "is / is not" honesty and the determinism CI check play *very* well with this
  crowd. The benchmark and the precise caveat are what earn respect here.
- Expect sharp, technical questions. Answer them straight; "you're right, that's a
  limitation" wins more than a rebuttal.

---

## dev.to / Hashnode (Day 2)

Cross-post **blog 01**, then **blog 02** a week later. **Set the canonical URL** to
your own site so you keep the SEO. Good for long-tail discovery (people Googling
"reproducible AI agent" / "agent flaky CI" months later).

- Add tags: `#ai`, `#llm`, `#python`, `#opensource`, `#testing`.
- Include the benchmark code block — dev.to readers copy-paste and try things.
- End with the repo link and an invitation to open an issue.

---

## LinkedIn (Day 3)

Lower developer density, slower, but good for **design-partner inbound** — founders,
eng leads, and platform teams who feel the reliability pain at the budget level.
Write it as a builder story, calmer than the X thread.

**Post:**
> Shipping AI agents taught me an uncomfortable lesson: the demo is the easy 20%. The
> hard 80% is that agents are non-deterministic, so you can't reproduce failures — and
> if you can't reproduce a failure, you can't fix it or write a test for it.
>
> I've been building an open-source runtime, Jaros, around a single idea: take the
> model out of the control path. The LLM only proposes inert data; a deterministic
> system decides what actually runs and records every decision. The payoff is that you
> can replay an entire agent run to byte-identical state — turning "it only happens
> sometimes" into a normal debugging session, and making agents something you can
> actually gate in CI.
>
> It's zero-infrastructure (no server, database, or broker), MIT-licensed, and honest
> about what it isn't (not a security sandbox, not cluster-scale). If your team is
> wrestling with agent reliability in production, I'd value a conversation — I'm
> looking for a few teams to try it on real workloads.
>
> https://github.com/jaredpilcher/Jaros

- Reply to every comment; LinkedIn's algorithm rewards author replies heavily.
- This is where "I'm looking for a few teams to try it" is appropriate — the audience
  is the right altitude for design partnerships.

---

## Channel timing recap

| Day | Channel(s) |
| --- | --- |
| Tue | Blog 01 (your site) → Show HN → X thread → r/LocalLLaMA |
| Wed | r/LLMDevs + r/AI_Agents → Lobsters → dev.to (blog 01) |
| Thu | r/MachineLearning `[P]` → LinkedIn |
| +1 week | Blog 02 (benchmark) → re-share to receptive channels → start Discord/Discussions |

Everywhere: same wedge sentence, same honesty, fast replies. The consistency is what
makes it read as a real project rather than a scattershot launch.
