"""The single, provider-agnostic LLM interface (EXT-004 / REQ-1, REQ-3).

All model access in the Reasoning Plane goes through one narrow contract,
:class:`LlmClient`, with a single primary entry point: ``complete``. Callers
depend only on this interface and the provider-neutral request/response
dataclasses below — no concrete provider type ever leaks to a caller.

No control flow inside the LLM (EXT-004 / REQ-3, PRIME-001):
    The LLM decides *what* to propose, never *how* the system runs. What
    crosses this boundary is **data only**:

    - :class:`LlmRequest`  -> ``complete`` -> :class:`LlmResponse`.

    :class:`LlmResponse` carries inert ``text``/``structured``/``model`` data
    and nothing else. It holds **no handles** (no sockets, file objects,
    callables, futures, or provider client instances) and nothing that can
    invoke a state-machine transition or perform a side effect. Reasoning
    consumes the response and may emit a ``Decision`` (EXT-001); the LLM itself
    never calls ``transition(...)`` and never drives execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from jaros.core.json_value import JsonValue


# #EXT-004-REQ-1 Start
@dataclass(frozen=True)
class LlmRequest:
    """A provider-neutral request to an :class:`LlmClient`.

    No provider-specific types appear here; any conforming adapter can satisfy
    it. ``params`` carries optional, inert JSON tuning data (e.g. temperature)
    and never callbacks or handles.

    Attributes:
        prompt: The input text the model should reason over.
        params: Optional, inert JSON-serializable tuning parameters.
    """

    prompt: str
    params: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class LlmResponse:
    """A provider-neutral, data-only response from an :class:`LlmClient`.

    Carries model output as inert data only. It deliberately holds no handles
    and nothing that drives a state transition: just ``text`` (the primary
    output), optional ``structured`` JSON data, and the ``model`` identifier
    that produced it.

    Attributes:
        text: The primary textual output of the model.
        model: Identifier of the model/adapter that produced this response.
        structured: Optional structured output as inert JSON data.
    """

    text: str
    model: str
    structured: JsonValue = None
# #EXT-004-REQ-1 End


# #EXT-004-REQ-1 Start
@runtime_checkable
class LlmClient(Protocol):
    """The single, narrow interface every model/provider adapter satisfies.

    Callers depend only on this Protocol — never on a concrete provider. The
    sole entry point, :meth:`complete`, takes inert data in and returns inert
    data out (EXT-004 / REQ-3); it must not perform side effects, hold system
    handles, or invoke any state-machine transition.
    """

    def complete(self, req: LlmRequest) -> LlmResponse:
        """Produce a data-only :class:`LlmResponse` for ``req``."""
        ...
# #EXT-004-REQ-1 End
