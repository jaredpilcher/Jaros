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

This is your **job channel** — recruiters and eng leaders are here, and v1 (June 9)
already drove profile views + followers. v2's job is to earn **comments**, not just likes.

### The post (v2 — paste-ready)

Built around the replay video, opening with your strongest line. The **first two lines are
the hook** — all that shows before "…see more," so they decide who expands.

> When an AI agent "does something wrong" — sends the wrong email, deletes the wrong file —
> it's almost never a dumb model.
>
> It's that we wired the model's output straight to the trigger. That's a design flaw, not a
> model flaw — and no amount of better prompting fixes a design flaw.
>
> So I open-sourced Jaros, built on one rule: the model only *proposes*. A deterministic
> system decides what actually runs, and records every decision.
>
> The payoff is something most agent stacks can't do 👇 I can replay an entire agent run and
> reconstruct it to byte-identical state — with zero model calls. "It only happens sometimes"
> becomes a normal debugging session: pin the decision log, replay, step through, fix.
>
> [⬆ attach the 30-second replay video here — NATIVE upload, no external link]
>
> It's zero-infrastructure — no server, no database, no broker. MIT, runs offline. And honest
> about limits: not a security sandbox, not cluster-scale, not "unbreakable." It's the
> reproducibility-and-safety layer you reach for the day your agent leaves the demo.
>
> A question for everyone building agents: when your team says "the agent did something
> wrong," are you reaching for a better prompt — or rethinking the architecture? Genuinely
> curious how others are handling this.

### First comment (post it immediately — the link lives HERE, not in the body)

> Repo + a 5-minute quickstart (no API key, runs offline): https://github.com/jaredpilcher/Jaros
> — happy to answer anything, and if you point it at your own agent I'd love to hear where it breaks.

### Why this beats v1 (15 reactions, 0 comments)

- **Hook in the first 2 lines** — the "design flaw" line, above the "…see more" fold.
- **Native-uploaded video, no link in the body** — LinkedIn throttles outbound links, so the
  GitHub link goes in the *first comment*. (v1's link-in-body + "go to GitHub" CTA is why it
  got 0 comments.)
- **Ends on a question** — pulls conversation *into the comments*, where reach is earned.
- **Seed it:** right after posting, ping 5–10 relevant people; reply to every comment within
  the hour. Early comments are what expand reach.
- **Timing:** Tue–Thu, ~9am ET. Author replies are weighted heavily — be fast and kind.

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
