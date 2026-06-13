# Getting started — day one to production

A linear path from `pip install` to a reproducible, scheduled, evaluated,
distributed agent system. Every command here is real and tested.

> **Mental model.** Agents *propose* inert `Decision` data; a deterministic
> Execution Plane decides whether and how to run it. The only non-determinism is
> the model's output, captured as data — so runs **reproduce by replay** and a
> misbehaving agent **can only touch what it was granted**. No server, database,
> or broker: just files and threads.

## 1. Install

```bash
pip install -e ".[dev]"
pytest          # full suite + architecture guardrails should pass
```

## 2. Run the OS and your first job

Use a throwaway data dir (never one a daemon you don't own is using):

```bash
DATA=/tmp/jaros
jaros serve --data-dir $DATA &                       # the long-running node
jaros submit advance --input '{}'    --data-dir $DATA # built-in agent
jaros status --data-dir $DATA                          # state, processed, schedules
jaros watch  --data-dir $DATA                          # live status + new results
```

Each accepted decision is recorded to `$DATA/state/decisions.log`; every mediated
action to `$DATA/state/audit.log`.

## 3. Add read-only agents (many purposes, at once)

Drop in the [read-only library](../examples/readonly/) — agents that only read
(health, disk, inventory, text), safe to run anywhere:

```bash
cp examples/readonly/plugins/*.py $DATA/plugins/
cp examples/readonly/tools/*.py   $DATA/tools/
jaros submit system-health                       --data-dir $DATA
jaros submit disk-monitor --input '{"path":"."}' --data-dir $DATA
```

Write your own agent (a `ReasoningBoundary` that emits `Decision` data) and a
read-only tool (`NAME`/`validate`/`execute`); see
[docs/building-agents.md](building-agents.md) and the [examples](../examples/).

## 4. Schedule them (native, no external cron)

```bash
cp examples/readonly/schedules/*.json $DATA/schedules/   # interval + cron examples
jaros status --data-dir $DATA                            # see schedules + next/last run
```

Schedules are crash-safe: a restart neither double-fires nor skips. See
[EXT-011](../.jarify/EXT-011/requirements.md).

## 5. Evaluate agents (reproducible tests)

```bash
cp examples/readonly/evals/*.json $DATA/evals/
jaros eval --data-dir $DATA        # input -> expected decision/result; exit 0 iff all pass
```

CI-friendly and reproducible — no model-grading flakiness. See
[EXT-013](../.jarify/EXT-013/requirements.md).

## 6. Reproduce a run by replay

The headline guarantee: replaying the recorded decisions reconstructs the run to
**byte-identical state, with no model call** — and Jaros *verifies* the handler
determinism it depends on (`jaros.execution.replays_agree`). Drive it from the
[web console](../console/) (Reproducibility page) or in code via
`jaros.state.replay`.

## 7. Watch + drive everything from the browser

```bash
cd console && npm install
JAROS_DATA_DIR=/tmp/jaros npm run dev      # http://localhost:5500
```

Submit jobs, install agents/tools, manage schedules, run evals, browse + replay
the decision log, and inspect the state machine and harness — all over the shared
file system; the node stays serverless. See the [console README](../console/README.md).

## 8. Deploy in Docker (one node, then many)

```bash
docker build -t jaros .
docker run -d --name jaros_os -v ${PWD}/.jaros-data:/data jaros
jaros submit advance --input '{}' --data-dir .jaros-data
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
- **Day-one flexibility** — drop-in plugin agents and tools, native scheduling,
  built-in evals, a config-swappable LLM, and a console, all on `pip install`.
