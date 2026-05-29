"""The single Reasoning Plane boundary interface (EXT-001 / REQ-2).

All reasoning is funnelled through :class:`ReasoningBoundary`, whose only output
type is ``list[Decision]``. This module imports *only* from ``decision.py`` — it
holds no reference to the executor, state store, queues, or file system handles,
enforcing that nothing on the reasoning side can reach into execution directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from jaros.core.decision import Decision


# #EXT-001-REQ-2 Start
@runtime_checkable
class ReasoningBoundary(Protocol):
    """Interface every reasoning entry point is typed against.

    Its only output is inert ``Decision`` data; it cannot perform side effects.
    """

    def decide(self, context: object) -> list[Decision]:
        """Reason over ``context`` and return inert decisions only."""
        ...
# #EXT-001-REQ-2 End
