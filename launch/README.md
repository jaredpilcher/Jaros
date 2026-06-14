# Jaros Launch Kit — the runbook

Everything you need to take Jaros from "great repo nobody's seen" to "developers
are trying it." Written for an **infra founder who is not a salesman**: ~80% of
this is building and showing your work, which you already do well. The
uncomfortable 20% (hitting "publish," replying to strangers) is *helping people
with a problem you can fix* — not selling.

> The whole game is one funnel: **Discover → Try → Adopt → Advocate.**
> Each step is won with an *artifact*, not a pitch. This folder is those artifacts.

---

## What's in this kit

| File | What it is | Use it for |
| --- | --- | --- |
| `README.md` (this) | The master runbook: sequence, channels, timing | Your launch operating manual |
| `quickstart-audit.md` | Fresh-machine audit of the try-it path + fixes | **Do this before launching** |
| `blog/01-flaky-agent-ci.md` | Flagship problem-first post | The launch centerpiece |
| `blog/02-deterministic-replay-vs-time-travel.md` | Technical/benchmark post | Second wave (week 2) |
| `posts/show-hn.md` | Hacker News title + body + first comment + reply templates | Launch day |
| `posts/reddit.md` | 3 subreddit variants + etiquette | Launch day / day 2 |
| `posts/x-thread.md` | X/Twitter launch thread + follow-ups | Launch day |
| `posts/lobsters-devto-linkedin.md` | Remaining channels | Launch week |
| `benchmark/` | A **runnable** reproducibility benchmark (real numbers) | Proof in the posts |

---

## The single most important thing

**A flawless 5-minute "wow."** Most OSS projects die not because the idea is bad
but because the quickstart breaks on a fresh machine, or the value takes 30
minutes to feel. Before you post anything, run `quickstart-audit.md` and make the
first run undeniable. For Jaros the wow is the replay benchmark:

```bash
python launch/benchmark/run_reproducibility_benchmark.py
```

It prints byte-identical replay across 5 runs with **0 model calls**, beside a
typical loop that diverges every time. That contrast *is* the product. Lead with
it everywhere.

---

## Phase 0 — Make it adoptable (before any launch)

Tick every box. This is pure building — your home turf.

- [ ] Run `quickstart-audit.md` end-to-end **on a clean container**; fix every stumble.
- [ ] README top: one plain sentence + the replay GIF (you have both).
- [ ] The 5-min wow works copy-paste with **no API key** (default adapter is offline).
- [ ] `CONTRIBUTING.md` + 3–5 `good first issue`s exist.
- [ ] A one-page landing site (the repo + docs is enough to start).
- [ ] Decide the **one wedge sentence** and use it identically everywhere:
      *"Your agent tests are flaky and you can't reproduce failures. Jaros records
      every decision and replays the run to byte-identical state — so you can
      debug it like normal software and gate it in CI."*
- [ ] Pick a launch week. Best days: **Tuesday–Thursday.** Avoid Mon/Fri, holidays,
      and big news days (major model releases, Apple/Google keynotes).

---

## Launch week — day by day

Times are **US Eastern** (HN/Reddit/X skew to a US-daytime audience; post when the
US is waking up). Adjust ±1hr; consistency matters more than precision.

### Day 1 (Tue) — the main launch

- **08:30 ET** — Publish `blog/01-flaky-agent-ci.md` on your site/blog first (so
  every post links to a page you control, not just the repo).
- **09:00 ET** — **Show HN** (`posts/show-hn.md`). Title matters more than anything.
  Immediately post your prepared first comment (the "why I built this" context).
- **09:15 ET** — **X thread** (`posts/x-thread.md`). Pin it.
- **09:30 ET** — **r/LocalLLaMA** post (`posts/reddit.md`, variant A).
- **All day** — Reply to *every* comment within ~15–30 min for the first 6 hours.
  This is the highest-leverage work of the entire launch. Be humble, concrete,
  non-defensive. Use the reply templates in `posts/show-hn.md`.
- **Do not** post to multiple subreddits the same hour — stagger by a day and read
  each sub's rules (some require self-promo flair or a "I built this" disclosure).

### Day 2 (Wed)

- **09:00 ET** — **r/LLMDevs** (variant B) and **Lobsters** (`posts/lobsters-devto-linkedin.md`).
- Post the **dev.to** cross-post of blog 01 (canonical URL → your site).
- Keep replying. Triage issues opened overnight; fix the easy ones same-day and
  thank the reporter by name.

### Day 3 (Thu)

