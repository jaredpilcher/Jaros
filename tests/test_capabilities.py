"""Tests for the capability/handle model (EXT-005 / REQ-3)."""

from __future__ import annotations

import pytest

from jaros.comms.fs import SharedFileSystem
from jaros.comms.queue import Queue
from jaros.harness.capabilities import (
    CapabilityError,
    FsRead,
    FsWrite,
    Grants,
    GrantSpec,
    QueueReceive,
    QueueSend,
    RevokedCapabilityError,
    grant,
    revoke,
)


def test_granted_queue_handle_works(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    # AdminRole has FsRead, FsWrite, QueueSend, QueueReceive
    grants = grant(GrantSpec(role="AdminRole", queue=q, fs=fs))

    grants.queue_send.send("hello")
    assert len(q) == 1
    assert grants.queue_receive.receive() == "hello"


def test_granted_fs_handle_works(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    # AdminRole has FsRead, FsWrite, QueueSend, QueueReceive
    grants = grant(GrantSpec(role="AdminRole", queue=q, fs=fs))

    grants.fs_write.write("outbox/msg.txt", "data")
    assert grants.fs_read.read("outbox/msg.txt") == "data"


def test_revoked_handle_raises_before_side_effect(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    # ReporterRole has FsWrite, QueueSend
    grants = grant(GrantSpec(role="ReporterRole", queue=q, fs=fs))

    revoke(grants)

    with pytest.raises(RevokedCapabilityError):
        grants.queue_send.send("nope")
    # No side effect: nothing was enqueued.
    assert len(q) == 0


def test_revoked_fs_handle_raises_before_write(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    # ReporterRole has FsWrite, QueueSend
    grants = grant(GrantSpec(role="ReporterRole", queue=q, fs=fs))

    revoke(grants)

    with pytest.raises(RevokedCapabilityError):
        grants.fs_write.write("outbox/x.txt", "data")
    assert not (tmp_path / "outbox" / "x.txt").exists()


def test_unrequested_capabilities_are_unreachable(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    # ReporterRole only has FsWrite and QueueSend -> the agent has no receive/fs_read handles.
    grants = grant(GrantSpec(role="ReporterRole", queue=q, fs=fs))

    assert grants.queue_send is not None
    assert grants.queue_receive is None
    assert grants.fs_write is not None
    assert grants.fs_read is None


def test_handles_are_frozen_cannot_swap_backing(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    grants = grant(GrantSpec(role="ReporterRole", queue=q, fs=fs))
    handle = grants.queue_send

    with pytest.raises(CapabilityError):
        handle._backing = Queue()  # cannot reach a different/raw queue
    with pytest.raises(CapabilityError):
        handle._revoked = [False]  # cannot clear its own revocation flag


def test_grant_requires_backing_object(tmp_path):
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    q = Queue()
    
    # ReporterRole requires both queue and fs backing objects
    with pytest.raises(CapabilityError):
        grant(GrantSpec(role="ReporterRole"))  # no backing objects at all
    with pytest.raises(CapabilityError):
        grant(GrantSpec(role="ReporterRole", queue=q))  # fs missing
    with pytest.raises(CapabilityError):
        grant(GrantSpec(role="ReporterRole", fs=fs))  # queue missing


def test_revoke_is_idempotent(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    grants = grant(GrantSpec(role="ReporterRole", queue=q, fs=fs))
    revoke(grants)
    revoke(grants)
    assert grants.revoked is True
