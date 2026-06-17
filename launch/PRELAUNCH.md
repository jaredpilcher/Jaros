# 🚀 Jaros launch — the do-this checklist

One page. Tick top to bottom. Every asset referenced lives in `launch/`. Nothing
here needs a decision you haven't already made — just execution.

> **Your wedge sentence** (use it *identically* everywhere — site, posts, replies):
> *"When a swarm of agents does something wrong, you can't reproduce it or say which
> agent caused it. Jaros records every decision in one hash-chained log, replays the
> whole hive to byte-identical state (zero model calls), and attributes any failure to
> the exact agent. Zero infrastructure."*

> **Your opening hook** (lead with it on *every* post, every platform):
> *"When an agent 'does something wrong' — sends the wrong email, deletes the wrong
> file — it's almost never a dumb model. We wired the model's output straight to the
> trigger. That's a design flaw, not a model flaw — and no prompt fixes a design flaw."*
> — your own line from the June 9 post. It's your best sentence. Reuse it everywhere.

## Two goals, two channels (don't confuse them)

You have two aims and they live on different platforms — track them separately:

| Goal | Where | What "working" looks like |
| --- | --- | --- |
| **Win developers** (adoption) | Show HN · r/LocalLLaMA · r/LLMDevs · X | completed quickstarts, issues from real use, someone ships on it |
| **Win a job** (personal brand) | LinkedIn | profile views, follower growth, eng-leaders/recruiters reaching out |

**You already ran a v1 launch — on LinkedIn (June 9).** It used the single-agent
**"design flaw, not a model flaw → a deterministic clerk reads each slip against the
rulebook"** framing (the LLM decides WHAT, a deterministic system decides HOW). Numbers
as of June 17: **1,004 impressions, 16+ reactions (incl. Kavita Sunku), still 0
comments, 0 reposts.** Read it right: the *reach* is a real, working **job** signal —
that's a strong day-one number for a solo infra post — don't dismiss it. Two things to
fix, both addressed below: (1) **zero conversation** (likes, then scroll) — the post sent
readers to GitHub instead of ending on a question; (2) it sells the *single-agent* story
and **omits your actual differentiator — the swarm**: replay a whole hive byte-identically
and attribute any failure to the exact agent. That swarm-accountability angle is the
**LinkedIn follow-up (v2)** below, and it's also what you haven't yet taken to the
**developer channels at all** (HN/Reddit/X). The relaunch fixes both.

There's also a **third, longer-horizon goal — a monetizable product someday** — and you
want all three moving at once. The senior way: treat it as **option value**, not a third
workstream. A handful of cheap choices now (see the *Parallel Track* below) keep
monetization wide open without stealing the focus adoption + the job hunt need. Do **not**
start building a paid product yet — that would drain the oxygen from the two goals above.

---

## PHASE 0 — Capitalize on the live post (this week, ~30 min)

The June 9 LinkedIn post is live and traveling (1,004 impressions). Don't let it go
cold while you prep the dev launch:

- [ ] **Reply to / thank early reactors by name** in the post — especially Kavita Sunku
      and anyone in eng leadership. Author engagement is what re-surfaces the post.
- [ ] **Seed one comment yourself** that plants the swarm hook (so the post isn't all
      likes-then-scroll): *"The part I didn't get to here: this isn't just one agent —
      you can replay a whole hive byte-for-byte and name the exact agent behind a
      failure. More on that soon."* It turns the dead comment section into a teaser for v2.
