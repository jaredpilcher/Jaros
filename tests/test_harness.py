"""Tests for harness mediation, default-deny, and configurable rules (EXT-005).

Covers REQ-1 (mediated actions), REQ-2 (non-bypassable, fail-closed), and
REQ-5 (developer-configurable rule set).
"""

from __future__ import annotations

import pytest

from jaros.comms.fs import SharedFileSystem
from jaros.comms.queue import Queue
from jaros.harness.capabilities import (
    FsRead,
    FsWrite,
    GrantSpec,
    QueueReceive,
    QueueSend,
)
from jaros.harness.harness import Action, Harness


def test_mediated_queue_send_through_harness():
    q: Queue = Queue()
    h = Harness()
    ctx = h.spawn("a1", GrantSpec(capabilities=(QueueSend(),), queue=q))

    result = h.request("a1", Action(type="queue.send", message="work"))

    assert result.allowed is True
    assert len(q) == 1
    assert q.peek() == "work"
    # The agent context exposes only its grants, no global refs.
    assert ctx.grants.queue_send is not None
    assert not hasattr(ctx, "queue")
    assert not hasattr(ctx, "fs")


def test_queue_send_only_agent_cannot_touch_fs(tmp_path):
    q: Queue = Queue()
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    h = Harness()
    # Granted only QueueSend; backing fs deliberately not provided.
    h.spawn("sender", GrantSpec(capabilities=(QueueSend(),), queue=q))

    write = h.request("sender", Action(type="fs.write", path="outbox/x.txt", data="d"))
    read = h.request("sender", Action(type="fs.read", path="outbox/x.txt"))

    assert write.allowed is False
    assert read.allowed is False
    assert not (tmp_path / "outbox" / "x.txt").exists()


def test_disallowed_action_is_refused_with_no_side_effect():
    q: Queue = Queue()
    h = Harness()
    h.spawn("a1", GrantSpec(capabilities=(QueueSend(),), queue=q))

    # Unknown action type -> default-deny, recorded, no effect.
    result = h.request("a1", Action(type="network.connect", message="evil"))

    assert result.allowed is False
    assert result.reason is not None
    assert len(q) == 0
    assert ("a1", "network.connect", result.reason) in h.denied


def test_unknown_agent_is_denied():
    h = Harness()
    result = h.request("ghost", Action(type="queue.send", message="x"))
    assert result.allowed is False
    assert "unknown agent" in (result.reason or "")


def test_teardown_revokes_capabilities():
    q: Queue = Queue()
    h = Harness()
    h.spawn("a1", GrantSpec(capabilities=(QueueSend(),), queue=q))

    h.teardown("a1")

    result = h.request("a1", Action(type="queue.send", message="x"))
    assert result.allowed is False
    assert len(q) == 0


def test_harness_rules_not_mutable_by_agent_at_runtime():
    h = Harness()
    rules = h.describe_rules()
    # The snapshot an agent can introspect is a frozen read-only mapping.
    with pytest.raises(TypeError):
        rules["queue.send"] = "FsWrite"  # type: ignore[index]
    # And the harness still enforces the original rules afterward.
    assert h.describe_rules()["queue.send"] == "QueueSend"


# --- REQ-5: developer-configurable rule set --------------------------------


def test_constructed_with_tighter_rule_is_enforced():
    # Operator tightens the rule set: writing to fs now requires FsRead too is
    # not expressible as one cap, so instead we *forbid* fs.write by requiring a
    # capability the agent is given but mapping queue.send to FsWrite (tighter:
    # an agent that only has QueueSend can no longer send to the queue).
    q: Queue = Queue()
    # Override: 'queue.send' now requires the FsWrite capability instead.
    h = Harness(rules={"queue.send": FsWrite})
    h.spawn("a1", GrantSpec(capabilities=(QueueSend(),), queue=q))

    result = h.request("a1", Action(type="queue.send", message="x"))

    assert result.allowed is False  # agent lacks FsWrite -> denied
    assert len(q) == 0
    assert h.describe_rules()["queue.send"] == "FsWrite"


def test_constructed_with_extra_rule_is_enforced(tmp_path):
    # Add a brand-new action type at boot, mapping it to FsRead.
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    fs.write("inbox/note.txt", "hi")
    h = Harness(rules={"fs.peek": FsRead})
    h.spawn(
        "a1",
        GrantSpec(capabilities=(FsRead(),), fs=fs),
    )

    result = h.request("a1", Action(type="fs.peek", path="inbox/note.txt"))

    assert result.allowed is True
    assert result.value == "hi"
    assert h.describe_rules()["fs.peek"] == "FsRead"


def test_configured_rules_fall_back_to_defaults():
    h = Harness()  # no rules supplied
    assert h.describe_rules()["fs.write"] == "FsWrite"
    assert h.describe_rules()["queue.receive"] == "QueueReceive"


def test_configured_rules_frozen_and_not_agent_mutable():
    h = Harness(rules={"fs.peek": FsRead})
    snap = h.describe_rules()
    assert snap["fs.peek"] == "FsRead"
    with pytest.raises(TypeError):
        snap["fs.peek"] = "FsWrite"  # type: ignore[index]
    # Enforcement unchanged after attempted mutation.
    assert h.describe_rules()["fs.peek"] == "FsRead"


def test_full_round_trip_fs_write_then_read(tmp_path):
    fs = SharedFileSystem(tmp_path)
    fs.ensure_layout()
    h = Harness()
    h.spawn("a1", GrantSpec(capabilities=(FsWrite(), FsRead()), fs=fs))

    w = h.request("a1", Action(type="fs.write", path="artifacts/o.txt", data="payload"))
    r = h.request("a1", Action(type="fs.read", path="artifacts/o.txt"))

    assert w.allowed is True
    assert r.allowed is True
    assert r.value == "payload"
