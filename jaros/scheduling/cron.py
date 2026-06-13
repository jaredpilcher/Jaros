"""Pure standard-library 5-field cron matcher (EXT-011 / REQ-2).

`cron_due(expr, dt)` returns whether a standard ``m h dom mon dow`` cron
expression matches the given :class:`~datetime.datetime` at minute granularity.
Supported field syntax: ``*``, lists (``1,2``), ranges (``1-5``), and steps
(``*/15``, ``0-30/10``). Day-of-week is ``0-6`` with Sunday = 0 (``7`` also
accepted for Sunday). When both day-of-month and day-of-week are restricted, a
match on *either* fires — the standard cron rule.

This module imports only the standard library and performs no I/O, so it does
not affect the no-server / zero-infrastructure guardrails over ``jaros/**``.
"""

from __future__ import annotations

from datetime import datetime


# #EXT-011-REQ-2 Start
class CronError(ValueError):
    """Raised when a cron expression or field is malformed."""


def _parse_field(spec: str, lo: int, hi: int) -> set[int]:
    """Expand one cron field into the set of integer values it permits."""
    allowed: set[int] = set()
    for part in spec.split(","):
        if not part:
            raise CronError(f"empty cron field segment in {spec!r}")
        rng, _, step_s = part.partition("/")
        try:
            step = int(step_s) if step_s else 1
            if rng == "*":
                start, end = lo, hi
            elif "-" in rng:
                a, b = rng.split("-", 1)
                start, end = int(a), int(b)
            else:
                start = end = int(rng)
        except ValueError:
            raise CronError(f"bad cron field segment {part!r}")
        if step <= 0 or start < lo or end > hi or start > end:
            raise CronError(f"cron field segment out of range: {part!r}")
        allowed.update(range(start, end + 1, step))
    return allowed


def cron_due(expr: str, dt: datetime) -> bool:
    """Return True iff the 5-field cron ``expr`` matches ``dt`` (minute granularity)."""
    fields = expr.split()
    if len(fields) != 5:
        raise CronError(f"cron needs 5 fields, got {len(fields)}: {expr!r}")
    minute_s, hour_s, dom_s, mon_s, dow_s = fields

    minutes = _parse_field(minute_s, 0, 59)
    hours = _parse_field(hour_s, 0, 23)
    doms = _parse_field(dom_s, 1, 31)
    months = _parse_field(mon_s, 1, 12)
    dows = _parse_field(dow_s, 0, 7)
    if 7 in dows:
        dows = set(dows) | {0}

    if dt.minute not in minutes or dt.hour not in hours or dt.month not in months:
        return False

    cron_dow = dt.isoweekday() % 7  # Sunday=0 .. Saturday=6
    dom_ok = dt.day in doms
    dow_ok = cron_dow in dows

    # Standard cron: if both DOM and DOW are restricted, match either.
    if dom_s != "*" and dow_s != "*":
        return dom_ok or dow_ok
    return dom_ok and dow_ok
# #EXT-011-REQ-2 End
