"""Tests for the runtime agent registry + agent loading (EXT-007 / REQ-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jaros.core import Decision, ReasoningBoundary
from jaros.llm import LlmConfig, create_llm_client
from jaros.registry import (
    AgentRegistry,
    load_agents,
    register_builtins,
)


def _llm():
    return create_llm_client(LlmConfig(provider="default"))


def test_register_resolve_and_kinds():
    reg = AgentRegistry()
    assert reg.names() == []
    assert not reg.has("noop")

    class _B:
        def decide(self, context: object) -> list[Decision]:
            return []

    reg.register("noop", lambda: _B())
    assert reg.has("noop")
    assert reg.names() == ["noop"]
    boundary = reg.resolve("noop")
    assert isinstance(boundary, ReasoningBoundary)
    assert boundary.decide(None) == []


def test_resolve_unknown_kind_raises():
    reg = AgentRegistry()
    with pytest.raises(KeyError):
        reg.resolve("missing")


def test_register_rejects_empty_kind():
    reg = AgentRegistry()
    with pytest.raises(ValueError):
        reg.register("", lambda: None)


def test_builtin_advance_kind_emits_advance_decision():
    reg = AgentRegistry()
    register_builtins(reg, _llm())
    assert "advance" in reg.names()

    boundary = reg.resolve("advance")
    decisions = boundary.decide({"task": "demo"})
    assert len(decisions) == 1
    d = decisions[0]
    assert isinstance(d, Decision)
    assert d.type == "advance"
    assert d.payload["events"] == ["start", "complete"]
    assert "note" in d.payload


def _write_agent(agents_dir: Path, name: str, agent: str) -> None:
    (agents_dir / f"{name}.py").write_text(
        "from jaros.core import create_decision\n"
        "import uuid\n"
        f"NAME = {agent!r}\n"
        "def build(llm):\n"
        "    class _B:\n"
        "        def decide(self, context):\n"
        "            return [create_decision(id='p-'+uuid.uuid4().hex,\n"
        f"                source={agent!r}, type='advance',\n"
        "                payload={'events': ['start', 'complete'], 'note': 'agent'})]\n"
        "    return _B()\n",
        encoding="utf-8",
    )


def test_load_agents_registers_dropped_module(tmp_path: Path):
    agents = tmp_path / "agents"
    agents.mkdir()
    reg = AgentRegistry()
    llm = _llm()

    # Nothing yet.
    assert load_agents(reg, agents, llm) == []
    assert not reg.has("greeter")

    # Drop an agent and rescan -> it becomes resolvable.
    _write_agent(agents, "greeter_agent", "greeter")
    newly = load_agents(reg, agents, llm)
    assert newly == ["greeter"]
    assert reg.has("greeter")
    boundary = reg.resolve("greeter")
    decisions = boundary.decide(None)
    assert decisions[0].source == "greeter"


def test_load_agents_is_idempotent(tmp_path: Path):
    agents = tmp_path / "agents"
    agents.mkdir()
    reg = AgentRegistry()
    llm = _llm()
    _write_agent(agents, "greeter_agent", "greeter")

    assert load_agents(reg, agents, llm) == ["greeter"]
    # Re-scan: already-loaded file is skipped, nothing newly registered.
    assert load_agents(reg, agents, llm) == []
    assert reg.names() == ["greeter"]


def test_load_agents_ignores_malformed_module(tmp_path: Path):
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "broken.py").write_text("NAME = 'broken'\n", encoding="utf-8")
    reg = AgentRegistry()
    # No build() -> not registered, but recorded so it is not retried forever.
    assert load_agents(reg, agents, _llm()) == []
    assert not reg.has("broken")
