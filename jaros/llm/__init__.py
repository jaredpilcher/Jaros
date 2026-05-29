"""Interchangeable LLM Adapter (EXT-004).

The LLM is a pluggable application behind one narrow interface, never a source
of control flow. Callers import the single :class:`LlmClient` interface, the
provider-neutral request/response types, and the config-driven factory from
this one place.
"""

from __future__ import annotations

from jaros.llm.client import LlmClient, LlmRequest, LlmResponse
from jaros.llm.factory import LlmConfig, create_llm_client

__all__ = [
    "LlmClient",
    "LlmRequest",
    "LlmResponse",
    "LlmConfig",
    "create_llm_client",
]
