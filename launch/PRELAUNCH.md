# 🚀 Jaros launch — the do-this checklist

One page. Tick top to bottom. Every asset referenced lives in `launch/`. Nothing
here needs a decision you haven't already made — just execution.

> **Your wedge sentence** (use it *identically* everywhere — site, posts, replies):
> *"When a swarm of agents does something wrong, you can't reproduce it or say which
> agent caused it. Jaros records every decision in one hash-chained log, replays the
> whole hive to byte-identical state (zero model calls), and attributes any failure to
> the exact agent. Zero infrastructure."*

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

### 2. Smooth the first run (the two P1 conveniences from the audit)
- [ ] **One-command bootstrap** — add `jaros init --with-examples` *or* replace the
      README's `mkdir`/`cp` steps with a single `&&`-chained paste block.
- [ ] **Second-terminal callout** — README quickstart says: *"`serve` runs in the
      foreground — open a second terminal for the next steps."*
- [ ] Lead the quickstart with `export JAROS_DATA_DIR=.jaros-data` and drop the
      repeated `--data-dir` flag.

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
> Golden rule: **reply fast and kind for the first 6 hours.** That's the launch.

### Day 1 — Tuesday (the main launch)
- [ ] **08:30** Publish `blog/01-flaky-agent-ci.md` on your site (URL you control).
- [ ] **09:00** **Show HN** — `posts/show-hn.md` (title option #1). Post the prepared
      first comment immediately. ⛔ Never ask for upvotes.
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
- [ ] **LinkedIn** — `posts/lobsters-devto-linkedin.md` (builder story; design-partner inbound).

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

## The 3 numbers that mean it's working (not stars, not revenue)
- [ ] Strangers **complete the quickstart**.
- [ ] Issues arrive from **real usage**, not "won't install."
- [ ] **Someone ships on Jaros without you in the room.** ← the moment it's real.

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
