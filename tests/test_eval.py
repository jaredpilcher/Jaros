"""Tests for the agent evaluation framework (EXT-013)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jaros.core.decision import create_decision
from jaros.core.decision_gate import reset_validators
from jaros.eval import EvalCase, load_cases, run_case, run_suite
from jaros.execution import executor
from jaros.execution.tools import load_custom_tools, reset_tools_registry
from jaros.llm import LlmConfig, create_llm_client
from jaros.registry import AgentRegistry, load_plugins

RO = Path(__file__).resolve().parents[1] / "examples" / "readonly"


@pytest.fixture(autouse=True)
def _isolate():
    reset_validators(); executor.reset_handlers(); reset_tools_registry()
    yield
    reset_validators(); executor.reset_handlers(); reset_tools_registry()


class _FakeRegistry:
    """Minimal registry: maps a kind to a boundary that emits a fixed decision."""

    def __init__(self, kind: str, decision):
        self._kind = kind
        self._decision = decision

    def resolve(self, kind):
        if kind != self._kind:
            raise KeyError(kind)
        decision = self._decision
        class _B:
            def decide(self, ctx):
                return [decision]
        return _B()


def _decision(kind="demo.act", source="agent", payload=None):
    return create_decision(id="d1", source=source, kind=kind, payload=payload or {})


def test_decision_level_checks_pass():
    reg = _FakeRegistry("k", _decision(kind="demo.act", source="agent", payload={"x": 1}))
    case = EvalCase.from_dict({
        "name": "ok", "kind": "k",
        "expect": {"decision_count": 1, "decision_kind": "demo.act", "source": "agent",
                   "payload_contains": {"x": 1}, "gate": "accept"},
    })
    res = run_case(case, reg, execute=False)
    assert res.passed, [c for c in res.checks if not c.ok]


def test_wrong_kind_fails():
    reg = _FakeRegistry("k", _decision(kind="demo.act"))
    case = EvalCase.from_dict({"name": "bad", "kind": "k", "expect": {"decision_kind": "other"}})
    res = run_case(case, reg, execute=False)
    assert not res.passed
    assert any(c.name == "decision_kind" and not c.ok for c in res.checks)


def test_unresolvable_kind_is_error():
    reg = _FakeRegistry("k", _decision())
    case = EvalCase.from_dict({"name": "missing", "kind": "nope", "expect": {"decision_count": 1}})
    res = run_case(case, reg, execute=False)
    assert not res.passed and res.error


def test_result_contains_executes_handler():
    executor.register_handler("demo.act", lambda d, **_: {"tool": "demo.act", "ok": True})
    reg = _FakeRegistry("k", _decision(kind="demo.act"))
    case = EvalCase.from_dict({"name": "exec", "kind": "k",
                               "expect": {"result_contains": {"tool": "demo.act", "ok": True}}})
    res = run_case(case, reg, execute=True)
    assert res.passed, [c for c in res.checks if not c.ok]


def test_load_cases_skips_malformed(tmp_path: Path):
    (tmp_path / "evals").mkdir()
    (tmp_path / "evals" / "good.json").write_text(
        '{"name":"g","kind":"k","expect":{"decision_count":1}}', encoding="utf-8")
    (tmp_path / "evals" / "list.json").write_text(
        '[{"name":"a","kind":"k"},{"name":"b","kind":"k"}]', encoding="utf-8")
    (tmp_path / "evals" / "bad.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "evals" / "noname.json").write_text('{"kind":"k"}', encoding="utf-8")
    names = sorted(c.name for c in load_cases(tmp_path / "evals"))
    assert names == ["a", "b", "g"]


def test_readonly_eval_suite_all_pass():
    """The shipped read-only eval cases pass against the read-only agents."""
    llm = create_llm_client(LlmConfig(provider="default"))
    reg = AgentRegistry()
    load_plugins(reg, RO / "plugins", llm)
    load_custom_tools(RO / "tools")
    cases = load_cases(RO / "evals")
    assert len(cases) >= 4
    report = run_suite(cases, reg)
    assert report.ok, report.to_dict()
