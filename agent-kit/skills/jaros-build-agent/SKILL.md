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
5. If the model should choose *what* happens, **let its answer drive the decision**
   — see the next section. Keep all effects in the tool, not the agent.

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

## Let the model DRIVE the decision (not just ride along)

This is the point of an agent. The LLM decides *what* — and that choice must shape
the **decision the executor acts on**: its `kind`, its `payload`, or the `events`
that drive the state machine. Do **not** call the model and then bury its text in a
cosmetic `note` while the real behaviour stays hardcoded — then the model decided
nothing.

The trick that keeps this reproducible: **parse the model's answer into inert data
and bake it into the decision.** The decision (with the model's choice in it) is
recorded, so `jaros replay` reconstructs the exact same outcome **with no model
call** — the model decides WHAT, the deterministic executor does HOW.

```python
import uuid
from jaros.core import create_decision
from jaros.llm import LlmRequest

KIND = "triage"

class TriageBoundary:
    def __init__(self, llm): self._llm = llm
    def decide(self, context) -> list:
        ticket = context.get("ticket", "") if isinstance(context, dict) else str(context)
        verdict = self._llm.complete(LlmRequest(prompt=(
            "Reply with ONLY one word: ACCEPT if this is a real request, REJECT if spam.\n\n"
            f"Ticket: {ticket}"))).text
        accepted = verdict.strip().upper().startswith("ACCEPT")
        # The model's verdict picks the events -> the reconstructed final state.
        events = ["start", "complete"] if accepted else ["start", "fail"]   # DONE vs FAILED
        return [create_decision(id=f"t-{uuid.uuid4().hex}", source=KIND, kind="advance",
                                payload={"events": events, "verdict": "accept" if accepted else "reject"})]

def build(llm): return TriageBoundary(llm)
```

A different model answer now yields a different recorded decision and a different
reconstructed state — and replay reproduces whichever the model chose, calling no
model. Parse defensively (models add fluff): match a keyword / first word, and pick
a sensible default so the deterministic mock (`provider: default`, which echoes the
prompt) still yields a valid decision and your evals stay reproducible. See the
runnable hive in [`examples/swarm/agents/`](../../../examples/swarm/agents/).

## Verify

Stage the agent (and its tool + an eval) and run `jaros eval` —
it must exit 0. Then `jaros replay --json` must report
`modelCalls: 0` and `byteIdentical: true`. See
[reference/workflow.md](../../reference/workflow.md).

## Rules (do not violate)

- Emit data only. No file writes, network, or handles inside `decide`.
- The payload must be JSON-serializable and round-trippable.
- If you call the model, its answer must **drive** the decision (kind / payload /
  events) — never a cosmetic note over hardcoded behaviour.
- See [reference/architecture.md](../../reference/architecture.md) and
  [reference/public-api.md](../../reference/public-api.md).
