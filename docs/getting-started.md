# Getting started — day one to production

A linear path from `pip install` to a reproducible, scheduled, evaluated,
distributed agent system. Every command here is real and tested.

The core loop at a glance — submit work, check status, replay it byte-identically with zero model calls, and run the eval suite (a real session, captured verbatim):

![A real Jaros CLI session: submit, status, replay --json, and a green eval suite](cli.png)

> **Mental model.** Agents *propose* inert `Decision` data; a deterministic
> Execution Plane decides whether and how to run it. The only non-determinism is
> the model's output, captured as data — so runs **reproduce by replay** and a
> misbehaving agent **can only touch what it was granted**. No server, database,
> or broker: just files and threads.

## 1. Install and scaffold a node

```bash
pip install jaros
jaros init --with-examples   # scaffolds ./.jaros-data with bundled example agents/tools/evals/schedules
```

`jaros init --with-examples` creates the data dir and stages a library of example
agents and tools (the read-only health/disk/inventory/text agents and the swarm
hive), so everything below has something to run — and the [console](../console/)
shows installed agents right away.

> Every command discovers the data dir automatically: it uses `./.jaros-data` by
> default, or `$JAROS_DATA_DIR` if set, or `--data-dir DIR` to override. The rest
> of this guide just relies on the default, so no flag is needed.

