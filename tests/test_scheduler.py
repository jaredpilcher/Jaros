"""Tests for the file-based, crash-safe scheduler (EXT-011 / REQ-1,3,5,6)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from jaros.scheduling.scheduler import Schedule, Scheduler, load_schedules


def _write(dir_: Path, name: str, body: dict) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


# --- model + loader ---------------------------------------------------------

def test_schedule_requires_exactly_one_trigger():
    with pytest.raises(ValueError):
        Schedule.from_dict({"id": "a", "agent": "advance"})  # no trigger
    with pytest.raises(ValueError):
        Schedule.from_dict({"id": "a", "agent": "advance", "every_seconds": 5, "cron": "* * * * *"})
    with pytest.raises(ValueError):
        Schedule.from_dict({"id": "", "agent": "advance", "every_seconds": 5})  # no id


def test_loader_skips_malformed(tmp_path: Path):
    sched_dir = tmp_path / "schedules"
    _write(sched_dir, "good", {"id": "g", "agent": "advance", "every_seconds": 60})
    _write(sched_dir, "bad_json", {})
    (sched_dir / "bad_json.json").write_text("{ not json", encoding="utf-8")
    _write(sched_dir, "bad_trigger", {"id": "b", "agent": "advance"})
    loaded = load_schedules(sched_dir)
    assert [s.id for s in loaded] == ["g"]


# --- interval ---------------------------------------------------------------

def test_interval_fires_once_per_window(tmp_path: Path):
    sched = Schedule(id="i", agent="advance", every_seconds=60)
    sc = Scheduler(tmp_path / "state.json")
    t0 = datetime(2026, 6, 13, 9, 0, 0)
    assert sc.due([sched], t0) == [sched]      # no prior state -> due
    sc.mark_fired(sched, t0)
    assert sc.due([sched], t0 + timedelta(seconds=30)) == []   # within window
    assert sc.due([sched], t0 + timedelta(seconds=61)) == [sched]  # window elapsed


# --- cron -------------------------------------------------------------------

def test_cron_fires_on_minute_not_twice(tmp_path: Path):
    sched = Schedule(id="c", agent="advance", cron="*/15 * * * *")
    sc = Scheduler(tmp_path / "state.json")
    on = datetime(2026, 6, 13, 9, 15, 0)
    assert sc.due([sched], on) == [sched]
    sc.mark_fired(sched, on)
    assert sc.due([sched], on + timedelta(seconds=20)) == []   # same minute
    assert sc.due([sched], datetime(2026, 6, 13, 9, 16, 0)) == []  # non-matching minute
    assert sc.due([sched], datetime(2026, 6, 13, 9, 30, 0)) == [sched]  # next match


# --- one-shot + enable ------------------------------------------------------

def test_one_shot_fires_once(tmp_path: Path):
    sched = Schedule(id="o", agent="advance", at="2026-06-13T09:00:00")
    sc = Scheduler(tmp_path / "state.json")
    assert sc.due([sched], datetime(2026, 6, 13, 8, 0, 0)) == []  # before
    when = datetime(2026, 6, 13, 9, 0, 1)
    assert sc.due([sched], when) == [sched]
    sc.mark_fired(sched, when)
    assert sc.due([sched], when + timedelta(hours=1)) == []  # never again


def test_disabled_suppresses(tmp_path: Path):
    sched = Schedule(id="d", agent="advance", every_seconds=1, enabled=False)
    sc = Scheduler(tmp_path / "state.json")
    assert sc.due([sched], datetime(2026, 6, 13, 9, 0, 0)) == []


# --- durability + prune -----------------------------------------------------

def test_state_persists_across_reload_and_prunes(tmp_path: Path):
    sched = Schedule(id="p", agent="advance", every_seconds=3600)
    state = tmp_path / "state.json"
    sc = Scheduler(state)
    t0 = datetime(2026, 6, 13, 9, 0, 0)
    sc.mark_fired(sched, t0)
    # Fresh scheduler (simulating a restart) must not immediately re-fire.
    sc2 = Scheduler(state)
    assert sc2.due([sched], t0 + timedelta(seconds=30)) == []
    # Pruning removes state for schedules no longer present.
    sc2.prune(set())
    assert json.loads(state.read_text(encoding="utf-8")) == {}


def test_describe_reports_timing(tmp_path: Path):
    sched = Schedule(id="x", agent="advance", every_seconds=60)
    sc = Scheduler(tmp_path / "state.json")
    desc = sc.describe([sched], datetime(2026, 6, 13, 9, 0, 0))
    assert desc[0]["id"] == "x"
    assert desc[0]["trigger"] == "every 60s"
    assert desc[0]["enabled"] is True
    assert desc[0]["nextRun"] is not None
