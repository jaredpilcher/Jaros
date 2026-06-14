"""Deterministic agent evaluation (EXT-013).

An eval is a reproducible test of an agent: given an input context, the agent's
``decide()`` emits inert ``Decision`` data, and the case asserts properties of
that decision (and, optionally, of the deterministic execution result). Because
reasoning emits only data and execution is deterministic, evals reproduce exactly
— the same property the Prime Directive gives the runtime.

This module imports only ``jaros`` + the standard library; no network, no model
training, no infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jaros.core.decision_gate import validate_decision
from jaros.execution import executor


# #EXT-013-REQ-1 Start
@dataclass(frozen=True)
class Expect:
    """Declarative, all-optional assertions about an agent's output."""

    decision_count: int | None = None
    decision_kind: str | None = None
    source: str | None = None
    payload_contains: dict[str, Any] | None = None
    gate: str | None = None  # "accept" | "reject"
    result_contains: dict[str, Any] | None = None
    deterministic: bool | None = None  # re-run the handler and require identical output


@dataclass(frozen=True)
class EvalCase:
    """One declarative agent evaluation case."""

    name: str
    kind: str
    input: Any = None
    expect: Expect = field(default_factory=Expect)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalCase":
        if not data.get("name") or not data.get("kind"):
            raise ValueError("eval case requires 'name' and 'kind'")
        exp = data.get("expect", {}) or {}
        if not isinstance(exp, dict):
            raise ValueError(f"eval case {data['name']!r} 'expect' must be an object")
        return cls(
            name=str(data["name"]),
            kind=str(data["kind"]),
            input=data.get("input"),
            expect=Expect(
                decision_count=exp.get("decision_count"),
                decision_kind=exp.get("decision_kind"),
                source=exp.get("source"),
                payload_contains=exp.get("payload_contains"),
                gate=exp.get("gate"),
                result_contains=exp.get("result_contains"),
                deterministic=exp.get("deterministic"),
            ),
        )


@dataclass
class EvalCheck:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class EvalResult:
    case: str
    passed: bool
    checks: list[EvalCheck] = field(default_factory=list)
    error: str | None = None
# #EXT-013-REQ-1 End


# #EXT-013-REQ-2 Start
def _is_subset(expected: dict[str, Any], actual: Any) -> bool:
    """True iff every key/value in ``expected`` matches in ``actual`` (a dict)."""
    if not isinstance(actual, dict):
        return False
    return all(actual.get(k) == v for k, v in expected.items())


def run_case(case: EvalCase, registry: Any, *, execute: bool = True) -> EvalResult:
    """Run one eval case against a resolved agent and report each check.

    ``registry`` resolves ``case.kind`` to a fresh ``ReasoningBoundary``. The
    executor handlers required for ``result_contains`` checks must already be
    registered by the caller (e.g. via ``load_custom_tools``).
    """
    result = EvalResult(case=case.name, passed=False)
    try:
        boundary = registry.resolve(case.kind)
        decisions = boundary.decide(case.input)
    except Exception as exc:  # resolution / reasoning failure is a failed eval
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    exp = case.expect
    checks = result.checks

    if exp.decision_count is not None:
        checks.append(EvalCheck(
            "decision_count", len(decisions) == exp.decision_count,
            f"got {len(decisions)}, want {exp.decision_count}",
        ))

    first = decisions[0] if decisions else None
    if first is None and any(
        v is not None for v in (exp.decision_kind, exp.source, exp.payload_contains, exp.gate, exp.result_contains)
    ):
        checks.append(EvalCheck("emits_decision", False, "agent emitted no decisions"))
        result.passed = all(c.ok for c in checks)
        return result

    if exp.decision_kind is not None and first is not None:
        checks.append(EvalCheck("decision_kind", first.kind == exp.decision_kind, f"got {first.kind!r}"))
    if exp.source is not None and first is not None:
        checks.append(EvalCheck("source", first.source == exp.source, f"got {first.source!r}"))
    if exp.payload_contains is not None and first is not None:
        checks.append(EvalCheck("payload_contains", _is_subset(exp.payload_contains, first.payload), f"payload={first.payload!r}"))

    if exp.gate is not None and first is not None:
        gated = validate_decision(first)
        want_accept = exp.gate == "accept"
        checks.append(EvalCheck("gate", gated.ok == want_accept, f"gate {'accepted' if gated.ok else 'rejected'}: {gated.reason or ''}"))

    if exp.result_contains is not None and first is not None:
        outcome = executor.apply(first)
        if not outcome.applied:
            checks.append(EvalCheck("result_contains", False, f"not applied: {outcome.reason}"))
        else:
            checks.append(EvalCheck("result_contains", _is_subset(exp.result_contains, outcome.output), f"output={outcome.output!r}"))

    if exp.deterministic and first is not None:
        # Re-run the handler and require identical output — catches a
        # non-deterministic handler (clock/RNG/external I/O) in the eval/CI itself.
        from jaros.execution import digest
        a = executor.apply(first)
        b = executor.apply(first)
        same = a.applied and b.applied and digest(a.output) == digest(b.output)
        checks.append(EvalCheck("deterministic", same, "handler output differs across runs" if not same else ""))

    result.passed = bool(checks) and all(c.ok for c in checks)
    return result
# #EXT-013-REQ-2 End
