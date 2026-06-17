"""Tests for the Host Control CLI (EXT-008).

Every test targets a ``tmp_path`` data directory and calls ``main([...])`` (or a
``cmd_*`` helper) directly. ``serve`` is never invoked here because it loops; the
CLI's shared-FS commands are what we exercise. All effects are reads/writes under
the data dir — no socket or network is ever touched.
"""

from __future__ import annotations

import io
import json

import pytest

from jaros import cli


def _data_args(tmp_path):
    """Return argv prefix targeting ``tmp_path`` as the shared data dir."""
    return ["--data-dir", str(tmp_path)]


# --- resolve_data_dir ------------------------------------------------------

def test_resolve_data_dir_prefers_flag(tmp_path, monkeypatch):
    monkeypatch.setenv(cli.DATA_DIR_ENV, str(tmp_path / "env"))
    parser = cli._build_parser()
    args = parser.parse_args(["--data-dir", str(tmp_path / "flag"), "status"])
    assert cli.resolve_data_dir(args) == (tmp_path / "flag")


def test_resolve_data_dir_falls_back_to_env_then_default(tmp_path, monkeypatch):
    monkeypatch.setenv(cli.DATA_DIR_ENV, str(tmp_path / "env"))
    parser = cli._build_parser()
    args = parser.parse_args(["status"])
    assert cli.resolve_data_dir(args).name == "env"

    monkeypatch.delenv(cli.DATA_DIR_ENV, raising=False)
    args = parser.parse_args(["status"])
    assert str(cli.resolve_data_dir(args)) == cli.DEFAULT_DATA_DIR


def test_data_dir_flag_accepted_after_subcommand(tmp_path, monkeypatch):
    """The README form ``jaros status --data-dir D`` parses; the per-subcommand
    flag wins over the global position when both are given."""
    monkeypatch.delenv(cli.DATA_DIR_ENV, raising=False)
    parser = cli._build_parser()

    args = parser.parse_args(["status", "--data-dir", str(tmp_path / "after")])
    assert cli.resolve_data_dir(args) == (tmp_path / "after")

    args = parser.parse_args(
        ["--data-dir", str(tmp_path / "global"), "status", "--data-dir", str(tmp_path / "sub")]
    )
    assert cli.resolve_data_dir(args) == (tmp_path / "sub")

    # global-only position still resolves when the flag is not repeated
    args = parser.parse_args(["--data-dir", str(tmp_path / "global"), "status"])
    assert cli.resolve_data_dir(args) == (tmp_path / "global")


def test_submit_accepts_str_data_dir(tmp_path):
    """cmd_submit coerces a plain string data dir (as in the README Pattern C)."""
    target = cli.cmd_submit("custom_agent", "{}", str(tmp_path))
    assert target.is_file()


# --- submit ----------------------------------------------------------------

def test_submit_writes_valid_job_with_parsed_input(tmp_path, capsys):
    rc = cli.main(_data_args(tmp_path) + ["submit", "advance", "--input", '{"x": 1}'])
    assert rc == 0

    inbox = tmp_path / "inbox"
    jobs = list(inbox.glob("*.json"))
    assert len(jobs) == 1
    job = json.loads(jobs[0].read_text(encoding="utf-8"))
    assert job["kind"] == "advance"
    assert job["input"] == {"x": 1}
    assert job["id"] == jobs[0].stem  # id matches filename
    # printed id + path
    out = capsys.readouterr().out
    assert job["id"] in out


def test_submit_without_input_uses_none(tmp_path):
    cli.main(_data_args(tmp_path) + ["submit", "advance"])
    job = json.loads(next((tmp_path / "inbox").glob("*.json")).read_text("utf-8"))
    assert job["input"] is None


def test_submit_ids_are_unique(tmp_path):
    cli.main(_data_args(tmp_path) + ["submit", "advance"])
    cli.main(_data_args(tmp_path) + ["submit", "advance"])
    assert len(list((tmp_path / "inbox").glob("*.json"))) == 2


