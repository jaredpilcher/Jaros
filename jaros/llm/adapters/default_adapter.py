"""Deterministic echo adapter implementing :class:`LlmClient` (EXT-004 / REQ-2).

A concrete, dependency-free adapter used as the default model. It is
deterministic (same request -> same response) and returns inert data only,
never driving control flow (EXT-004 / REQ-3).
"""

from __future__ import annotations

from dataclasses import dataclass

from jaros.llm.client import LlmRequest, LlmResponse


# #EXT-004-REQ-2 Start
@dataclass(frozen=True)
class DefaultAdapter:
    """Deterministic echo adapter that conforms to :class:`LlmClient`.

    Returns the prompt verbatim as ``text``. Holds no provider handles and
    performs no side effects.
    """

    model: str = "default-echo"

    def complete(self, req: LlmRequest) -> LlmResponse:
        """Echo the prompt back as data-only output."""
        return LlmResponse(text=req.prompt, model=self.model)
# #EXT-004-REQ-2 End
