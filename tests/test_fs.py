"""Tests for the shared file system layout (EXT-006 / REQ-2, REQ-4)."""

from __future__ import annotations

import pytest

from jaros.comms.fs import LAYOUT_DIRS, LayoutViolationError, SharedFileSystem


def test_ensure_layout_creates_dirs_idempotently(tmp_path):
    sfs = SharedFileSystem(tmp_path)
    sfs.ensure_layout()
    sfs.ensure_layout()  # idempotent
    for name in LAYOUT_DIRS:
        assert (tmp_path / name).is_dir()


def test_validate_layout_passes_on_fresh_layout(tmp_path):
    sfs = SharedFileSystem(tmp_path)
    sfs.ensure_layout()
    sfs.validate_layout()  # must not raise


def test_validate_layout_fails_when_dir_missing(tmp_path):
    sfs = SharedFileSystem(tmp_path)
    sfs.ensure_layout()
    (tmp_path / "inbox").rmdir()
    with pytest.raises(LayoutViolationError):
        sfs.validate_layout()


def test_write_read_round_trip_in_each_layout_dir(tmp_path):
    sfs = SharedFileSystem(tmp_path)
    sfs.ensure_layout()
    for name in LAYOUT_DIRS:
        rel = f"{name}/msg.txt"
        sfs.write(rel, f"hello-{name}")
        assert sfs.read(rel) == f"hello-{name}"


def test_write_is_atomic_no_temp_left_behind(tmp_path):
    sfs = SharedFileSystem(tmp_path)
    sfs.ensure_layout()
    sfs.write("artifacts/a.txt", "data")
    leftovers = list((tmp_path / "artifacts").glob(".*tmp"))
    assert leftovers == []


def test_refuses_parent_traversal(tmp_path):
    sfs = SharedFileSystem(tmp_path)
    sfs.ensure_layout()
    with pytest.raises(LayoutViolationError):
        sfs.write("../escape.txt", "x")
    with pytest.raises(LayoutViolationError):
        sfs.read("inbox/../../escape.txt")


def test_refuses_absolute_path(tmp_path):
    sfs = SharedFileSystem(tmp_path)
    sfs.ensure_layout()
    abs_path = str((tmp_path.parent / "abs.txt").resolve())
    with pytest.raises(LayoutViolationError):
        sfs.write(abs_path, "x")


def test_layout_dir_names_exposed():
    assert LAYOUT_DIRS == (
        "state",
        "inbox",
        "outbox",
        "artifacts",
        "plugins",
        "processed",
        "failed",
    )
    assert SharedFileSystem.LAYOUT_DIRS == LAYOUT_DIRS
