# Reference — public API

The exact surface an author uses. These signatures are current as of this repo;
they are mirrored by the runnable [templates](../templates/) and the working
[`examples/`](../../examples/).

## Building a decision

```python
from jaros.core import create_decision, Decision

create_decision(*, id: str, source: str, type: str, payload: JsonValue) -> Decision
```

- `id` — unique per decision (use `uuid.uuid4().hex`).
- `source` — the emitting agent's name.
- `type` — the discriminator; **must equal the tool `NAME`** that executes it.
- `payload` — inert, JSON-serializable data ONLY. `create_decision` proves it
  round-trips (`json.loads(json.dumps(payload)) == payload`) and raises otherwise.

`Decision` is a frozen dataclass: `id`, `source`, `type`, `payload`.

## The agent contract (`ReasoningBoundary`)

A module dropped in `agents/` must expose:

```python
NAME: str                       # the agent's name (what a job's `agent` field selects)

def build(llm) -> ReasoningBoundary
    # returns an object exposing:
    def decide(self, context) -> list[Decision]
    #   context is the job's parsed JSON input; return inert decisions only.
```

`build(llm)` receives the shared `LlmClient`; call `llm.complete(LlmRequest(prompt=...))`
to decide *what* to do, then put the result in the payload. (Use a model only for
the genuinely non-deterministic choice — keep effects in the tool.)

## The tool contract

A class dropped in `tools/`:

```python
from jaros.core.decision_gate import ValidationResult

class MyTool:
    NAME = "my.action"                       # equals the decision type

    def validate(self, decision) -> ValidationResult:
        # cheap, pure structural checks
        return ValidationResult.accept(decision)      # or .reject("why")

    def execute(self, decision, **collaborators) -> dict:
        # DETERMINISTIC effect; return inert data
        return {"tool": self.NAME, ...}
```

`ValidationResult.accept(decision)` / `ValidationResult.reject(reason: str)` are the
only two outcomes.

## Eval case JSON (`evals/*.json`)

A file is one case object or a list of them. `name` and `agent` are required; every
`expect` key is optional (only the ones present are checked):

```json
{
  "name": "human-readable case name",
  "agent": "word-count",
  "input": { "path": "README.md" },
  "expect": {
    "decision_count": 1,
    "decision_type": "text.wordcount",
    "source": "word-count",
    "payload_contains": { "path": "README.md" },
    "gate": "accept",
    "result_contains": { "tool": "text.wordcount" },
    "deterministic": true
  }
}
```

`gate` is `"accept"` or `"reject"`. `result_contains` runs the real handler, so the
matching tool must be staged in `tools/`. `deterministic: true` re-runs the handler
and requires identical output (catches a non-deterministic `execute`).

## Schedule JSON (`schedules/*.json`)

One object per file. Exactly one trigger: `every_seconds` (int), `cron`
(5-field string), or `at` (ISO timestamp, one-shot):

```json
{ "id": "word-count-hourly", "agent": "word-count",
  "input": { "path": "README.md" }, "every_seconds": 3600, "enabled": true }
```

See also: [architecture.md](architecture.md) · [workflow.md](workflow.md)
