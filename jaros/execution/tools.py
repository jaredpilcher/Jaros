"""Dynamic Execution Plane custom tools loader and registry (EXT-009).

Conforms strictly to the Prime Directive:
- Agent (Reasoning Plane) proposes namespaced actions as JSON Decisions.
- Dynamic Tools (Execution Plane) execute them deterministically on the host.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path
from typing import Any, Callable

from jaros.core import Decision
from jaros.core.decision_gate import register_validator, ValidationResult
from jaros.execution import executor
from jaros.harness import Harness

logger = logging.getLogger(__name__)


# #EXT-009-REQ-3 Start
class PolicyManager:
    """Manages high-performance cached reading and runtime reloading of security policy JSON with local override support."""

    def __init__(self, path: Path) -> None:
        # Resolve to an ABSOLUTE path now (cwd is known-good at construction). A
        # relative path would break if any later code changed the process cwd,
        # silently yielding an empty policy that fails every decision closed.
        self._path = Path(path).resolve()
        self.cache: dict[str, Any] = {}
        self.last_mtime: float = 0.0
        self.last_mtimes: tuple[float, float] = (0.0, 0.0)

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, new_path: Path) -> None:
        new_path = Path(new_path).resolve()
        if new_path == self._path:
            return  # unchanged: keep the cache (callers re-assign the same path every tick)
        self._path = new_path
        self.last_mtime = 0.0
        self.last_mtimes = (0.0, 0.0)  # Clear cache only on an actual path change

    def get_policy(self) -> dict[str, Any]:
        local_path = self._path.parent / (self._path.stem + ".local" + self._path.suffix)
        main_mtime = self._path.stat().st_mtime if self._path.exists() else 0.0
        local_mtime = local_path.stat().st_mtime if local_path.exists() else 0.0
        
        current_mtimes = (main_mtime, local_mtime)
        # Reload when the files change OR whenever the cache is still empty — never
        # let a single transient empty read get latched in as the policy (that would
        # fail every decision closed with "GuestRole"). Keep retrying until a real
        # policy loads, then serve it from cache.
        if current_mtimes != getattr(self, "last_mtimes", (0.0, 0.0)) or not self.cache:
            if not self._path.exists():
                return self.cache
            try:
                # Load main policy
                with open(self._path, "r", encoding="utf-8") as f:
                    policy = json.load(f)
                
                # Load local override if exists
                if local_path.exists():
                    try:
                        with open(local_path, "r", encoding="utf-8") as f:
                            local_policy = json.load(f)
                        policy = self._deep_merge(policy, local_policy)
                    except Exception as e:
                        logger.warning("Failed to load local policy override from %s: %s", local_path, e)
                
                self.cache = policy
                self.last_mtimes = current_mtimes
                self.last_mtime = main_mtime
                logger.info("Security policy config dynamically reloaded (with layered local overrides)")
            except Exception as exc:
                logger.warning("Failed to refresh policy: %s", exc)

        if self.cache:
            return self.cache
        # Last resort: the cache is still empty (e.g. a stuck/transient state).
        # Do a direct, uncached read so the gate never fails closed with an empty
        # policy while the file is actually present and valid.
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    policy = json.load(f)
                local_path = self._path.parent / (self._path.stem + ".local" + self._path.suffix)
                if local_path.exists():
                    with open(local_path, "r", encoding="utf-8") as f:
                        policy = self._deep_merge(policy, json.load(f))
                self.cache = policy
                return policy
        except Exception as exc:
            logger.warning("Direct policy read failed: %s", exc)
        return self.cache

    def _deep_merge(self, dict1: dict, dict2: dict) -> dict:
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
# #EXT-009-REQ-3 End


# Global policy manager instance
policy_manager = PolicyManager(Path("config/permissions.json"))

# Registry tracking to ensure reloading custom tools is completely idempotent
_loaded_tools: set[str] = set()
_permission_gate_registered: bool = False


def register_permission_gate(harness: Harness, permissions_path: Path) -> None:
    """Register the global, dynamic role-based permission validation gate once."""
    global _permission_gate_registered
    if _permission_gate_registered:
        return
        
    @register_validator
    def role_permission_gate(d: Decision) -> ValidationResult:
        # Default-allow built-in system agents/kinds
        if d.source == "daemon-writer" or d.kind == "advance":
            return ValidationResult.accept(d)
            
        grants = harness._grants.get(d.source)
        if not grants:
            return ValidationResult.reject(f"Unauthorized: agent source '{d.source}' is not registered with the harness")
            
        role_name = getattr(grants, "role", "")
        if not role_name:
            return ValidationResult.reject(f"Unauthorized: agent '{d.source}' has no security role assigned")
            
        # Load permissions config
        policy = policy_manager.get_policy()
        if not policy:
            # Minimal hardcoded fallback for unit tests
            from jaros.harness.capabilities import BUILTIN_ROLES
            allowed_caps = BUILTIN_ROLES.get(role_name, ())
            # Map default action kinds
            default_map = {
                "fs.read": "FsRead",
                "fs.write": "FsWrite",
                "queue.send": "QueueSend",
                "queue.receive": "QueueReceive",
            }
            required_cap = default_map.get(d.kind)
            if required_cap:
                if any(cap.__name__ == required_cap for cap in allowed_caps):
                    return ValidationResult.accept(d)
            return ValidationResult.reject(f"Role '{role_name}' does not possess permission for action '{d.kind}'")
            
        allowed_actions = policy.get("roles", {}).get(role_name, {}).get("actions", [])
        if d.kind not in allowed_actions:
            return ValidationResult.reject(
                f"Security Gate: Role '{role_name}' is not authorized to perform custom action '{d.kind}'"
            )
            
        return ValidationResult.accept(d)

    _permission_gate_registered = True


def load_custom_tools(tools_dir: Path, harness: Harness, permissions_path: Path) -> list[str]:
    """Scan directory, dynamically import Python modules, and register custom tools.

    Idempotent: tools already imported are skipped, permitting repeated runtime scans.
    """
    loaded_names: list[str] = []
    
    # Update policy manager path dynamically to support caller's configuration
    policy_manager.path = Path(permissions_path)
    
    # 1. Register the dynamic role-based permission gate
    register_permission_gate(harness, permissions_path)
    
    if not tools_dir.exists():
        tools_dir.mkdir(parents=True, exist_ok=True)
        return loaded_names
        
    for path in sorted(tools_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
            
        abs_path = str(path.resolve())
        if abs_path in _loaded_tools:
            continue  # Already loaded and registered -> idempotent scan!
            
        try:
            module_name = f"jaros_tool_{path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find any tool class in the module
            tool_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and hasattr(obj, "NAME") and hasattr(obj, "validate") and hasattr(obj, "execute"):
                    tool_class = obj
                    break
                    
            if tool_class is None:
                logger.warning("No valid tool class found in %s", path.name)
                continue
                
            tool_instance = tool_class()
            action_name = tool_instance.NAME
            
            # 2. Register Validation Gate for this action
            def make_validator(inst: Any) -> Callable[[Decision], ValidationResult]:
                def validator(d: Decision) -> ValidationResult:
                    if d.kind == inst.NAME:
                        return inst.validate(d)
                    return ValidationResult.accept(d)
                return validator
                
            register_validator(make_validator(tool_instance))
            
            # 3. Register Executor Handler for this action
            executor.register_handler(action_name, tool_instance.execute)
            
            _loaded_tools.add(abs_path)
            loaded_names.append(action_name)
            logger.info("Dynamically registered custom execution tool: %s", action_name)
            
        except Exception as exc:
            # Fault isolation: tool loading errors must never crash the system
            logger.error("Failed to load custom tool from %s: %s", path.name, exc)
            
    return loaded_names


def reset_tools_registry() -> None:
    """Clear registered tools tracker and permission gate registration flag. Intended for tests."""
    global _permission_gate_registered
    _permission_gate_registered = False
    _loaded_tools.clear()
