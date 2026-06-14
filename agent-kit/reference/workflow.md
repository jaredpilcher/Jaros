# Reference — workflow

The CLI loop for authoring and verifying. Use a throwaway `--data-dir` for
experiments — never one a daemon you don't own is using.

```bash
DATA=/tmp/jaros

# 1. stage your artifacts (or copy a template to start)
mkdir -p $DATA/agents $DATA/tools $DATA/evals $DATA/schedules
cp agent-kit/templates/agent.py    $DATA/agents/word_count_agent.py
cp agent-kit/templates/tool.py     $DATA/tools/word_count_tool.py
cp agent-kit/templates/eval.json   $DATA/evals/word_count.json

# 2. run the node (long-running); it loads agents/ + tools/ on each tick
jaros serve  --data-dir $DATA &

# 3. submit a job and inspect
jaros submit word-count --input '{"path":"README.md"}' --data-dir $DATA
jaros status --data-dir $DATA          # state, processed, schedules
jaros watch  --data-dir $DATA          # live status + new results

# 4. VERIFY your work
jaros eval   --data-dir $DATA          # exit 0 iff all eval cases pass
jaros replay --data-dir $DATA --json   # { decisions, modelCalls:0, byteIdentical, ok }
```

## Commands

| Command | What it does |
| --- | --- |
| `jaros serve` | Run the node: watch `inbox/`, load `agents/`+`tools/`, process jobs. |
| `jaros submit <kind> --input <json>` | Write a job to `inbox/` (the only entry point). |
| `jaros status` / `jaros watch` | Inspect / live-follow state, counts, schedules. |
| `jaros add-agent <file.py>` | Install an agent module into `agents/`. |
| `jaros eval` | Run `evals/*.json`; exit 0 iff all pass (CI-friendly). |
| `jaros replay [--json]` | Rebuild the run from the decision log, byte-identical, no model call. |

## What "done" looks like for an authored artifact

1. `jaros eval` passes (exit 0) — the decision and (optionally) the executed
   result match expectations.
2. `jaros replay --json` reports `"modelCalls": 0` and `"byteIdentical": true` —
   the run is reproducible, i.e. your `execute()` is deterministic.
3. The whole repo's suite still passes: `pytest`.

See also: [architecture.md](architecture.md) · [public-api.md](public-api.md)
