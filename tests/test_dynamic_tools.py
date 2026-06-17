"""Tests for dynamic custom Execution Plane tools (EXT-009).

Covers dynamic discovery/registration of a custom tool and that its own
deterministic ``validate()``/``execute()`` are wired into the gate and executor.
The former role-based permission enforcer (EXT-009 / REQ-3) is deprecated and
removed; capability-safety is structural least-privilege via harness handles
(EXT-005), not an authorization policy.
"""

from __future__ import annotations

import pytest

from jaros.comms.fs import SharedFileSystem
from jaros.core.decision import create_decision
from jaros.core.decision_gate import validate_decision, reset_validators
from jaros.execution import executor
from jaros.execution.tools import load_custom_tools, reset_tools_registry


# Define a custom tool mockup source code
TOOL_SOURCE = """
from jaros.core.decision_gate import ValidationResult

class AccountReaderTool:
    NAME = "db.accounts.read"

    def validate(self, decision) -> ValidationResult:
        payload = decision.payload if isinstance(decision.payload, dict) else {}
        account_id = payload.get("account_id")
        if not account_id:
            return ValidationResult.reject("Missing account_id parameter")
        return ValidationResult.accept(decision)

    def execute(self, decision, **collaborators) -> dict:
        payload = decision.payload
        account_id = payload.get("account_id")
        return {"account_id": account_id, "status": "active", "balance": 1500.0}
"""


@pytest.fixture(autouse=True)
def cleanup():
    # Make sure we clean up registered validators and handlers for test isolation
    reset_validators()
    executor.reset_handlers()
    reset_tools_registry()
    yield
    reset_validators()
    executor.reset_handlers()
    reset_tools_registry()


def test_dynamic_tool_loads_and_registers(tmp_path):
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()

    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)

    # Drop a custom tool into the tools directory and load it.
    (tools_dir / "account_reader.py").write_text(TOOL_SOURCE, encoding="utf-8")
    loaded_tools = load_custom_tools(tools_dir)
    assert "db.accounts.read" in loaded_tools


def test_custom_tool_validate_rejects_bad_payload(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "account_reader.py").write_text(TOOL_SOURCE, encoding="utf-8")
    load_custom_tools(tools_dir)

    # The tool's own validate() runs in the gate: missing account_id -> rejected.
    bad = create_decision(
        id="dec-bad-1",
        source="auditor",
        type="db.accounts.read",
        payload={},
    )
    gated_bad = validate_decision(bad)
    assert not gated_bad.ok
    assert "Missing account_id" in gated_bad.reason


def test_custom_tool_validate_and_execute(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "account_reader.py").write_text(TOOL_SOURCE, encoding="utf-8")
    load_custom_tools(tools_dir)

    ok = create_decision(
        id="dec-ok-1",
        source="auditor",
        type="db.accounts.read",
        payload={"account_id": "acc_123"},
    )
    gated_ok = validate_decision(ok)
    assert gated_ok.ok

    outcome = executor.apply(ok)
    assert outcome.applied
    assert outcome.output["account_id"] == "acc_123"
    assert outcome.output["balance"] == 1500.0


def test_loader_is_idempotent(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "account_reader.py").write_text(TOOL_SOURCE, encoding="utf-8")

    first = load_custom_tools(tools_dir)
    second = load_custom_tools(tools_dir)
    assert first == ["db.accounts.read"]
    assert second == []  # already loaded -> not re-registered
