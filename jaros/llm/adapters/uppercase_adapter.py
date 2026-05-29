"""Deterministic uppercasing adapter implementing :class:`LlmClient`.

A second concrete adapter (EXT-004 / REQ-2, REQ-4) used to prove that swapping
the configured provider changes output at the same call site with no caller
change. Deterministic and data-only (EXT-004 / REQ-3).
"""

from __future__ import annotations

from dataclasses import dataclass

from jaros.llm.client import LlmRequest, LlmResponse


# #EXT-004-REQ-2 Start
@dataclass(frozen=True)
class UppercaseAdapter:
    """Deterministic adapter that uppercases the prompt; conforms to LlmClient.

    Distinct from :class:`DefaultAdapter` so a config-only swap is observable.
    Holds no provider handles and performs no side effects.
    """

    model: str = "uppercase-echo"

    def complete(self, req: LlmRequest) -> LlmResponse:
        """Return the uppercased prompt as data-only output."""
        return LlmResponse(text=req.prompt.upper(), model=self.model)
# #EXT-004-REQ-2 End
