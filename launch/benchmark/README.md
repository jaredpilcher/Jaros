# Reproducibility benchmark

A **runnable** proof of Jaros's headline claim, for use in the launch posts. No
fabricated numbers — you run it, you paste what it prints.

## Run it

```bash
pip install -e .        # or: pip install jaros
python launch/benchmark/run_reproducibility_benchmark.py
```

### What it does

1. **Records an agent run** — the reasoning emits inert `Decision` data, which is
   appended to a durable decision log (exactly as the daemon does).
2. **Replays it 5× into fresh, isolated state** through the deterministic executor
   (`jaros.state.replay(dlog, executor.apply, log=fresh)`), hashing the rebuilt
   transition log each time. **No model is called on replay.**
3. **Contrasts** with a typical "model-drives" step whose output depends on live
   state (clock/RNG — a stand-in for live tool calls + an un-pinned model), run 5×.

### Representative output

```
[Jaros]  recorded run replayed 5x into fresh isolated state
         model calls on replay : 0
         distinct state hashes : 1  (1 == byte-identical)
         => REPRODUCIBLE       : True

[Typical 'model-drives' loop] same step run 5x
         distinct outputs      : 5
         => REPRODUCIBLE       : False
```

**The headline for your post:** *"Replayed a recorded agent run 5 times into fresh
state — byte-identical every time, zero model calls. The same logic in a
model-drives loop produced 5 different results."*

## Why this is honest

- The Jaros side uses the **real** `record_decision` / `replay` / executor APIs —
  not a mock. If a handler were non-deterministic, the hashes would differ and the
  benchmark would say so (that's literally what `scripts/check_determinism.py`
  guards in CI).
- The contrast loop is labeled as a *stand-in* for the typical pattern, not a
  strawman of a specific competitor. You're showing the **property** Jaros has and
  the default pattern lacks — not claiming a rigged head-to-head.

## Optional: the LangGraph side-by-side (for blog 02)

If you want the literal A/B for the technical post, add a second script that builds
a tiny LangGraph graph with a node that calls `time.time()`/`random`, checkpoints
it, and uses **time-travel** to re-run from a checkpoint — then show the node
re-executes and the result changes. This isn't a knock; it's the documented
behavior: LangGraph time-travel *re-executes* nodes, so LLM/IO/side-effects fire
again and may differ. (Source:
<https://dev.to/sreeni5018/debugging-non-deterministic-llm-agents-implementing-checkpoint-based-state-replay-with-langgraph-5171>.)

Keep that script in its own file, gate it behind `pip install langgraph`, and
**do not commit fabricated numbers** — run it, screenshot it, cite the version.
The contrast you're drawing is *state-snapshot rewind (re-executes)* vs
*record-and-replay (re-injects recorded decisions)*. That distinction is the
whole technical story of blog 02.

## Caveat to state plainly (it strengthens you)

Byte-identical replay holds **because executor handlers are deterministic**. Jaros
makes that checkable (`replays_agree`, `Expect.deterministic`) and checked in CI
(`check_determinism.py`). Say so — pre-empting the one critique a careful reviewer
will raise ("what if a handler isn't pure?") is more persuasive than hiding it.
