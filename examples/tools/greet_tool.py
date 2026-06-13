"""Example custom Execution-Plane tool: ``demo.greet`` (EXT-009).

Drop this file into the shared-FS ``tools/`` folder; the daemon registers its
deterministic ``validate()`` into the gate and ``execute()`` into the executor at
runtime. Capability-safety is structural least-privilege via the harness-granted
handles — there is no separate authorization policy.

A custom tool is a plain class exposing ``NAME``, ``validate(decision)``, and
``execute(decision, **collaborators)``.
"""

from __future__ import annotations

from jaros.core.decision_gate import ValidationResult


class GreetTool:
    NAME = "demo.greet"

    def validate(self, decision) -> ValidationResult:
        payload = decision.payload if isinstance(decision.payload, dict) else {}
        if not payload.get("name"):
            return ValidationResult.reject("demo.greet requires a 'name'")
        return ValidationResult.accept(decision)

    def execute(self, decision, **collaborators) -> dict:
        name = decision.payload.get("name")
        return {"greeting": f"hello, {name}!", "tool": self.NAME}
