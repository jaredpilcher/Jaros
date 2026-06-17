# Jaros Agent Kit

**For AI coding agents (and the developers who point them here).** This folder is
everything an agent needs to understand Jaros and author correct agents, tools,
evals, and schedules — without reading the whole codebase first. Point your AI
coding agent at this folder and it can get to work.

## Mental model (read this first)

Jaros is a zero-infrastructure agent OS. The one rule that governs everything:

> **An agent reasons and emits inert `Decision` data; a deterministic tool runs
> it.** The agent never performs a side effect. Because the only non-determinism
> (the model's output) is captured as data, every run **reproduces by replay**,
> byte-identically, with zero model calls — and a misbehaving agent can only touch
> what it was granted.

Full background: [`reference/architecture.md`](reference/architecture.md).

## What you can build, and the skill for each

| To build… | Use the skill | Start from |
| --- | --- | --- |
| An **agent** (emits decisions) | [`skills/jaros-build-agent`](skills/jaros-build-agent/SKILL.md) | [`templates/agent.py`](templates/agent.py) |
| A custom **tool** (runs a decision) | [`skills/jaros-build-tool`](skills/jaros-build-tool/SKILL.md) | [`templates/tool.py`](templates/tool.py) |
| An **eval** (reproducible test) | [`skills/jaros-write-eval`](skills/jaros-write-eval/SKILL.md) | [`templates/eval.json`](templates/eval.json) |
| A **schedule** (cron / interval) | [`skills/jaros-schedule-agent`](skills/jaros-schedule-agent/SKILL.md) | [`templates/schedule.json`](templates/schedule.json) |

## Reference (the real, current surface)

- [`reference/architecture.md`](reference/architecture.md) — the four rules
  (inert decisions, reproducibility, capability-safety, zero-infra).
- [`reference/public-api.md`](reference/public-api.md) — exact signatures and JSON
  shapes you write against.
- [`reference/workflow.md`](reference/workflow.md) — the `serve` / `submit` /
  `eval` / `replay` loop.

## The templates are a runnable example

The four templates form one coherent `word-count` example. Stage them and run the
suite — they pass unmodified, so they are a correct starting point, not pseudocode:

```bash
export JAROS_DATA_DIR=/tmp/jaros
mkdir -p $JAROS_DATA_DIR/agents $JAROS_DATA_DIR/tools $JAROS_DATA_DIR/evals
cp agent-kit/templates/agent.py  $JAROS_DATA_DIR/agents/word_count_agent.py
cp agent-kit/templates/tool.py   $JAROS_DATA_DIR/tools/word_count_tool.py
cp agent-kit/templates/eval.json $JAROS_DATA_DIR/evals/word_count.json
jaros eval        # -> 1/1 eval cases passed  (exit 0)
```

## How to finish (definition of done)

Whatever you author, verify it before you call it done:

1. `jaros eval` exits 0.
2. `jaros replay --json` shows `"modelCalls": 0` and
   `"byteIdentical": true` (your `execute()` is deterministic).
3. The repo suite still passes: `pytest`.

## Going deeper

- Worked, real artifacts: [`../examples/`](../examples/) (incl. the read-only library).
- The web console to drive it all: [`../console/`](../console/) and
  [`../docs/console.md`](../docs/console.md).
- Full intent and specs: [`../.jarify/`](../.jarify/) — the Prime Directive is
  `PRIME-001`; this kit is `EXT-014`.
