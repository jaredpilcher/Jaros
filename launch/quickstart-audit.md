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
jaros replay
# replayed 6 recorded decisions across 5 agent(s) - model calls: 0
#   reconstructed state : DONE
#   byte-identical      : yes
#   tamper-evident chain: intact
#   attribution [FAILURE] : agent 'X' produced decision #N — reason: …
# reproduced byte-identically; any member's failing handoff is attributed to the exact agent.
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

### ✅ P1 — Collapse the bootstrap to one command — **DONE (shipped: EXT-008)**

The flow used to ask the user to `mkdir -p`, then `cp examples/agents/*.py` and
`cp examples/tools/*.py` by hand — each manual step a place to stumble. **Fixed:**
`jaros init --with-examples` now scaffolds the full 11-dir layout and stages the
bundled example agents/tools/evals/schedules in one command:

```bash
jaros init --with-examples
# initialized Jaros data dir: .jaros-data
#   layout: state, inbox, outbox, … (11 created)
#   examples staged: agents=7 tools=5 evals=1 schedules=2
```

### ✅ P2 — Two-terminal flow + drop the repeated flag — **DONE**

`jaros serve` blocks, so newcomers didn't realize they needed a second terminal,
and every command used to repeat `--data-dir .jaros-data`. **Fixed two ways:**
(a) **data-dir auto-discovery** — the CLI resolves the data dir from
`$JAROS_DATA_DIR`, else `./.jaros-data`, so the flag is gone from every example;
(b) **`serve` now launches the bundled web console by default** (`--no-console` to
opt out), so the "wow" is visible in a browser without a second terminal at all —
the console has one-click replay built in. The README still notes that the
CLI-only flow uses a second terminal for `submit`/`watch`.

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

# 2. Scaffold a data dir + bundled example agents (one command)
jaros init --with-examples   # creates ./.jaros-data; the CLI auto-discovers it

# 3. Boot the OS — also opens the web console (one-click replay) in your browser
jaros serve                  # add --no-console for headless; serve blocks the terminal

# 4. In a second terminal: submit work across agents, watch it run
jaros submit greeter --input '{"name":"Jaros"}'
jaros watch

# 5. THE WOW: replay the whole hive to byte-identical state, attribute any failure
jaros replay                 # ✅ ships today (EXT-008 / EXT-015) — 0 model calls
```

Every step works today. The data dir is auto-discovered (no `--data-dir`), `serve`
shows the console without a second terminal, and `replay` reconstructs the whole
swarm byte-identically and names the agent behind any failure. The only remaining
"(after …)" gap is `pip install jaros` (PyPI publish) — an afternoon, and it
doesn't block the wow.

---

## Pre-launch checklist (gate for posting)

- [x] **The wow is a single command in the path: `jaros replay` (EXT-008, verified).**
- [x] No API key required anywhere in the path (default echo adapter, offline).
- [x] The wow (`jaros replay`) is the *last thing the visitor sees* in the quickstart.
- [ ] Fresh container: install → `init` → boot → submit → **replay** in < 5 min (re-run on a clean image).
- [ ] `pip install jaros` works (PyPI) **or** the editable fallback is crystal clear.  ← P1
- [x] One-paste bootstrap (`jaros init --with-examples`) — shipped.
- [x] data-dir auto-discovery (no repeated `--data-dir`) — shipped.
- [x] `serve` shows the console by default (`--no-console` to opt out) — shipped.
- [ ] Badges (CI, PyPI, MIT, Python versions) on the README.  ← P2
- [ ] Someone who isn't you ran it start-to-finish and hit zero surprises.

**Status:** P0 (wow-in-the-path) and both P1 conveniences (`jaros init`, data-dir
discovery, console-by-default) are **done and verified on a fresh data dir**. What's
left before/around posting is non-code polish — PyPI publish, badges, and one
independent clean-image dry run.
