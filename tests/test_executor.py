"""Tests for the executor and pluggable handlers (EXT-001 / REQ-4, REQ-6, REQ-7)."""

from __future__ import annotations

import pytest

from jaros.core import create_decision
from jaros.core.decision import Decision
from jaros.core.decision_gate import (
    register_validator,
    reset_validators,
    ValidationResult,
)
from jaros.execution.executor import (
    apply,
    register_handler,
    reset_handlers,
)


@pytest.fixture(autouse=True)
def _reset_registries():
    reset_handlers()
    reset_validators()
    yield
    reset_handlers()
    reset_validators()


def test_handler_runs_for_its_kind_with_collaborators():
    seen: dict[str, object] = {}

    def handle(d: Decision, *, store=None):
        seen["id"] = d.id
        seen["store"] = store
        return "done"

    register_handler("write", handle)
    d = create_decision(id="d1", source="a", kind="write", payload={"k": "v"})
    result = apply(d, store="STATE")
    assert result.applied is True
    assert result.output == "done"
    assert seen == {"id": "d1", "store": "STATE"}


def test_unknown_kind_refused_with_no_effect():
    ran: list[str] = []
    register_handler("write", lambda d, **_: ran.append("write"))
    d = create_decision(id="d1", source="a", kind="mystery", payload={})
    result = apply(d)
    assert result.applied is False
    assert "mystery" in (result.reason or "")
    assert ran == []  # no handler ran, no side effect


def test_gate_rejected_decision_refused_and_no_handler_runs():
    ran: list[str] = []
    register_handler("write", lambda d, **_: ran.append("write"))
    # Empty id -> structural rejection by the gate.
    d = Decision(id="", source="a", kind="write", payload={})
    result = apply(d)
    assert result.applied is False
    assert result.reason
    assert ran == []


def test_custom_validator_rejection_blocks_handler():
    ran: list[str] = []
    register_handler("write", lambda d, **_: ran.append("write"))
    register_validator(
        lambda d: ValidationResult.reject("nope")
    )
    d = create_decision(id="d1", source="a", kind="write", payload={})
    result = apply(d)
    assert result.applied is False
    assert result.reason == "nope"
    assert ran == []


# --- EXT-001 / REQ-7: the accepted decision is surfaced + recordable ----------

def test_accepted_decision_surfaced_on_result():
    register_handler("write", lambda d, **_: "ok")
    d = create_decision(id="d1", source="a", kind="write", payload={"k": "v"})
    result = apply(d)
    assert result.applied is True
    assert result.accepted is not None
    assert result.accepted.id == "d1"


def test_on_accept_fires_before_handler_and_only_when_accepted():
    order: list[str] = []
    register_handler("write", lambda d, **_: order.append("handler"))

    d = create_decision(id="d1", source="a", kind="write", payload={})
    apply(d, on_accept=lambda x: order.append(f"record:{x.id}"))
    # Recorded before the handler ran (record before effects are observable).
    assert order == ["record:d1", "handler"]

    # A gate-rejected decision must NOT fire on_accept (no effect, nothing to record).
    order.clear()
    rejected = Decision(id="", source="a", kind="write", payload={})
    apply(rejected, on_accept=lambda x: order.append("record"))
    assert order == []


def test_apply_is_deterministic_over_identical_decisions():
    outputs: list[object] = []
    register_handler("write", lambda d, **_: d.payload)
    d = create_decision(id="d1", source="a", kind="write", payload={"n": 1})
    outputs.append(apply(d).output)
    outputs.append(apply(d).output)
    assert outputs[0] == outputs[1]
