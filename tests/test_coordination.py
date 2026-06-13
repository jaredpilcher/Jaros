"""Tests for bounded multi-node coordination over the shared FS (EXT-002 / REQ-7).

Single-node is a zero-overhead no-op; multi-node claims and hands off work via
atomic claim files on the shared file system — no broker or network.
"""

from __future__ import annotations

from jaros.state import FileCoordinator


def test_single_node_is_zero_overhead_noop(tmp_path):
    coord = FileCoordinator(tmp_path, node_id="solo")  # single_node=True default
    # Claims always succeed and write nothing to disk.
    assert coord.try_claim("job-1") is True
    assert coord.try_claim("job-1") is True
    assert not (tmp_path / "state" / "claims").exists()
    assert coord.owner("job-1") == "solo"


def test_multi_node_claim_is_exclusive(tmp_path):
    a = FileCoordinator(tmp_path, node_id="node-a", single_node=False)
    b = FileCoordinator(tmp_path, node_id="node-b", single_node=False)

    assert a.try_claim("job-1") is True
    # The shared file system arbitrates: b cannot claim what a holds.
    assert b.try_claim("job-1") is False
    assert a.owner("job-1") == "node-a"
    assert b.owner("job-1") == "node-a"


def test_multi_node_handoff_after_release(tmp_path):
    a = FileCoordinator(tmp_path, node_id="node-a", single_node=False)
    b = FileCoordinator(tmp_path, node_id="node-b", single_node=False)

    assert a.try_claim("job-1") is True
    assert b.try_claim("job-1") is False

    a.release("job-1")
    # After release, another node can pick up the work.
    assert b.try_claim("job-1") is True
    assert b.owner("job-1") == "node-b"


def test_expired_lease_is_stolen_but_fresh_is_not(tmp_path):
    import os
    import time

    a = FileCoordinator(tmp_path, node_id="node-a", single_node=False, lease_seconds=1.0)
    b = FileCoordinator(tmp_path, node_id="node-b", single_node=False, lease_seconds=1.0)
    assert a.try_claim("job") is True
    assert b.try_claim("job") is False          # live claim is not stealable
    assert b.owner("job") == "node-a"

    # Node-a "crashes": its claim's lease expires (no more renew).
    claim = tmp_path / "state" / "claims" / "job.claim"
    old = time.time() - 100
    os.utime(claim, (old, old))
    assert b.try_claim("job") is True            # stolen after the lease expired
    assert b.owner("job") == "node-b"


def test_renew_keeps_a_claim_and_rejects_non_owner(tmp_path):
    a = FileCoordinator(tmp_path, node_id="node-a", single_node=False, lease_seconds=10.0)
    assert a.try_claim("job") is True
    assert a.renew("job") is True
    b = FileCoordinator(tmp_path, node_id="node-b", single_node=False, lease_seconds=10.0)
    assert b.renew("job") is False               # cannot renew what you don't own


def test_release_is_idempotent_and_unclaimed_owner_is_none(tmp_path):
    b = FileCoordinator(tmp_path, node_id="node-b", single_node=False)
    assert b.owner("never") is None
    b.release("never")  # no error
    b.release("never")
