"""Tests for the inert Decision contract (EXT-001 / REQ-1)."""

from __future__ import annotations

import dataclasses

import pytest

from jaros.core import Decision, create_decision
from jaros.core.json_value import NotSerializableError, assert_serializable


def test_assert_serializable_accepts_nested_json():
    assert_serializable({"a": [1, 2.5, "x", True, None], "b": {"c": []}})


def test_assert_serializable_rejects_function():
    with pytest.raises(NotSerializableError):
        assert_serializable({"cb": lambda: None})


def test_assert_serializable_rejects_set_bytes_and_instances():
    class Thing:
        pass

    for bad in ({1, 2, 3}, b"bytes", Thing(), (1, 2)):
        with pytest.raises(NotSerializableError):
            assert_serializable(bad)


def test_assert_serializable_rejects_non_string_dict_key():
    with pytest.raises(NotSerializableError):
        assert_serializable({1: "x"})


def test_create_decision_returns_frozen_immutable():
    d = create_decision(id="d1", source="agent-a", kind="noop", payload={"n": 1})
    assert isinstance(d, Decision)
    assert d.id == "d1" and d.source == "agent-a" and d.kind == "noop"
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.id = "other"  # type: ignore[misc]


def test_create_decision_rejects_non_serializable_payload():
    with pytest.raises(NotSerializableError):
        create_decision(id="d", source="a", kind="k", payload={"f": lambda: 1})


def test_create_decision_payload_round_trips():
    payload = {"items": [1, "two", {"three": 3}], "flag": False}
    d = create_decision(id="d", source="a", kind="k", payload=payload)
    assert d.payload == payload