- [ ] **DM Swagath** (Coinbase AI director, now a connection) — short, no ask. Point him
      at the post + repo and the *accountability* angle (it's his world). Draft:
      *"Great talking the other day. Finally open-sourced the thing I mentioned — Jaros,
      a deterministic runtime for agent swarms: replay a whole hive byte-for-byte and
      attribute any failure to the exact agent (the EU AI Act Art. 12 accountability
      angle for regulated/fintech). Repo: github.com/jaredpilcher/Jaros — would love
      your read."*
- [ ] **Queue the swarm-apex follow-up (LinkedIn v2)** for Day 3 of launch week — it's
      written in `posts/lobsters-devto-linkedin.md`. This is the post that carries your
      real differentiator and the regulated-market story Swagath cares about.

---

## PHASE 1 — Pre-launch gate (≈1 day, do before posting anything)

### 1. Publish to PyPI so `pip install jaros` works
- [ ] Check the name is free: open <https://pypi.org/project/jaros/>. If taken,
      pick `jaros-os` and update `name` in `pyproject.toml` + every `pip install`
      mention (site, README, posts).
- [ ] Build + upload:
  ```bash
  pip install build twine
  python -m build
  twine upload dist/*        # needs a PyPI account + API token
  ```
- [ ] Verify in a clean venv: `pip install jaros && jaros --help`.

### 2. Smooth the first run — ✅ **DONE (shipped in 0.3.0 / EXT-008)**
- [x] **One-command bootstrap** — `jaros init --with-examples` scaffolds the 11-dir
      layout + stages 7 example agents, 5 tools, evals, schedules. Verified on a fresh dir.
- [x] **data-dir auto-discovery** — CLI resolves `$JAROS_DATA_DIR` else `./.jaros-data`;
      the repeated `--data-dir` flag is gone from every example.
- [x] **`serve` shows the web console by default** (one-click replay in a browser;
      `--no-console` for headless) — so the wow is visible without a second terminal.
      The README still notes the CLI-only flow uses a second terminal for `submit`/`watch`.

> These were the two P1 conveniences from the audit. They're done — the first-run
> friction is gone. What remains in Phase 1 is PyPI publish, badges, the replay clip,
> the landing page, and the independent clean-image dry run.

### 3. Trust signals on the README
- [ ] Badges at the top: CI status, PyPI version, **MIT**, Python 3.10–3.12.
- [ ] First line under the title is the wedge sentence.
- [ ] The replay GIF/clip is visible above the fold.

### 4. Record the 30–40s replay clip (your most-reused asset)
- [ ] Screen-record the console's one-click replay: decision log → **Replay** →
      "byte-identical, 0 model calls". Keep it < 40s, no audio needed.
- [ ] Save as `docs/replay.mp4` (and a `.gif` for README/X). Optionally drop the
      `.mp4` into the landing page (`launch/site/index.html`, `<!-- REPLAY CLIP -->`).

### 5. Publish the landing page
- [ ] Follow `launch/site/README.md` (GitHub Pages / Netlify / Vercel — ~2 min).
- [ ] Put the live URL in: repo **About → Website**, your X bio, and swap every
      `YOUR-SITE` placeholder in `launch/blog/01` and `02`.

### 6. The real gate — a clean-image dry run
- [ ] Fresh container/VM → `pip install jaros` → boot → `jaros submit …` →
      `jaros replay` → **see byte-identical in under 5 minutes.**
- [ ] Have **one person who isn't you** do it cold. Fix every stumble before posting.
- [ ] `pytest -q` green + all 5 guardrails (`check_planes/no_server/comms/zero_infra/determinism`).

**Gate:** all of Phase 1 ticked → you're cleared to launch. ✅

---

## PHASE 2 — Launch week (target Tue–Thu). Times = US Eastern.

> Pre-written assets: blog → `launch/blog/`, posts → `launch/posts/`.
> Golden rules: **open every post with the hook line above**, and **reply fast and
> kind for the first 6 hours.** That's the launch.
> Note: the June 9 LinkedIn post was v1 on the *job* channel. This week is the **real**
> launch — it hits the *developer* channels you skipped, plus a stronger LinkedIn v2.

### Day 1 — Tuesday (the main launch)
- [ ] **08:30** Publish `blog/01-flaky-agent-ci.md` on your site (URL you control).
- [ ] **09:00** **Show HN** — `posts/show-hn.md` (title option #1). Open the first
      comment with the **"design flaw, not a model flaw"** hook. ⛔ Never ask for upvotes.
- [ ] **09:15** **X thread** — `posts/x-thread.md`, lead with the replay clip. Pin it.
- [ ] **09:30** **r/LocalLLaMA** — `posts/reddit.md` variant A.
- [ ] **All day** Reply to every comment within ~15–30 min. Use the reply templates
      in `posts/show-hn.md`. Never defensive — *"fair, here's the tradeoff."*

### Day 2 — Wednesday
- [ ] **09:00** **r/LLMDevs** + **r/AI_Agents** — `posts/reddit.md` variant B.
- [ ] **Lobsters** + **dev.to** cross-post of blog 01 (set canonical URL → your site).
- [ ] Triage overnight issues; fix easy ones same-day, thank reporters by name.

### Day 3 — Thursday
- [ ] **09:00** **r/MachineLearning** `[P]` — `posts/reddit.md` variant C (technical framing).
- [ ] **LinkedIn v2 — the swarm-apex follow-up** (copy in `posts/lobsters-devto-linkedin.md`).
      This is the post that adds what June 9 left out: **swarm reproducibility &
      accountability** — replay a whole hive byte-for-byte, attribute any failure to the
      exact agent. It's your real differentiator *and* the regulated-market (fintech/crypto)
      story — the one Swagath at Coinbase feels. Make it earn **comments**, not just likes
      (June 9 got 16 reactions / **0 comments**). Fix exactly what June 9 missed:
  - Open with the swarm hook in the first 1–2 lines (all that shows before "…see more"):
    *"When a swarm of AI agents 'does something wrong,' can you reproduce it — and say
    which agent caused it?"* It decides who expands.
  - **Native-upload the 30s replay video.** **No external link in the body** (LinkedIn
    throttles outbound links); put the GitHub link in the **first comment**.
  - **End on a question** to pull conversation *into the comments* — e.g. *"For people
    running multi-agent systems: when a swarm misbehaves in prod, how does your team
    reproduce it and figure out which agent was responsible — today?"* (June 9 sent
    everyone to GitHub → 0 comments.)
  - **Seed it:** ping 5–10 relevant people right after posting; reply to every comment
    within the hour. Early comments are what expand reach.
  - Draft to adapt: `posts/lobsters-devto-linkedin.md` (LinkedIn section).

### Day 4–5 — cool off
- [ ] Convert every "this is cool" into *"want me to help you try it on your agent?"*
      → seeds your first design partner.

---

## PHASE 3 — Week 2 (convert the skeptics)
- [ ] Run `python launch/benchmark/run_reproducibility_benchmark.py`, paste the real
      output, publish `blog/02-deterministic-replay-vs-time-travel.md`.
- [ ] (Optional) add the LangGraph side-by-side — see `launch/benchmark/README.md`
      (run it; never fabricate numbers).
- [ ] **Build + publish reference agent #1 — `repo-fixer`** (spec: `launch/reference-agents.md`).
      This is your "here's a *real* agent — now replay its run byte-for-byte" proof.
      Ship it with its deterministic eval and a 30s replay clip. **Claim only
      reproducible/replayable/auditable — never "production-ready."**
- [ ] Re-share blog 02 + the reference-agent clip to the channels that received the launch well.
- [ ] Open **GitHub Discussions or a Discord**; link it from the README.

---

## PHASE 4 — Weeks 3–8 (the flywheel + on-ramps)
- [ ] **Build reference agents #2 `extractor` and #3 `researcher`** (spec:
      `launch/reference-agents.md`), one at a time. Each gets a deterministic eval, a
      short "Build a reproducible \<X\> agent" SEO page/blog, and a README example.
      These are recognizable on-ramps *and* design-partner conversation starters.
