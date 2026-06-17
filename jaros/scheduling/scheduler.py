"""File-based, crash-safe agent scheduler (EXT-011).

Operators declare schedules as JSON files in the shared ``schedules/`` folder.
The :class:`Scheduler` decides which are due given the current time and durable
last-fire state, so recurring/one-shot runs survive a restart without
double-firing or skipping. It imports only the standard library — no external
cron, broker, or service.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from jaros.scheduling.cron import CronError, cron_due

logger = logging.getLogger(__name__)


# #EXT-011-REQ-1 Start
@dataclass(frozen=True)
class Schedule:
    """One operator-defined scheduled job and its trigger."""

    id: str
    agent: str
    input: Any = None
    enabled: bool = True
    every_seconds: int | None = None
    cron: str | None = None
    at: str | None = None

    @property
    def trigger(self) -> str:
        if self.every_seconds is not None:
            return f"every {self.every_seconds}s"
        if self.cron:
            return f"cron {self.cron}"
        if self.at:
            return f"at {self.at}"
        return "none"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Schedule":
        """Build + validate a Schedule from a parsed schedule file."""
        if not isinstance(data, dict) or not data.get("id") or not data.get("agent"):
            raise ValueError("schedule requires non-empty 'id' and 'agent'")
        triggers = [t for t in ("every_seconds", "cron", "at") if data.get(t) is not None]
        if len(triggers) != 1:
            raise ValueError(
                f"schedule {data.get('id')!r} must declare exactly one of "
                "every_seconds/cron/at"
            )
        every = data.get("every_seconds")
        if every is not None and (not isinstance(every, int) or every <= 0):
            raise ValueError("every_seconds must be a positive integer")
        if data.get("cron") is not None:
            cron_due(str(data["cron"]), datetime.now())  # validate expression now
        if data.get("at") is not None:
            datetime.fromisoformat(str(data["at"]))  # validate timestamp now
        return cls(
            id=str(data["id"]),
            agent=str(data["agent"]),
            input=data.get("input"),
            enabled=bool(data.get("enabled", True)),
            every_seconds=every,
            cron=data.get("cron"),
            at=data.get("at"),
        )


def load_schedules(schedules_dir: str | os.PathLike[str]) -> list[Schedule]:
    """Load and validate all ``*.json`` schedules, skipping malformed files."""
    directory = Path(schedules_dir)
    out: list[Schedule] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        try:
            out.append(Schedule.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (ValueError, CronError, json.JSONDecodeError, OSError) as exc:
            logger.warning("skipping malformed schedule %s: %s", path.name, exc)
    return out
# #EXT-011-REQ-1 End


# #EXT-011-REQ-3 Start
class Scheduler:
    """Decides which schedules are due, with durable crash-safe last-fire state."""

    def __init__(self, state_path: str | os.PathLike[str]) -> None:
        self.state_path = Path(state_path)
        self._state: dict[str, dict[str, Any]] = self._load_state()

    def _load_state(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _persist(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_name(f".{self.state_path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(self._state, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.state_path)

    @staticmethod
    def _minute_key(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M")

    def _is_due(self, sch: Schedule, now: datetime) -> bool:
        st = self._state.get(sch.id, {})
        if sch.every_seconds is not None:
            last = st.get("lastRun")
            return last is None or (now.timestamp() - float(last)) >= sch.every_seconds
        if sch.cron is not None:
            try:
                if not cron_due(sch.cron, now):
                    return False
            except CronError:
                return False
            return st.get("lastMinute") != self._minute_key(now)
        if sch.at is not None:
            if st.get("fired"):
                return False
            try:
                return now >= datetime.fromisoformat(sch.at)
            except ValueError:
                return False
        return False

    def due(self, schedules: list[Schedule], now: datetime) -> list[Schedule]:
        """Return the enabled schedules that should fire at ``now``."""
        return [s for s in schedules if s.enabled and self._is_due(s, now)]

    def mark_fired(self, sch: Schedule, now: datetime) -> None:
        """Record a dispatch durably so it is not re-fired after a restart."""
        st = self._state.setdefault(sch.id, {})
        st["lastRun"] = now.timestamp()
        st["lastMinute"] = self._minute_key(now)
        if sch.at is not None:
            st["fired"] = True
        self._persist()

    def prune(self, schedule_ids: set[str]) -> None:
        """Drop persisted state for schedules that no longer exist."""
        stale = [sid for sid in self._state if sid not in schedule_ids]
        if stale:
            for sid in stale:
                self._state.pop(sid, None)
            self._persist()
    # #EXT-011-REQ-3 End

    # #EXT-011-REQ-6 Start
    def _next_run(self, sch: Schedule, now: datetime) -> str | None:
        st = self._state.get(sch.id, {})
        if sch.every_seconds is not None:
            base = float(st["lastRun"]) if st.get("lastRun") else now.timestamp()
            return datetime.fromtimestamp(base + sch.every_seconds).isoformat(timespec="seconds")
        if sch.cron is not None:
            probe = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            for _ in range(1440):  # scan up to 24h ahead
                try:
                    if cron_due(sch.cron, probe):
                        return probe.isoformat(timespec="minutes")
                except CronError:
                    return None
                probe += timedelta(minutes=1)
            return None
        if sch.at is not None and not st.get("fired"):
            return sch.at
        return None

    def describe(self, schedules: list[Schedule], now: datetime) -> list[dict[str, Any]]:
        """Return an observable snapshot of each schedule's timing for status.json."""
        out: list[dict[str, Any]] = []
        for s in schedules:
            st = self._state.get(s.id, {})
            last = st.get("lastRun")
            out.append({
                "id": s.id,
                "agent": s.agent,
                "trigger": s.trigger,
                "enabled": s.enabled,
                "lastRun": datetime.fromtimestamp(float(last)).isoformat(timespec="seconds") if last else None,
                "nextRun": self._next_run(s, now) if s.enabled else None,
            })
        return out
    # #EXT-011-REQ-6 End
