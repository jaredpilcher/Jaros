"""Tests for the durable append-only transition log (EXT-002 / REQ-3)."""

from __future__ import annotations

from jaros.state.log import LogEntry, TransitionLog


def _entry(index, event, state):
    return LogEntry.make(index=index, event=event, state=state)


def test_append_and_read_preserve_order(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    log.append(_entry(1, "start", "RUNNING"))
    log.append(_entry(2, "block", "BLOCKED"))
    log.append(_entry(3, "unblock", "RUNNING"))

    entries = list(log.read())
    assert [e.index for e in entries] == [1, 2, 3]
    assert [e.event for e in entries] == ["start", "block", "unblock"]
    assert [e.state for e in entries] == ["RUNNING", "BLOCKED", "RUNNING"]
    assert log.length() == 3


def test_append_is_durable_across_new_handles(tmp_path):
    TransitionLog(tmp_path, "t.log").ensure()
    writer = TransitionLog(tmp_path, "t.log")
    writer.append(_entry(1, "start", "RUNNING"))

    # A brand-new handle (simulating a restart) sees the persisted entry.
    reader = TransitionLog(tmp_path, "t.log")
    entries = list(reader.read())
    assert len(entries) == 1
    assert entries[0].state == "RUNNING"


def test_each_entry_has_index_and_valid_checksum(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    log.append(_entry(1, "start", "RUNNING"))
    (entry,) = list(log.read())
    assert entry.index == 1
    assert entry.checksum_ok()


def test_read_tolerates_torn_trailing_line(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    log.append(_entry(1, "start", "RUNNING"))
    log.append(_entry(2, "complete", "DONE"))

    # Simulate an interrupted append: a partial final line with no newline.
    with open(log.path, "a", encoding="utf-8") as fh:
        fh.write('{"index": 3, "event": "fa')  # torn, no newline

    entries = list(log.read())
    # The torn trailing line is dropped; earlier entries survive intact.
    assert [e.index for e in entries] == [1, 2]
    assert entries[-1].state == "DONE"


def test_ensure_is_idempotent_and_creates_file(tmp_path):
    log = TransitionLog(tmp_path / "sub", "t.log")
    log.ensure()
    log.ensure()
    assert log.path.exists()
    assert log.length() == 0


def test_read_empty_log_yields_nothing(tmp_path):
    log = TransitionLog(tmp_path, "t.log")
    log.ensure()
    assert list(log.read()) == []
