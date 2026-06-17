# Reference — workflow

The CLI loop for authoring and verifying. Use a throwaway data dir (set `JAROS_DATA_DIR`) for
experiments — never one a daemon you don't own is using.

```bash
export JAROS_DATA_DIR=/tmp/jaros
# 1. stage your artifacts (or copy a template to start)
mkdir -p $JAROS_DATA_DIR/agents $JAROS_DATA_DIR/tools $JAROS_DATA_DIR/evals $JAROS_DATA_DIR/schedules
cp agent-kit/templates/agent.py    $JAROS_DATA_DIR/agents/word_count_agent.py
cp agent-kit/templates/tool.py     $JAROS_DATA_DIR/tools/word_count_tool.py
cp agent-kit/templates/eval.json   $JAROS_DATA_DIR/evals/word_count.json

# 2. run the node (long-running); it loads agents/ + tools/ on each tick
jaros serve &

# 3. submit a job and inspect
jaros submit word-count --input '{"path":"README.md"}'
jaros status          # state, processed, schedules
jaros watch          # live status + new results

# 4. VERIFY your work
jaros eval          # exit 0 iff all eval cases pass
jaros replay --json   # { decisions, modelCalls:0, byteIdentical, ok }
```

## Commands

| Command | What it does |
| --- | --- |
| `jaros serve` | Run the node: watch `inbox/`, load `agents/`+`tools/`, process jobs. |
| `jaros submit <agent> --input <json>` | Write a job to `inbox/` (the only entry point). |
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
