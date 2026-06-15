"""Lightweight, file/env-driven default-LLM selection (EXT-004 / REQ-4).

No bespoke client library: the *active* model for the whole node is chosen by a
tiny JSON file or one environment variable, then built through the existing
:func:`jaros.llm.create_llm_client` factory. Point the swarm at a different model
by editing ``config/llm.json`` (or setting ``JAROS_LLM_PROVIDER``) — no code
change. Every agent already reaches the model through the one ``LlmClient``
interface, so a config edit re-points all of them at once.

Resolution order (first match wins):
  1. ``JAROS_LLM_PROVIDER`` env var (+ optional ``JAROS_LLM_MODEL``).
  2. ``<data-dir>/config/llm.json``  — travels with the data dir.
  3. ``./config/llm.json``           — repo/working-dir default.
  4. the built-in ``default`` echo adapter (a deterministic mock).

``config/llm.json`` is just: ``{"provider": "ollama", "options": {"model": "llama3"}}``
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from jaros.llm.factory import LlmConfig

DEFAULT_PROVIDER = "default"


def resolve_llm_config(data_dir: str | os.PathLike[str] | None = None) -> LlmConfig:
    """Return the configured :class:`LlmConfig`, or the default echo mock."""
    provider = os.environ.get("JAROS_LLM_PROVIDER")
    if provider:
        options: dict[str, object] = {}
        model = os.environ.get("JAROS_LLM_MODEL")
        if model:
            options["model"] = model
        return LlmConfig(provider=provider, options=options)

    candidates: list[Path] = []
    if data_dir is not None:
        candidates.append(Path(data_dir) / "config" / "llm.json")
    candidates.append(Path("config") / "llm.json")
    for path in candidates:
        try:
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("provider"):
                    return LlmConfig(
                        provider=str(data["provider"]),
                        options=dict(data.get("options") or {}),
                    )
        except (OSError, ValueError):
            continue

    return LlmConfig(provider=DEFAULT_PROVIDER)
