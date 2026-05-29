"""Configuration-driven adapter selection (EXT-004 / REQ-2, REQ-4).

The active :class:`LlmClient` is chosen by configuration at startup. Swapping
the underlying model/provider is a configuration change, not a code change:
the harness, state machine, and callers require zero modification. Adding a new
provider means registering an adapter here and implementing the interface —
nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from jaros.core.json_value import JsonValue
from jaros.llm.adapters.default_adapter import DefaultAdapter
from jaros.llm.adapters.uppercase_adapter import UppercaseAdapter
from jaros.llm.client import LlmClient


# #EXT-004-REQ-2 Start
@dataclass(frozen=True)
class LlmConfig:
    """Provider-neutral configuration selecting an :class:`LlmClient`.

    Attributes:
        provider: Registered provider key (see :data:`_REGISTRY`).
        options: Optional, inert JSON-serializable adapter options.
    """

    provider: str
    options: dict[str, JsonValue] = field(default_factory=dict)


# The provider registry. Adding an adapter is a one-line registration here plus
# an interface implementation — callers and the harness are untouched.
_REGISTRY: dict[str, Callable[[], LlmClient]] = {
    "default": DefaultAdapter,
    "uppercase": UppercaseAdapter,
}
# #EXT-004-REQ-2 End


# #EXT-004-REQ-4 Start
def create_llm_client(config: LlmConfig | Mapping[str, JsonValue]) -> LlmClient:
    """Build the configured :class:`LlmClient` from ``config``.

    Accepts either an :class:`LlmConfig` or a plain mapping with a ``provider``
    key, so selection is achievable by editing configuration alone. The same
    call site yields a different adapter purely by changing ``provider``.

    Args:
        config: An :class:`LlmConfig`, or a mapping containing ``provider``.

    Returns:
        A concrete adapter satisfying :class:`LlmClient`.

    Raises:
        ValueError: if ``provider`` is missing or unknown. The error lists the
            known providers to make a misconfiguration obvious.
    """
    if isinstance(config, LlmConfig):
        provider = config.provider
    else:
        if "provider" not in config:
            raise ValueError(
                "LLM config is missing required 'provider' key; "
                f"known providers: {_known_providers()}"
            )
        provider = config["provider"]

    factory = _REGISTRY.get(provider)
    if factory is None:
        raise ValueError(
            f"unknown LLM provider {provider!r}; "
            f"known providers: {_known_providers()}"
        )
    return factory()


def _known_providers() -> str:
    """Return a stable, human-readable list of registered provider keys."""
    return ", ".join(sorted(_REGISTRY))
# #EXT-004-REQ-4 End
