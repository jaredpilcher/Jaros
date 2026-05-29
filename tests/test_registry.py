"""Tests for the runtime agent registry + plugin loading (EXT-007 / REQ-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jaros.core import Decision, ReasoningBoundary
from jaros.llm import LlmConfig, create_llm_client
from jaros.registry import (
    AgentRegistry,
    load_plugins,
    register_builtins,
)


def _llm():
    return create_llm_client(LlmConfig(provider="default"))


def test_register_resolve_and_kinds():
    reg = AgentRegistry()
    assert reg.kinds() == []
    assert not reg.has("noop")

    class _B:
        def decide(self, context: object) -> list[Decision]:
            return []

    reg.register("noop", lambda: _B())
    assert reg.has("noop")
    assert reg.kinds() == ["noop"]
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
    assert "advance" in reg.kinds()

    boundary = reg.resolve("advance")
    decisions = boundary.decide({"task": "demo"})
    assert len(decisions) == 1
    d = decisions[0]
    assert isinstance(d, Decision)
    assert d.kind == "advance"
    assert d.payload["events"] == ["start", "complete"]
    assert "note" in d.payload


def _write_plugin(plugins_dir: Path, name: str, kind: str) -> None:
    (plugins_dir / f"{name}.py").write_text(
        "from jaros.core import create_decision\n"
        "import uuid\n"
        f"KIND = {kind!r}\n"
        "def build(llm):\n"
        "    class _B:\n"
        "        def decide(self, context):\n"
        "            return [create_decision(id='p-'+uuid.uuid4().hex,\n"
        f"                source={kind!r}, kind='advance',\n"
        "                payload={'events': ['start', 'complete'], 'note': 'plugin'})]\n"
        "    return _B()\n",
        encoding="utf-8",
    )


def test_load_plugins_registers_dropped_module(tmp_path: Path):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    reg = AgentRegistry()
    llm = _llm()

    # Nothing yet.
    assert load_plugins(reg, plugins, llm) == []
    assert not reg.has("greeter")

    # Drop a plugin and rescan -> it becomes resolvable.
    _write_plugin(plugins, "greeter_plugin", "greeter")
    newly = load_plugins(reg, plugins, llm)
    assert newly == ["greeter"]
    assert reg.has("greeter")
    boundary = reg.resolve("greeter")
    decisions = boundary.decide(None)
    assert decisions[0].source == "greeter"


def test_load_plugins_is_idempotent(tmp_path: Path):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    reg = AgentRegistry()
    llm = _llm()
    _write_plugin(plugins, "greeter_plugin", "greeter")

    assert load_plugins(reg, plugins, llm) == ["greeter"]
    # Re-scan: already-loaded file is skipped, nothing newly registered.
    assert load_plugins(reg, plugins, llm) == []
    assert reg.kinds() == ["greeter"]


def test_load_plugins_ignores_malformed_module(tmp_path: Path):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "broken.py").write_text("KIND = 'broken'\n", encoding="utf-8")
    reg = AgentRegistry()
    # No build() -> not registered, but recorded so it is not retried forever.
    assert load_plugins(reg, plugins, _llm()) == []
    assert not reg.has("broken")
