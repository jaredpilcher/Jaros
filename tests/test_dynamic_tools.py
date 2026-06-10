"""Tests for dynamic custom execution plane tools and role-based permissions (EXT-009)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from jaros.comms.fs import SharedFileSystem
from jaros.comms.queue import Queue
from jaros.core.decision import create_decision
from jaros.core.decision_gate import validate_decision, reset_validators
from jaros.execution import executor
from jaros.harness.capabilities import GrantSpec
from jaros.harness.harness import Harness
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


def test_dynamic_tool_loader_and_permission_checks(tmp_path):
    # Set up directories
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    
    # Drop custom tool into tools directory
    tool_file = tools_dir / "account_reader.py"
    tool_file.write_text(TOOL_SOURCE, encoding="utf-8")
    
    # Setup permissions configuration
    permissions_path = tmp_path / "permissions.json"
    permissions_policy = {
        "roles": {
            "AccountAuditor": {
                "description": "Allowed to read account records",
                "actions": ["db.accounts.read"]
            },
            "GuestRole": {
                "description": "Guest only",
                "actions": ["fs.read"]
            }
        }
    }
    permissions_path.write_text(json.dumps(permissions_policy), encoding="utf-8")
    
    # Initialize Harness and load tools
    harness = Harness()
    loaded_tools = load_custom_tools(tools_dir, harness, permissions_path)
    
    assert "db.accounts.read" in loaded_tools
    
    # 1. Spawn authorized and unauthorized agents
    harness.spawn("auditor", GrantSpec(role="AccountAuditor", fs=fs))
    harness.spawn("guest", GrantSpec(role="GuestRole", fs=fs))
    
    # 2. Test unauthorized access
    unauth_decision = create_decision(
        id="dec-unauth-1",
        source="guest",
        kind="db.accounts.read",
        payload={"account_id": "acc_123"}
    )
    
    gate_unauth = validate_decision(unauth_decision)
    assert not gate_unauth.ok
    assert "is not authorized" in gate_unauth.reason
    
    # 3. Test authorized access but with missing/invalid parameters (custom gate fails)
    bad_param_decision = create_decision(
        id="dec-bad-1",
        source="auditor",
        kind="db.accounts.read",
        payload={}  # missing account_id!
    )
    
    gate_bad = validate_decision(bad_param_decision)
    assert not gate_bad.ok
    assert "Missing account_id" in gate_bad.reason
    
    # 4. Test fully authorized and valid call (should pass gate and execute successfully)
    valid_decision = create_decision(
        id="dec-ok-1",
        source="auditor",
        kind="db.accounts.read",
        payload={"account_id": "acc_123"}
    )
    
    gate_ok = validate_decision(valid_decision)
    assert gate_ok.ok
    
    execution_outcome = executor.apply(valid_decision)
    assert execution_outcome.applied
    assert execution_outcome.output["account_id"] == "acc_123"
    assert execution_outcome.output["balance"] == 1500.0


def test_policy_manager_local_override(tmp_path: Path):
    from jaros.execution.tools import PolicyManager
    
    main_path = tmp_path / "permissions.json"
    local_path = tmp_path / "permissions.local.json"
    
    main_config = {
        "roles": {
            "DefaultRole": {
                "description": "Default role description",
                "actions": ["fs.read"]
            }
        },
        "assignments": {
            "advance": "AdminRole"
        }
    }
    
    local_config = {
        "roles": {
            "DefaultRole": {
                "actions": ["fs.read", "db.query"]
            },
            "LocalRole": {
                "description": "Only in local config",
                "actions": ["fs.write"]
            }
        },
        "assignments": {
            "custom": "LocalRole"
        }
    }
    
    main_path.write_text(json.dumps(main_config), encoding="utf-8")
    local_path.write_text(json.dumps(local_config), encoding="utf-8")
    
    pm = PolicyManager(main_path)
    policy = pm.get_policy()
    
    # Assert merged roles
    assert "DefaultRole" in policy["roles"]
    assert "LocalRole" in policy["roles"]
    assert policy["roles"]["DefaultRole"]["actions"] == ["fs.read", "db.query"]
    assert policy["roles"]["DefaultRole"]["description"] == "Default role description"
    assert policy["roles"]["LocalRole"]["actions"] == ["fs.write"]
    
    # Assert merged assignments
    assert policy["assignments"]["advance"] == "AdminRole"
    assert policy["assignments"]["custom"] == "LocalRole"
