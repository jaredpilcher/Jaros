# Reddit — subreddit variants

Reddit punishes copy-paste cross-posting. **Stagger by a day**, tailor each to the
sub, read each sub's rules first (several require a self-promo disclosure or flair),
and reply to every comment. Lead with value; the link is secondary.

---

## Variant A — r/LocalLLaMA (Day 1, ~9am ET)

*Your warmest crowd: hands-on, loves self-hostable/offline. The "no API key, runs
offline" angle lands hardest here.*

**Title:** I built a zero-infra agent runtime that replays a run to byte-identical state (offline, no API key)

**Body:**
> I got tired of agents that pass locally and fail in CI on the same input, with
> failures I could never reproduce. So I built **Jaros**, a small MIT-licensed Python
> runtime around one idea: the model only ever emits inert `Decision` data, and a
> deterministic executor does the work. Every decision is recorded, so you can replay
> a whole run to **byte-identical state with zero model calls** — debug it like normal
> software.
>
> It's fully zero-infra — no server, DB, or broker — and runs **offline with no API
> key** on the default adapter (there's a build check that fails if any module imports
> a database driver or broker, which I'm weirdly proud of). Agents run as lightweight
> threads, not microservices, and hold only the capability handles you grant them.
>
> Runnable benchmark in the repo (replays a run 5× → 1 distinct state hash; a typical
> model-drives loop → 5 different outputs). Honest about limits: it's not a hardened
> sandbox, not cluster-scale, not "unbreakable."
>
> Repo + quickstart: https://github.com/jaredpilcher/Jaros — would love to hear what
> breaks if you point it at your own setup.

---

## Variant B — r/LLMDevs and r/AI_Agents (Day 2)

*Builders feeling the exact pain. Lead with the CI story.*

**Title:** Making agent runs reproducible so they can actually pass CI

**Body:**
> Agent reliability advice in 2026 all says the same thing: build a golden dataset,
> graders, and a CI gate that blocks regressions. But you can't gate what you can't
> reproduce — and most agent loops aren't reproducible, because the model drives
> execution and a tool call *is* a side effect.
>
> I've been building **Jaros** to attack that at the runtime level: the LLM only
> proposes inert `Decision` data, a deterministic executor acts, and every decision is
> recorded — so a run replays to byte-identical state with no model call. Recovery is
> just a special case of replay. There's an eval framework where a case can assert
> `deterministic: true`, plus a CI check that fails the build if the core path stops
> being reproducible.
>
> It's zero-infra (files + threads, no server/DB/broker), MIT, runs offline.
> Repo: https://github.com/jaredpilcher/Jaros. Curious whether this maps to how you're
> handling agent testing today — what's your current approach to flaky runs?

---

## Variant C — r/MachineLearning (Day 3, `[P]` Project flair)

*Stricter, research-leaning. Lead with the technical contribution, not the launch.
Understate.*

**Title:** [P] Jaros: record-and-replay for LLM agents — byte-identical run reconstruction

**Body:**
> Sharing a project exploring deterministic replay for agent systems. The design
> separates a non-deterministic reasoning plane (the LLM, which may only emit inert
> `Decision` data) from a deterministic execution plane (an executor that performs all
> effects). Because the only non-deterministic input — the model output — is captured
> as data and logged before any effect, replaying the decision log reconstructs a run
> to byte-identical state with no model invocation. This is the classic record-replay
> technique (log non-deterministic inputs, re-inject on replay) applied to agents,
> contrasted with checkpoint/time-travel which rewinds state but re-executes nodes.
>
> The reproducibility guarantee is conditional on handler determinism, which the
> project makes a checked invariant (a CI guardrail fails if the core execution path
> diverges across replays). Runnable benchmark and writeup of the mechanism in the
> repo. Feedback on the approach and its failure modes welcome.
>
> https://github.com/jaredpilcher/Jaros

---

## Reddit etiquette

- Read the rules; some subs require you to disclose you're the author (always do).
- Don't link-drop and leave — the first 2 hours of replies determine the post's fate.
- Answer questions, ask questions back, be a person. Karma/sub-history helps; if your
  account is thin, comment around the sub for a few days first.
- If a post underperforms, don't repost the same thing — adjust angle and target a
  different sub later.
