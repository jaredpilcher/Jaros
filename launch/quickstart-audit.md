# Quickstart audit — make the first run flawless

> The #1 reason good OSS projects die at launch is a try-it path that stalls on a
> fresh machine, or a value that takes 30 minutes to feel. Fix this **before** you
> post anything. Target: a stranger goes from zero to **seeing the wow in under 5
> minutes**, with no API key and no infrastructure.

I audited the current quickstart (README "Quickstart") against a clean-machine
mindset. Findings below, ordered by leverage.

---

## What's already great (keep + advertise)

- ✅ **`jaros` is a real console script** (`[project.scripts] jaros = jaros.cli:main`).
- ✅ **No API key to try.** The default model is a deterministic, dependency-free
  echo adapter — Jaros runs fully **offline**. This is a genuine friction win that
  most agent frameworks can't claim. **Say it loudly in the first line of the
  quickstart:** *"No API key. No database. No server. It runs offline."*
- ✅ **Zero-infra is real and enforced** (`scripts/check_zero_infra.py`). Great trust signal.
- ✅ Atomic FS ingestion means the two-terminal flow never sees partial state.

---

## Fixes, by leverage

### 🔴 P0 — The quickstart doesn't end on the *wow* (the replay)

The current quickstart stops at `submit` + `watch`. That demonstrates "it runs an
agent" — which every framework does. **It never shows the differentiator** (replay
to byte-identical state). A visitor leaves without feeling why Jaros is different.

**Fix (today, no code):** end the quickstart with the runnable benchmark, which
already prints the wow:

```bash
python launch/benchmark/run_reproducibility_benchmark.py
# => Jaros replay: 5x, 0 model calls, 1 distinct state hash (byte-identical)
#    typical loop: 5x, 5 distinct outputs (not reproducible)
```

…and a one-line pointer to the **console's one-click replay** (screenshot in the README).

**Fix (this week, small code — highest-leverage pre-launch task): add `jaros replay`.**
A user who just ran `jaros submit ...` should be able to do:

```bash
jaros replay --data-dir .jaros-data
# Replays state/decisions.log through the built-in handlers into fresh state,
# prints: decisions replayed, model calls (0), final state, and a byte-identical
# check vs the live transition log.
```

Spec: read `state/decisions.log` via `jaros.state.read_decisions`, register the
same built-in handlers the daemon uses (`advance`, `fs.write`), call
`jaros.state.replay(dlog, executor.apply, log=fresh_TransitionLog)`, hash both
logs, print the comparison. This turns the wow into a single command in the path
people already walk. **Do this before launch if you do nothing else on the code.**

### 🟠 P1 — Publish to PyPI so the try-path is `pip install jaros`

Today's quickstart uses `pip install -e ".[dev]"`, which requires cloning the repo
*and* pulls contributor-only dev deps. That's a contributor flow, not a try flow.

**Fix:** publish `0.1.0` to PyPI (the package name, version, and metadata are
ready). Then the first line becomes:

```bash
pip install jaros        # not ".[dev]" — that's for contributors
```

Keep the editable install in a separate "Contributing" section. (Verify the name
`jaros` is available on PyPI; if taken, decide on a fallback like `jaros-os` now,
before the launch hard-codes a name.)

### 🟠 P1 — Collapse the bootstrap to one command

The current flow asks the user to `mkdir -p`, then `cp examples/plugins/*.py` and
`cp examples/tools/*.py` by hand. Each manual step is a place to stumble.

**Fix:** add `jaros init --with-examples --data-dir .jaros-data` that creates the
layout and stages the example agents/tools. Until then, provide a copy-paste block
that's a *single* fenced command (chain with `&&`) so it's one paste, not four.

### 🟡 P2 — Make the two-terminal flow obvious + drop the repeated flag

`jaros serve` blocks, so newcomers don't realize they need a second terminal, and
every command repeats `--data-dir .jaros-data`.

**Fix:** (a) add a callout: *"`serve` runs in the foreground — open a second
terminal for the commands below."* (b) Lead with `export JAROS_DATA_DIR=.jaros-data`
once, then drop the flag from every example (the CLI already honors the env var).

### 🟡 P2 — Add the trust badges

**Fix:** README badges for CI status, PyPI version, license (MIT), and Python
versions. They're social proof for the visitor deciding whether to spend 5 minutes.

### ⚪ P3 — Minor

- The `Homepage`/`Repository` URLs use `…/Jaros` (capital). GitHub is
  case-tolerant, but pick one casing and use it consistently across README, posts,
  and package metadata so links and analytics don't fragment.
- Confirm `python tests/integration/run_local_demo.py` runs clean on a fresh clone
  (it's referenced as the no-Docker smoke test — it should be the safety net you
  point skeptics to).

---

## The improved quickstart (paste-ready target)

```bash
# 1. Install — no API key, no database, no server. Runs offline.
pip install jaros            # (after PyPI publish; until then: pip install -e .)

# 2. Boot the OS on a data dir (foreground — use a second terminal for step 3)
export JAROS_DATA_DIR=.jaros-data
jaros init --with-examples   # (after adding init; until then: mkdir+cp block)
jaros serve

# 3. In a second terminal: submit work, watch it run
export JAROS_DATA_DIR=.jaros-data
jaros submit greeter --input '{"name":"Jaros"}'
jaros watch

# 4. THE WOW: replay the whole run to byte-identical state, with zero model calls
jaros replay                 # (after adding replay; until then: run the benchmark)
```

Steps 1–3 exist today. Steps marked "(after …)" are the three small pre-launch
fixes above — none is more than an afternoon, and together they are the difference
between "looks interesting" and "oh, *that's* what it does."

---

## Pre-launch checklist (gate for posting)

- [ ] Fresh container: install → boot → submit → **see the wow** in < 5 min.
- [ ] No API key required anywhere in the path.
- [ ] The wow (replay/benchmark) is the *last thing the visitor sees*, not buried.
- [ ] `pip install jaros` works (PyPI) **or** the editable fallback is crystal clear.
- [ ] Badges + one-paste bootstrap + second-terminal callout in place.
- [ ] Someone who isn't you ran it start-to-finish and hit zero surprises.
