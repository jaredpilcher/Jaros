---
name: jaros-build-agent
description: Use when creating a new Jaros agent — a ReasoningBoundary that reasons over a job's input and emits inert Decision data (never a side effect). Covers the KIND/build(llm)/decide contract and verification.
---

# Build a Jaros agent

An agent answers a job `kind`. It reasons over the job's input and returns a list
of inert `Decision` objects — data only, never a side effect. The effect for a
decision lives in a **tool** whose `NAME` equals the decision's `kind` (see
[jaros-build-tool](../jaros-build-tool/SKILL.md)).

## Contract

A `*.py` in the data dir's `agents/` folder must expose:

- `KIND: str` — the job kind this agent answers.
- `build(llm) -> ReasoningBoundary` — factory; `llm` is the shared client.
- the returned object has `decide(self, context) -> list[Decision]`.

## Steps

1. Copy [`templates/agent.py`](../../templates/agent.py) into `<data-dir>/agents/`.
2. Set `KIND` (what `jaros submit <KIND>` routes to).
3. In `decide`, read what you need from `context` (the job's parsed JSON input).
4. Return `create_decision(id=..., source=KIND, kind="<action>", payload={...})`.
   - `kind` must equal the executing tool's `NAME`.
   - `payload` is inert JSON only — `create_decision` rejects anything else.
5. If you need the model to choose *what* to do, call
   `self._llm.complete(LlmRequest(prompt=...))` and put the result in `payload`.
   Keep all effects in the tool, not the agent.

## Worked example

```python
import uuid
from jaros.core import create_decision

KIND = "word-count"

class WordCountBoundary:
    def __init__(self, llm): self._llm = llm
    def decide(self, context) -> list:
        path = context.get("path", "README.md") if isinstance(context, dict) else "README.md"
        return [create_decision(id=f"wc-{uuid.uuid4().hex}", source=KIND,
                                kind="text.wordcount", payload={"path": path})]

def build(llm): return WordCountBoundary(llm)
```

## Verify

Stage the agent (and its tool + an eval) and run `jaros eval --data-dir <dir>` —
it must exit 0. Then `jaros replay --data-dir <dir> --json` must report
`modelCalls: 0` and `byteIdentical: true`. See
[reference/workflow.md](../../reference/workflow.md).

## Rules (do not violate)

- Emit data only. No file writes, network, or handles inside `decide`.
- The payload must be JSON-serializable and round-trippable.
- See [reference/architecture.md](../../reference/architecture.md) and
  [reference/public-api.md](../../reference/public-api.md).