In a hurry? Point your coding agent (such as **Claude Code**) at
[`agent-kit/`](../agent-kit/), tell it to read the kit, and it learns Jaros and
builds + verifies agents for you — more in [step 3](#3-the-read-only-library-already-installed).

> Hacking on Jaros itself? Clone the repo and `pip install -e ".[dev]"` instead,
> then `pytest` (full suite + architecture guardrails should pass).

## 2. Run the OS and your first job

```bash
jaros serve &                          # the long-running node (+ web console)
jaros submit system-health             # a bundled example agent
jaros submit advance --input '{}'      # the built-in agent
jaros status                           # state, processed, schedules
jaros watch                            # live status + new results
```

`jaros serve` prints a short banner — data dir, model, and the console URL
(http://localhost:5500) — then stays quiet, logging only meaningful events (a job
completing or failing, a schedule firing), not a per-tick heartbeat. It also brings
the [web console](#8-watch--drive-everything-from-the-browser) up by default; pass
`--no-console` to skip it. `jaros watch` is likewise change-only: it reprints the
status line only when it changes and adds one line per new result.

Each accepted decision is recorded to `.jaros-data/state/decisions.log`; every mediated
action to `.jaros-data/state/audit.log`.

## 3. The read-only library (already installed)

`--with-examples` staged the [read-only library](../examples/readonly/) — agents
that only read (health, disk, inventory, text), safe to run anywhere. Try a few:

```bash
jaros submit disk-monitor --input '{"path":"."}'        
jaros submit text-metrics --input '{"path":"README.md"}'
```

Write your own agent (a `ReasoningBoundary` that emits `Decision` data) and a
read-only tool (`NAME`/`validate`/`execute`); see
[docs/building-agents.md](building-agents.md) and the [examples](../examples/).

**Or let your coding agent build it.** Point your coding agent — **Claude Code**,
Cursor, or similar — at [`AGENTS.md`](../AGENTS.md) → [`agent-kit/`](../agent-kit/)
and tell it to read what's there. The kit hands it the whole project in one
folder — the mental model, a skill per artifact, accurate API reference, and
runnable templates — so it learns how Jaros is meant to be used and authors +
verifies new agents and tools for you right away. Just say *"read `agent-kit/`
and build me an agent that does X."*

## 4. Schedule them (native, no external cron)

The example schedules came with `--with-examples` (one interval, one cron). The
daemon dispatches them natively:

```bash
jaros status   # see schedules + next/last run
```

Schedules are crash-safe: a restart neither double-fires nor skips. See
[EXT-011](../.jarify/EXT-011/requirements.md).

## 5. Evaluate agents (reproducible tests)

```bash
jaros eval        # runs the bundled evals/; exit 0 iff all pass
```

CI-friendly and reproducible — no model-grading flakiness. See
[EXT-013](../.jarify/EXT-013/requirements.md).

## 6. Reproduce a run by replay

The headline guarantee, in one command — reconstruct the entire run from the
recorded decisions, **byte-identical, with no model call**:

```bash
jaros replay          # human report; exit 0 reproducible, 1 divergence, 2 nothing
jaros replay --json   # { decisions, modelCalls:0, finalState, byteIdentical, ok }
```

Replay re-applies the decision log through the runtime's **own** handlers into a
fresh sandbox (it never touches the live data dir) and compares the rebuilt
transition log to the original. The guarantee rests on handler determinism, which
`scripts/check_determinism.py` gates in CI; replay's divergence path (exit 1) is
the user-facing version of that same check. Also available from the
[web console](../console/) Reproducibility page or in code via `jaros.state.replay`.

## 7. Reproduce a whole *swarm* — and find the culprit

The same guarantee scales from one agent to a **hive**. Stand up a swarm
(planner -> worker -> reviewer), seed a bad handoff, and replay the *whole* run —
byte-identical, no model call — with every decision attributed to the agent that
made it. Every agent reaches the model through the one `LlmClient` interface; the
demo uses the deterministic **mock** by default (no model server). Point it at a
real small model by setting `config/llm.json` to `{"provider":"ollama"}`.

The swarm hive (planner/worker/reviewer + the handoff tool) also came with
`--with-examples`, so just run it:

```bash
for t in "login fails" "double charge"; do
  jaros submit planner  --input "{\"ticket\":\"$t\"}"
  jaros submit worker   --input "{\"ticket\":\"$t\"}"
  jaros submit reviewer --input "{\"ticket\":\"$t\"}"
done
jaros submit worker --input '{"ticket":"refund","bad":true}'  # seed a bad handoff

jaros replay          # per-agent summary + the attributed agent/decision
jaros replay --json   # adds byAgent + attribution (modelCalls:0, byteIdentical)
```

`jaros replay` reconstructs every member's decisions in recorded order to
byte-identical state and, for the seeded bad handoff, pinpoints the exact agent
and decision that produced it — by recorded fact, from the one ordered,
hash-chained, per-agent decision log. End-to-end in Docker:
`python tests/integration/run_swarm_replay_demo.py`. See
[examples/swarm/](../examples/swarm/) and [EXT-015](../.jarify/EXT-015/requirements.md).

## 8. Watch + drive everything from the browser

`jaros serve` already started the console — open **http://localhost:5500**. It
ships in the wheel (a prebuilt SPA + a pure-stdlib server), so **`pip install
jaros` gives you the console with no Node toolchain**. Submit jobs, install
agents/tools, manage schedules, run evals, browse + replay the decision log, and
inspect the state machine and harness — all over the shared file system; the node
stays serverless.

```bash
jaros console --console-port 8080   # run just the console (no daemon), on a port you pick
jaros serve --no-console            # or skip it entirely
```

For console **development** (React hot-reload against a checkout), run the
TypeScript bridge instead — `cd console && npm install && npm run dev`. See the
[console README](../console/README.md).

## 9. Deploy in Docker (one node, then many)

```bash
docker build -t jaros .
docker run -d --name jaros_os -v ${PWD}/.jaros-data:/data jaros
jaros submit advance --input '{}'          # host CLI drives the container over ./.jaros-data
```

**Distributed:** run several containers on the *same* shared volume. Each job is
claimed by an atomic `inbox → claimed` rename, so it is processed **exactly
once** and siblings skip it — no broker, no consensus service. Proven by
`python tests/integration/run_distributed_demo.py`.

## Enterprise notes

- **Reproducibility & forensics** — pin `state/decisions.log`, replay to
  reproduce; `state/audit.log` is a durable record of every allowed/denied action.
- **Capability-safety** — agents run under least-privilege roles (`FsReadRole`
  for read-only); a bug can't reach what it wasn't granted. Real isolation against
  hostile code is the host's job (process/container/VPC).
- **Zero-infra & scope honesty** — no server/database/broker (enforced by
  `scripts/check_zero_infra.py`); single-node-first with bounded multi-node
  coordination over the shared FS. Not a cluster-scale replacement for
  Temporal/Dapr — by design.
- **Day-one flexibility** — drop-in agents and tools, native scheduling,
  built-in evals, a config-swappable LLM, and a console, all on `pip install`.
