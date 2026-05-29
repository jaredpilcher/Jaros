"""JSON value type and a recursive serializability guard.

A `Decision` payload (EXT-001 / REQ-1) must be inert, JSON-serializable data
only — never functions, closures, handles, class instances, sets, or bytes.
This module defines the allowed value space and the guard that enforces it.
"""

from __future__ import annotations

from typing import Union

# #EXT-001-REQ-1 Start
# A JsonValue is the closed set of JSON-representable Python values.
JsonValue = Union[
    None,
    bool,
    int,
    float,
    str,
    list["JsonValue"],
    dict[str, "JsonValue"],
]


class NotSerializableError(TypeError):
    """Raised when a value contains anything that is not inert JSON data."""


def assert_serializable(value: object, *, _path: str = "$") -> None:
    """Recursively assert that ``value`` is inert, JSON-serializable data.

    Rejects functions, lambdas, class instances, sets, tuples, bytes, and any
    other non-JSON type. ``bool`` is allowed (it is a JSON boolean) but is
    checked before ``int`` because ``bool`` is a subclass of ``int``. Dict keys
    must be strings, matching JSON object semantics.

    Raises:
        NotSerializableError: if any nested value is not JSON-serializable.
    """
    if value is None:
        return
    # bool must precede the int/float check since bool subclasses int.
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        # Reject NaN/Infinity which are not valid JSON.
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise NotSerializableError(
                f"non-finite float is not JSON-serializable at {_path}"
            )
        return
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            assert_serializable(item, _path=f"{_path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NotSerializableError(
                    f"dict key {key!r} is not a string at {_path}"
                )
            assert_serializable(item, _path=f"{_path}.{key}")
        return
    raise NotSerializableError(
        f"value of type {type(value).__name__!r} is not JSON-serializable at {_path}"
    )
# #EXT-001-REQ-1 End
