"""Dynamic Execution Plane custom tools loader and registry (EXT-009).

Conforms strictly to the Prime Directive:
- Agent (Reasoning Plane) proposes namespaced actions as JSON Decisions.
- Dynamic Tools (Execution Plane) execute them deterministically on the host.

Each tool contributes its own deterministic ``validate()`` to the gate and its
``execute()`` handler to the executor. Capability-safety is structural
least-privilege via harness-granted handles (EXT-005); Jaros enforces no
authorization policy of its own (the former role-based permission enforcer was
removed — see EXT-009 / REQ-3, deprecated).
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable

from jaros.core import Decision
from jaros.core.decision_gate import register_validator, ValidationResult
from jaros.execution import executor

logger = logging.getLogger(__name__)


# Registry tracking to ensure reloading custom tools is completely idempotent
_loaded_tools: set[str] = set()


def load_custom_tools(tools_dir: Path) -> list[str]:
    """Scan directory, dynamically import Python modules, and register custom tools.

    Idempotent: tools already imported are skipped, permitting repeated runtime scans.
    """
    loaded_names: list[str] = []

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

            # 1. Register Validation Gate for this action
            def make_validator(inst: Any) -> Callable[[Decision], ValidationResult]:
                def validator(d: Decision) -> ValidationResult:
                    if d.kind == inst.NAME:
                        return inst.validate(d)
                    return ValidationResult.accept(d)
                return validator

            register_validator(make_validator(tool_instance))

            # 2. Register Executor Handler for this action
            executor.register_handler(action_name, tool_instance.execute)

            _loaded_tools.add(abs_path)
            loaded_names.append(action_name)
            logger.info("Dynamically registered custom execution tool: %s", action_name)

        except Exception as exc:
            # Fault isolation: tool loading errors must never crash the system
            logger.error("Failed to load custom tool from %s: %s", path.name, exc)

    return loaded_names


def reset_tools_registry() -> None:
    """Clear the registered-tools tracker. Intended for tests."""
    _loaded_tools.clear()