- [ ] Land **3–5 design partners** — inbound from pain: when someone posts
      "my agent is non-deterministic / I can't reproduce this," reply and help.
      (A reference agent that matches their use case is the perfect opener.)
- [ ] Work each one hands-on + free until their agent is reproducible → case study.
- [ ] Your AI-learning site = design-partner #1 (dogfood + case study). Get others too.
- [ ] **Only after the three land:** spec **bring-your-own-agent** (a thin adapter so
      people run *their* existing agent on Jaros and gain replay for free — additive,
      not parasitic). See the follow-up note in `launch/reference-agents.md`.

> ⚠️ **Reference-agent guardrail:** build the *pattern*, never clone a named project;
> ship ≤3 done well (not 30 clones); the eval ships with the agent; and the claim is
> always the narrow true one (reproducible/replayable/auditable/least-privilege),
> never "the production-ready version of X." This is the same over-claiming line that
> protects the whole project.

---

## PARALLEL TRACK — keep the monetization door open (cheap, non-distracting)

You want a *possible* product one day. The move is **option value**: a few cheap choices
now that keep monetization open while spending ~zero focus on it. Building a paid product
now would steal the oxygen the two goals above need — so don't. Just don't foreclose it.

**The model (proven): open-core.** The runtime stays free + MIT forever — that's what wins
adoption *and* your job. The *paid* layer, later, is what teams pay for — never the core:
- **Jaros Cloud** — hosted replay & audit: a team's run history, searchable, retained,
  shareable. (Replay-as-a-service is the natural SaaS.)
