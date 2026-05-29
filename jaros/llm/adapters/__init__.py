"""Concrete :class:`LlmClient` adapters (EXT-004 / REQ-2).

Each adapter implements the single provider-agnostic interface. Adding a new
adapter requires implementing the interface only — no caller edits.
"""

from __future__ import annotations

from jaros.llm.adapters.default_adapter import DefaultAdapter
from jaros.llm.adapters.uppercase_adapter import UppercaseAdapter

__all__ = ["DefaultAdapter", "UppercaseAdapter"]
