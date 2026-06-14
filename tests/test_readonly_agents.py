"""Tests for the read-only agent library (EXT-012).

Each read-only agent proposes a decision whose tool only reads — no writes, no
mutation — and many of them run concurrently under one daemon.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from jaros.core.decision_gate import reset_validators, validate_decision
from jaros.daemon import Daemon
from jaros.execution import executor
from jaros.execution.tools import load_custom_tools, reset_tools_registry

RO = Path(__file__).resolve().parents[1] / "examples" / "readonly"


def _load_agent(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stage(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.py"):
        (dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate():
    reset_validators(); executor.reset_handlers(); reset_tools_registry()
    yield
    reset_validators(); executor.reset_handlers(); reset_tools_registry()


def test_each_readonly_agent_runs_through_its_tool(tmp_path: Path):
    _stage(RO / "tools", tmp_path / "tools")
    load_custom_tools(tmp_path / "tools")
    sample = tmp_path / "sample.txt"
    sample.write_text("one two\nthree\n", encoding="utf-8")

    cases = {
        "system_health_agent.py": {},
        "disk_monitor_agent.py": {"path": str(tmp_path)},
        "inventory_agent.py": {"path": str(tmp_path)},
        "text_metrics_agent.py": {"path": str(sample)},
    }
    results = {}
    for fname, ctx in cases.items():
        mod = _load_agent(RO / "agents" / fname)
        [decision] = mod.build(object()).decide(ctx)
        gated = validate_decision(decision)
        assert gated.ok, gated.reason
        outcome = executor.apply(decision)
        assert outcome.applied, outcome.reason
        results[mod.KIND] = outcome.output

    assert results["system-health"]["system"]
    assert results["disk-monitor"]["freeBytes"] >= 0
    assert results["inventory"]["count"] >= 1
    assert results["text-metrics"]["words"] == 3


def test_many_readonly_agents_run_under_one_daemon(tmp_path: Path):
    _stage(RO / "agents", tmp_path / "agents")
    _stage(RO / "tools", tmp_path / "tools")
    sample = tmp_path / "sample.txt"
    sample.write_text("a b c\n", encoding="utf-8")

    daemon = Daemon(tmp_path)
    daemon.tick()  # load the agents + read-only tools

    jobs = [
        ("system-health", {}),
        ("disk-monitor", {"path": str(tmp_path)}),
        ("inventory", {"path": str(tmp_path)}),
        ("text-metrics", {"path": str(sample)}),
    ]
    for i, (kind, inp) in enumerate(jobs):
        (tmp_path / "inbox" / f"j{i}.json").write_text(
            json.dumps({"id": f"j{i}", "kind": kind, "input": inp}), encoding="utf-8"
        )

    for _ in range(60):
        daemon.tick()
        if daemon.processed >= 4:
            break

    assert daemon.processed >= 4
    assert daemon.failed == 0
    kinds = {
        json.loads(o.read_text(encoding="utf-8"))["kind"]
        for o in (tmp_path / "outbox").glob("*.json")
    }
    assert {"system-health", "disk-monitor", "inventory", "text-metrics"} <= kinds
