"""Tests for the decision validation gate (EXT-001 / REQ-3, REQ-5)."""

from __future__ import annotations

import pytest

from jaros.core import create_decision
from jaros.core.decision import Decision
from jaros.core.decision_gate import (
    ValidationResult,
    register_validator,
    reset_validators,
    validate_decision,
)


@pytest.fixture(autouse=True)
def _reset_gate():
    reset_validators()
    yield
    reset_validators()


def _good() -> Decision:
    return create_decision(id="d1", source="agent-a", kind="noop", payload={"n": 1})


def test_validate_accepts_good_decision():
    result = validate_decision(_good())
    assert result.ok is True
    assert result.value == _good()
    assert result.reason is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": "", "source": "a", "kind": "k"},
        {"id": "d", "source": "", "kind": "k"},
        {"id": "d", "source": "a", "kind": ""},
    ],
)
def test_validate_rejects_malformed_fields(kwargs):
    d = Decision(payload={"ok": True}, **kwargs)
    result = validate_decision(d)
    assert result.ok is False
    assert result.value is None
    assert result.reason


def test_validate_rejects_non_serializable_payload():
    # Bypass create_decision to plant a bad payload directly on the frozen type.
    d = Decision(id="d", source="a", kind="k", payload={"f": lambda: 1})  # type: ignore[dict-item]
    result = validate_decision(d)
    assert result.ok is False
    assert "serializable" in (result.reason or "")


def test_registered_validator_can_reject():
    def no_forbidden(d: Decision) -> ValidationResult:
        if isinstance(d.payload, dict) and d.payload.get("forbidden"):
            return ValidationResult.reject("payload is forbidden")
        return ValidationResult.accept(d)

    register_validator(no_forbidden)
    bad = create_decision(id="d", source="a", kind="k", payload={"forbidden": True})
    result = validate_decision(bad)
    assert result.ok is False
    assert result.reason == "payload is forbidden"
    # A non-forbidden decision still passes through the same validator.
    assert validate_decision(_good()).ok is True


def test_structural_check_runs_before_registered_validators():
    calls: list[str] = []

    def custom(d: Decision) -> ValidationResult:
        calls.append("custom")
        return ValidationResult.accept(d)

    register_validator(custom)
    # Malformed (empty id) must be rejected by structural check; custom never runs.
    bad = Decision(id="", source="a", kind="k", payload={})
    result = validate_decision(bad)
    assert result.ok is False
    assert calls == []  # short-circuited before the registered validator


def test_registered_validators_run_in_registration_order():
    order: list[str] = []

    def first(d: Decision) -> ValidationResult:
        order.append("first")
        return ValidationResult.accept(d)

    def second(d: Decision) -> ValidationResult:
        order.append("second")
        return ValidationResult.reject("stop at second")

    def third(d: Decision) -> ValidationResult:  # should never run
        order.append("third")
        return ValidationResult.accept(d)

    register_validator(first)
    register_validator(second)
    register_validator(third)
    result = validate_decision(_good())
    assert result.ok is False and result.reason == "stop at second"
    assert order == ["first", "second"]  # third short-circuited
