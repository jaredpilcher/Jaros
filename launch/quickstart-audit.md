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

### ✅ P0 — End the quickstart on the *wow* (the replay) — **DONE (shipped: EXT-008)**

The quickstart used to stop at `submit` + `watch` — "it runs an agent," which every
framework does, never showing the differentiator. **This is now fixed:** `jaros
replay` ships, the README quickstart ends on it, and it's the single command that
makes the value land:

```bash
jaros replay --data-dir .jaros-data
# replayed 2 recorded decisions (2 applied) - model calls: 0
#   reconstructed state : DONE
#   byte-identical      : yes
# reproducible: the recorded decisions reconstruct the run exactly, with no model call.
```

Verified end-to-end (submit → process → replay): byte-identical, exit `0`,
`--json` emits `{decisions, modelCalls:0, finalState, byteIdentical, ok}`, empty
log → exit `2`, divergence → exit `1`, and replay touches **nothing** in the live
data dir (it reconstructs into an isolated sandbox, reusing the production handlers
via `jaros/execution/handlers.py`). Tests in `tests/test_cli_replay.py`.

Two supporting "wow" assets also exist and stay useful:
- `python launch/benchmark/run_reproducibility_benchmark.py` — the 5×, 0-model-call,
  byte-identical-vs-divergent-loop benchmark (great for the blog/posts).
- The **console's one-click replay** (screenshot in the README) — the visual version.

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
jaros replay                 # ✅ ships today (EXT-008)
```

`jaros submit/watch/replay` (steps 3–4) all work today. The only remaining
"(after …)" gaps are the two P1 conveniences — `pip install jaros` (PyPI) and
`jaros init --with-examples` — each an afternoon, and neither blocks the wow.

---

## Pre-launch checklist (gate for posting)

- [x] **The wow is a single command in the path: `jaros replay` (EXT-008, verified).**
- [x] No API key required anywhere in the path (default echo adapter, offline).
- [x] The wow (`jaros replay`) is the *last thing the visitor sees* in the quickstart.
- [ ] Fresh container: install → boot → submit → **replay** in < 5 min (re-run on a clean image).
- [ ] `pip install jaros` works (PyPI) **or** the editable fallback is crystal clear.  ← P1
- [ ] One-paste bootstrap (`jaros init --with-examples`) + second-terminal callout.  ← P1/P2
- [ ] Badges (CI, PyPI, MIT, Python versions) on the README.  ← P2
- [ ] Someone who isn't you ran it start-to-finish and hit zero surprises.

**Status:** the P0 (wow-in-the-path) is done. What's left before posting is all
non-code polish — PyPI publish, one-command bootstrap, badges, and one clean-image
dry run.
