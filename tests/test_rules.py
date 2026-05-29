"""Tests for the architectural rule set (EXT-005 / REQ-4)."""

from __future__ import annotations

import pytest

from jaros.harness.capabilities import FsWrite, QueueSend
from jaros.harness.rules import (
    DEFAULT_RULES,
    describe_rules,
    freeze_rules,
)


def test_default_rules_map_actions_to_capabilities():
    assert DEFAULT_RULES["queue.send"] is QueueSend
    assert DEFAULT_RULES["fs.write"] is FsWrite


def test_default_rules_are_deep_frozen():
    # MappingProxyType refuses item assignment / deletion at runtime.
    with pytest.raises(TypeError):
        DEFAULT_RULES["queue.send"] = FsWrite  # type: ignore[index]
    with pytest.raises(TypeError):
        del DEFAULT_RULES["queue.send"]  # type: ignore[misc]


def test_freeze_rules_is_independent_of_source_dict():
    src = {"queue.send": QueueSend}
    frozen = freeze_rules(src)
    src["queue.send"] = FsWrite  # mutate the original
    assert frozen["queue.send"] is QueueSend  # snapshot unaffected
    with pytest.raises(TypeError):
        frozen["x"] = FsWrite  # type: ignore[index]


def test_describe_rules_is_an_immutable_snapshot():
    snap = describe_rules()
    assert snap["fs.write"] == "FsWrite"
    with pytest.raises(TypeError):
        snap["fs.write"] = "QueueSend"  # type: ignore[index]