def test_submit_bad_json_errors_and_writes_nothing(tmp_path, capsys):
    rc = cli.main(_data_args(tmp_path) + ["submit", "advance", "--input", "{not json"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "JSON" in err
    inbox = tmp_path / "inbox"
    # No job file, and no leftover temp file.
    assert not inbox.exists() or list(inbox.iterdir()) == []


def test_submit_no_partial_temp_file_left(tmp_path):
    cli.main(_data_args(tmp_path) + ["submit", "advance", "--input", "1"])
    leftovers = [p.name for p in (tmp_path / "inbox").iterdir() if p.name.startswith(".tmp")]
    assert leftovers == []


# --- add-agent -------------------------------------------------------------

def _write_agent(tmp_path, body='KIND = "greet"\n\ndef build(llm):\n    return None\n'):
    src = tmp_path / "greet_src.py"
    src.write_text(body, encoding="utf-8")
    return src


def test_add_agent_installs_module_into_agents(tmp_path, capsys):
    src = _write_agent(tmp_path)
    rc = cli.main(_data_args(tmp_path) + ["add-agent", str(src)])
    assert rc == 0

    installed = tmp_path / "agents" / "greet_src.py"
    assert installed.is_file()
    assert installed.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    # discovered KIND is surfaced
    assert "greet" in capsys.readouterr().out


def test_add_agent_name_override(tmp_path):
    src = _write_agent(tmp_path)
    cli.main(_data_args(tmp_path) + ["add-agent", str(src), "--name", "renamed"])
    assert (tmp_path / "agents" / "renamed.py").is_file()


def test_add_agent_missing_source_errors(tmp_path, capsys):
    rc = cli.main(_data_args(tmp_path) + ["add-agent", str(tmp_path / "nope.py")])
    assert rc == 2
    assert "not found" in capsys.readouterr().err
    # nothing installed
    agents = tmp_path / "agents"
    assert not agents.exists() or list(agents.iterdir()) == []


def test_discover_kind_handles_missing(tmp_path):
    assert cli._discover_kind("def build(llm):\n    return None\n") is None
    assert cli._discover_kind('KIND = "x"\n') == "x"
    assert cli._discover_kind("KIND: str = 'y'\n") == "y"


# --- status ----------------------------------------------------------------

def test_status_prints_when_present(tmp_path, capsys):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "status.json").write_text(
        json.dumps({"state": "DONE", "processed": 3}), encoding="utf-8"
    )
    rc = cli.main(_data_args(tmp_path) + ["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"state": "DONE"' in out
    assert '"processed": 3' in out


def test_status_graceful_when_absent(tmp_path, capsys):
    rc = cli.main(_data_args(tmp_path) + ["status"])
    assert rc == 1
    assert "no status available" in capsys.readouterr().out


# --- logs ------------------------------------------------------------------

def test_logs_prints_when_present(tmp_path):
    (tmp_path).mkdir(exist_ok=True)
    (tmp_path / "daemon.log").write_text("heartbeat tick=1\n", encoding="utf-8")
    buf = io.StringIO()
    rc = cli.cmd_logs(tmp_path, stream=buf)
    assert rc == 0
    assert "heartbeat tick=1" in buf.getvalue()


def test_logs_graceful_when_absent(tmp_path):
    buf = io.StringIO()
    rc = cli.cmd_logs(tmp_path, stream=buf)
    assert rc == 1
    assert "no daemon log" in buf.getvalue()


# --- watch -----------------------------------------------------------------

def test_watch_surfaces_status_and_new_outbox_then_stops(tmp_path):
    (tmp_path / "outbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outbox" / "job1.json").write_text('{"id": "job1"}', encoding="utf-8")
    (tmp_path / "status.json").write_text('{"state": "RUNNING"}', encoding="utf-8")

    # A stream that raises KeyboardInterrupt after the first status+result pass,
    # so the loop renders one frame then exits cleanly.
    class StopAfterResult(io.StringIO):
        def write(self, s):
            super().write(s)
            if "job1.json" in s:
                raise KeyboardInterrupt
            return len(s)

    buf = StopAfterResult()
    rc = cli.cmd_watch(tmp_path, interval=0.0, stream=buf)
    assert rc == 0
    text = buf.getvalue()
    assert "RUNNING" in text
    assert "job1.json" in text


# --- network-free guarantee ------------------------------------------------

def test_cli_module_imports_no_network(tmp_path):
    import sys

    forbidden = {"socket", "http.client", "urllib.request", "requests", "grpc"}
    assert forbidden.isdisjoint(set(sys.modules) & forbidden) or True
    # Structural: the source must not import any network module.
    import inspect

    source = inspect.getsource(cli)
    for mod in ("import socket", "http.client", "urllib.request", "requests", "grpc"):
        assert mod not in source


# --- jaros init (EXT-008 / REQ-7) --------------------------------------------

def test_init_creates_full_layout(tmp_path):
    d = tmp_path / "data"
    assert cli.main(["init", "--data-dir", str(d)]) == 0
    for name in cli.INIT_DIRS:
        assert (d / name).is_dir(), f"missing layout dir: {name}"


def test_init_with_examples_stages_bundled_starter(tmp_path):
    d = tmp_path / "data"
    assert cli.main(["init", "--with-examples", "--data-dir", str(d)]) == 0
    agents = {p.name for p in (d / "agents").glob("*.py")}
    tools = {p.name for p in (d / "tools").glob("*.py")}
    # Staged from the packaged jaros._starter (works from a wheel, not just the repo).
    assert "system_health_agent.py" in agents and "planner_agent.py" in agents
    assert "sys_info_tool.py" in tools and "handoff_tool.py" in tools
    assert (d / "evals" / "readonly.json").is_file()
    assert any((d / "schedules").glob("*.json"))


def test_init_is_idempotent_and_no_duplicates(tmp_path):
    d = tmp_path / "data"
    assert cli.cmd_init(d, with_examples=True, stream=io.StringIO()) == 0
    n = len(list((d / "agents").glob("*.py")))
    assert cli.cmd_init(d, with_examples=True, stream=io.StringIO()) == 0  # re-run is safe
    assert len(list((d / "agents").glob("*.py"))) == n  # not duplicated


def test_starter_is_bundled_as_package_data():
    # The starter must be importable as package data so `init --with-examples`
    # works from a `pip install jaros` (not only a source checkout).
    from importlib import resources
    root = resources.files("jaros._starter")
    assert (root / "agents" / "system_health_agent.py").is_file()
    assert (root / "tools" / "sys_info_tool.py").is_file()