- **Team / console-pro** — shared dashboards, RBAC/SSO, retention, compliance/audit exports.
- **Managed multi-node / support** — for the few who outgrow single-node.

**Cheap moves to make now (each well under an hour; none distracts from launch):**
- [ ] **Keep the commercial surface modular.** Core runtime = free/MIT; anything paid-shaped
      later (cloud, console-pro, team features) lives in a *separate* component. The console
      already is — keep it that way; don't entangle paid-shaped features into the MIT core.
- [ ] **License discipline.** MIT the *core* (adoption). Build future paid features as **new
      code under your own terms** — **never relicense what you already gave away** (the
      HashiCorp / Redis backlash is the cautionary tale).
- [ ] **Own the brand.** Claim the GitHub org, the domain, the PyPI/npm name, and the social
      handles now; consider a "Jaros" trademark eventually. Cheap insurance.
- [ ] **Capture demand, don't sell.** Add a one-line **"Jaros Cloud — notify me"** email
      capture + a **"Teams / Enterprise — talk to us"** link to the landing page. Zero
      selling; it builds a waitlist and *evidence of willingness-to-pay* for later.
- [ ] **Write a one-paragraph business-model hypothesis** (open-core: free runtime, paid
      cloud/team/compliance). Keep it private — it doubles as **interview gold** ("here's how
      I'd monetize it") without doing any of the work now.

> **The honest tension** (be ready to speak to it): MIT + "become the standard" + "monetize
> later" is the Docker story — the tech can win while the company struggles, because value
> leaks to whoever operates at scale. Open-core with a hosted layer is the proven answer, and
> the time to set the *seams* is now (keep paid-shaped surface separable) — even though you
> build none of it yet.

---

## The numbers that mean it's working (not stars, not revenue)

**Developer axis** (adoption):
- [ ] Strangers **complete the quickstart**.
- [ ] Issues arrive from **real usage**, not "won't install."
- [ ] **Someone ships on Jaros without you in the room.** ← the moment it's real.

**Job axis** (the goal that's already showing signal):
- [ ] **Profile views + followers** from posts (June 9 already drove 1,004 impressions — amplify it).
- [ ] **Comments** on the LinkedIn post (June 9 got 0 — the metric to move with the swarm v2).
- [ ] **A reply from Swagath** (or any eng leader) to the DM / post — the warmest job signal there is.
- [ ] Inbound from **eng leaders / recruiters** who saw the project.

**Monetization signal** (option-value — watch passively, sell nothing):
- [ ] Waitlist signups for "Jaros Cloud / team features."
- [ ] Anyone asking "can I pay for hosted replay / audit / retention?" — write it down.

> Reactions/likes are vanity here. The signals that matter are *people clicking through
> to you* (job) and *people running the thing* (developers).

## The one rule for the next two months
**Hold scope.** After Phase 1 the bottleneck is attention + design partners, not
code. Deepen the moat (replay + capability-safety + zero-infra). Don't widen it.

---

### Quick links
| Need | File |
|---|---|
| Full strategy/runbook | `launch/README.md` |
| Landing page + hosting | `launch/site/index.html`, `launch/site/README.md` |
| Quickstart fixes (status) | `launch/quickstart-audit.md` |
| Launch blog (centerpiece) | `launch/blog/01-flaky-agent-ci.md` |
| Benchmark blog (week 2) | `launch/blog/02-deterministic-replay-vs-time-travel.md` |
| Show HN + reply templates | `launch/posts/show-hn.md` |
| Reddit variants | `launch/posts/reddit.md` |
| X thread | `launch/posts/x-thread.md` |
| Lobsters / dev.to / LinkedIn | `launch/posts/lobsters-devto-linkedin.md` |
| Runnable benchmark | `launch/benchmark/run_reproducibility_benchmark.py` |
| Reference agents (build spec) | `launch/reference-agents.md` |
