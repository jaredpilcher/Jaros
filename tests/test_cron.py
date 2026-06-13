"""Tests for the pure-stdlib cron matcher (EXT-011 / REQ-2)."""

from __future__ import annotations

from datetime import datetime

import pytest

from jaros.scheduling.cron import CronError, cron_due


def dt(y=2026, mo=6, d=13, h=9, mi=0):
    return datetime(y, mo, d, h, mi)


def test_wildcard_always_matches():
    assert cron_due("* * * * *", dt(h=3, mi=27)) is True


def test_minute_step():
    expr = "*/15 * * * *"
    assert cron_due(expr, dt(mi=0)) is True
    assert cron_due(expr, dt(mi=15)) is True
    assert cron_due(expr, dt(mi=45)) is True
    assert cron_due(expr, dt(mi=7)) is False


def test_exact_minute_and_hour():
    expr = "30 9 * * *"
    assert cron_due(expr, dt(h=9, mi=30)) is True
    assert cron_due(expr, dt(h=9, mi=31)) is False
    assert cron_due(expr, dt(h=10, mi=30)) is False


def test_list_and_range():
    assert cron_due("0 9,17 * * *", dt(h=17, mi=0)) is True
    assert cron_due("0 9,17 * * *", dt(h=12, mi=0)) is False
    # 2026-06-13 is a Saturday; 1-5 = Mon-Fri should not match
    assert cron_due("0 9 * * 1-5", dt(d=13, h=9, mi=0)) is False
    # 2026-06-15 is a Monday
    assert cron_due("0 9 * * 1-5", dt(d=15, h=9, mi=0)) is True


def test_sunday_zero_and_seven():
    # 2026-06-14 is a Sunday
    assert cron_due("0 0 * * 0", dt(d=14, h=0, mi=0)) is True
    assert cron_due("0 0 * * 7", dt(d=14, h=0, mi=0)) is True


def test_dom_dow_or_semantics():
    # Both restricted -> match either. 2026-06-13 is Saturday (dow=6), day 13.
    assert cron_due("0 0 13 * 1", dt(d=13, h=0, mi=0)) is True   # matches DOM
    assert cron_due("0 0 1 * 6", dt(d=13, h=0, mi=0)) is True    # matches DOW (Sat)
    assert cron_due("0 0 1 * 1", dt(d=13, h=0, mi=0)) is False   # neither


@pytest.mark.parametrize("expr", ["* * * *", "60 * * * *", "* 24 * * *", "*/0 * * * *", "a * * * *", "5-2 * * * *"])
def test_malformed_raises(expr):
    with pytest.raises(CronError):
        cron_due(expr, dt())
