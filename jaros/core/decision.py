"""The inert Decision contract (EXT-001 / REQ-1).

A Decision is the *only* thing the Reasoning Plane may emit. It is immutable,
JSON-serializable data: it carries intent (``kind``) and inert ``payload`` data,
never callbacks, closures, or handles. It records its ``source`` (the emitting
agent) and a discriminated ``kind`` so the executor can dispatch deterministically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from jaros.core.json_value import JsonValue, assert_serializable


# #EXT-001-REQ-1 Start
@dataclass(frozen=True)
class Decision:
    """An immutable, JSON-serializable proposal emitted by the Reasoning Plane.

    Attributes:
        id: Unique identifier for this decision.
        source: Identifier of the emitting agent/source.
        kind: Discriminator used for deterministic executor dispatch.
        payload: Inert, JSON-serializable data only.
    """

    id: str
    source: str
    kind: str
    payload: JsonValue


def create_decision(
    *,
    id: str,
    source: str,
    kind: str,
    payload: JsonValue,
) -> Decision:
    """Construct a validated, frozen :class:`Decision`.

    The payload is asserted to be inert JSON data and proven to be
    round-trippable (serialize -> deserialize -> identical), guaranteeing the
    Decision carries no executable side effect.

    Raises:
        NotSerializableError: if the payload contains non-serializable values.
    """
    assert_serializable(payload)
    # Prove serialize -> deserialize -> identical (the Decision is pure data).
    if json.loads(json.dumps(payload)) != payload:
        raise ValueError("payload is not JSON round-trippable")
    return Decision(id=id, source=source, kind=kind, payload=payload)
# #EXT-001-REQ-1 End
