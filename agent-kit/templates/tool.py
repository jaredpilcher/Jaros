"""TEMPLATE — a Jaros custom tool.

A tool is the deterministic Execution-Plane side of a decision. The daemon
dispatches a decision to the tool whose `NAME` equals the decision's `kind`,
running `validate()` (at the gate) and then `execute()` (the actual effect).

Keep `execute()` DETERMINISTIC: the same decision must always produce the same
output (no clock, no RNG, no network) — that is what lets a run replay to
byte-identical state. A read-only tool (no writes) is the safest kind.

To use this template:
  1. Copy it to `<data-dir>/tools/word_count_tool.py` (rename as you like).
  2. Set `NAME` to the decision `kind` your agent emits.
  3. Implement `validate()` (cheap structural checks) and `execute()` (the effect).
The daemon imports every `*.py` in `tools/` on its next tick — no restart.

Contract:
  - a class with a `NAME: str` attribute
  - `validate(self, decision) -> ValidationResult`
  - `execute(self, decision, **collaborators) -> dict`
"""

from __future__ import annotations

from pathlib import Path

from jaros.core.decision_gate import ValidationResult


class WordCountTool:
    NAME = "text.wordcount"  # MUST equal the decision kind the agent emits

    def validate(self, decision) -> ValidationResult:
        # Cheap, pure structural checks. Reject early with a clear reason.
        if not isinstance(decision.payload, dict) or not decision.payload.get("path"):
            return ValidationResult.reject("text.wordcount requires a 'path' in the payload")
        return ValidationResult.accept(decision)

    def execute(self, decision, **collaborators) -> dict:
        # Deterministic effect: read the file and count words. Returns inert data.
        path = decision.payload["path"]
        try:
            words = len(Path(path).read_text(encoding="utf-8").split())
        except OSError:
            words = 0
        return {"tool": self.NAME, "path": path, "words": words}
