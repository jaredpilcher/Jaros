"""Core boundary contracts for the Reasoning / Execution seam (EXT-001).

Re-exports the inert Decision contract, its constructor, the reasoning boundary
interface, and the JSON value types so callers import them from one place.
"""

from __future__ import annotations

from jaros.core.decision import Decision, create_decision
from jaros.core.json_value import (
    JsonValue,
    NotSerializableError,
    assert_serializable,
)
from jaros.core.reasoning_boundary import ReasoningBoundary

__all__ = [
    "Decision",
    "create_decision",
    "ReasoningBoundary",
    "JsonValue",
    "NotSerializableError",
    "assert_serializable",
]
