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

## LinkedIn — the apex post (what to publish)

Your *job* channel — recruiters and eng leaders are here. Lead with the swarm
**accountability** angle: it's the part that resonates with regulated / high-stakes
teams (fintech, crypto, infra). Make it earn **comments**, not just likes.

**Post** (open with the hook; the first two lines are all that show before "…see more"):
> When a swarm of AI agents "does something wrong," two questions are almost
> impossible to answer: can you **reproduce** it, and **which agent** caused it?
>
> That's not a model problem — it's an architecture problem. And it's fixable.
>
> Most agent stacks let the model drive: a tool call *is* a side effect. So the one
> non-deterministic thing in your system is also in the control path, and at swarm
> scale the failures compound — you can't replay what happened, and the logs show
> surface chatter, not the deciding agent.
>
> I open-sourced **Jaros** to fix that by construction. The model only *proposes*
> inert `Decision` data; a deterministic system decides what runs and records every
> decision — in one ordered, **hash-chained** log, tagged with the agent that made it.
>
> The payoff:
> • Replay a whole **hive of agents** to byte-identical state — with **zero model calls**.
> • Attribute any failure to the **exact agent and decision** that caused it (recorded fact, not a guess).
> • A **tamper-evident** record of who-did-what — the accountability regulated teams need.
>
> [attach the 30s replay clip / the swarm-replay screenshot]
>
> Zero-infrastructure — no server, no database, no broker. MIT, runs offline. Honest
> about limits: it's the reproducibility-and-accountability *substrate* a swarm runs
> on — not a swarm-orchestration framework, not cluster-scale, not "unbreakable."
>
> For people building multi-agent systems: when a swarm misbehaves in prod, how does
> your team reproduce it and figure out which agent was responsible — today?

**First comment** (post immediately — link lives HERE, not in the body):
> Repo + a 5-minute quickstart (no API key, runs offline):
> https://github.com/jaredpilcher/Jaros — it replays a hive of agents and names the
> one that broke it. Happy to dig in with anyone wrestling with multi-agent reliability.

**Notes**
- **Native-upload** the replay clip; no external link in the body (LinkedIn throttles
  outbound links) — GitHub link goes in the first comment.
- Reply to every comment fast; author replies are weighted heavily.
- The "which agent was responsible" question is the comment-bait — and the exact pain
  a fintech/crypto AI leader feels. Seed it with a few thoughtful connections.

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