- **09:00 ET** — **r/MachineLearning** (variant C, framed as a project/engineering
  post — that sub is stricter; lead with the technical contribution, not the launch).
- **LinkedIn** post (`posts/lobsters-devto-linkedin.md`) — a calmer, builder-story version.
- Write a short "launch day, by the numbers" note for yourself; decide what to fix.

### Day 4–5 (Fri / weekend)

- Cool-off. Respond, don't broadcast. Convert any "this is cool" into "want to try
  it on your agent? I'll help" — the first design-partner seed.

---

## Week 2 — the technical follow-through

The launch buys a spike of attention; the *second* post converts the skeptics.

- Publish `blog/02-deterministic-replay-vs-time-travel.md` (the benchmark post).
  Run `benchmark/` yourself, paste the real output, and — if you have an afternoon —
  add the optional LangGraph side-by-side (see `benchmark/README.md`).
- Re-share to HN (a *different* angle is fair; resubmitting the identical link is not),
  Lobsters, and the subreddits that received the launch well.
- Start a Discord or GitHub Discussions and link it from the README. Early users
  want a place to ask; that place becoming active is itself the marketing.

---

## Channel cheat-sheet (where developers actually are)

| Channel | Audience | How to show up | Notes |
| --- | --- | --- | --- |
| **Hacker News (Show HN)** | Broad senior dev | Honest "I built this," problem-first | The big one. Title + fast replies decide it. Don't ask for upvotes (bannable). |
| **r/LocalLLaMA** | Hands-on LLM builders | Demo + "no API key to try" | Your warmest crowd. Loves self-hostable/offline. |
| **r/LLMDevs, r/AI_Agents** | Agent builders | The flaky-CI pain | Directly your wedge. |
| **r/MachineLearning** | Researchers/engineers | Technical contribution framing `[P]` | Strict; lead with substance, not launch. |
| **Lobsters** | Senior, low-noise | Technical, understated | Needs an invite; quality bar is high. |
| **X/Twitter** | Fast, visual | The replay GIF + thread | Tag no one to start; let it travel. |
| **dev.to / Hashnode** | SEO + beginners | Cross-post the blog | Set canonical URL to your site. |
| **LinkedIn** | Slower, founders/teams | Builder story | Lower dev density; still good for design-partner inbound. |
| **Discords/Slacks** (LangChain, agent communities) | Practitioners | Be a member first, share when relevant | Never drive-by spam. |

---

## The engagement playbook (your "sales", reframed as helping)

1. **Reply fast and kind.** Speed of response is the strongest trust signal a solo
   project has. First 6 hours = drop everything.
2. **Never get defensive.** "Fair — here's the tradeoff" beats winning an argument.
   The `is / is not` in the Prime Directive is your honesty shield; use it.
3. **Turn interest into a try.** "Happy to help you wire this into your agent —
   open an issue or DM me." That sentence lands design partners.
4. **Fix in public.** A bug reported at 10am and fixed by 2pm with a thank-you is
   worth more than any feature.
5. **Collect the pain.** Every "but does it handle X?" is a roadmap entry and a
   future blog post. Write them down.

---

## 30 / 60 / 90

- **30 days:** flawless quickstart; the wow; blog 01 drafted; CONTRIBUTING + issues.
- **60 days:** launched (HN + 2 subreddits + X); responded to everything; friction fixed;
  blog 02 (benchmark) live.
- **90 days:** 2–3 design partners running a real agent on Jaros; a third post; iterate
  on what partners actually needed. **Someone ships on Jaros without you in the room.**

---

## Metrics that matter (not revenue yet)

- Did people **complete the quickstart**? (Instrument the docs with a "did this work?" link.)
- Are issues coming from **real usage**, not just "won't install"?
- **Design partners** signed (the real number).
- "Someone built something on it without me" — the moment it's real.
- Stars/week — a *lagging* social-proof proxy. Nice, not the goal.

---

## Do / Don't

**Do:** lead with the problem; show the wow in 60s; be honest about "is not"; reply
fast; help people try it; publish the benchmark you can reproduce.

**Don't:** ask for upvotes (HN-bannable); say "revolutionary/unbreakable/world-first";
cross-post identically to 6 subs in an hour; argue with critics; add features instead
of talking to users; launch before the quickstart is flawless.

---

*Built for the `prime-directive-reconciliation` branch. Every claim in these
artifacts is backed by something that runs today (`launch/benchmark/`,
`scripts/check_determinism.py`, the console replay). Keep it that way — the honesty
is the moat.*
