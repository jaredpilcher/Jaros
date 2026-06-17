---
name: jaros-write-eval
description: Use when writing a Jaros eval — a declarative, reproducible test that an agent emits the expected decision (and optionally the expected executed result). Covers the eval JSON shape and running the suite.
---

# Write a Jaros eval

An eval is a reproducible test of an agent: given an `input`, the agent's
`decide()` emits a decision, and the case asserts properties of that decision and
(optionally) of the deterministic execution result. No model-grading — results
reproduce exactly, so the same suite gates CI.

## Shape

A file in `evals/` is one case object or a list of them. `name` and `agent` are
required; every `expect` key is optional and only checked when present.

| `expect` key | Checks |
| --- | --- |
| `decision_count` | number of decisions emitted |
| `decision_type` | first decision's `type` |
| `source` | first decision's `source` |
| `payload_contains` | subset match on the payload |
| `gate` | `"accept"` or `"reject"` at the validation gate |
| `result_contains` | subset match on the executed tool result (tool must be staged) |
| `deterministic` | re-runs the handler; requires identical output |

## Steps

1. Copy [`templates/eval.json`](../../templates/eval.json) into `<data-dir>/evals/`.
2. Set `name`, `agent` (the agent under test), and `input`.
3. Add the `expect` keys you care about. Use `gate: "accept"` to assert the
   decision is valid; add `result_contains` (with the tool staged in `tools/`) to
   assert the executed output.

## Worked example

```json
{
  "name": "word-count emits an accepted text.wordcount decision",
  "agent": "word-count",
  "input": { "path": "README.md" },
  "expect": {
    "decision_type": "text.wordcount",
    "payload_contains": { "path": "README.md" },
    "gate": "accept",
    "result_contains": { "tool": "text.wordcount" }
  }
}
```

## Verify

```bash
jaros eval      # prints [PASS]/[FAIL] per case; exit 0 iff all pass
```

`result_contains` runs the real handler, so stage the matching tool first. See
[reference/public-api.md](../../reference/public-api.md).
