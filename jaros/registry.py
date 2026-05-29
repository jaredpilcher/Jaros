"""Runtime agent registry + plugin loading (EXT-007 / REQ-3).

The registry maps an agent ``kind`` to a factory that produces a
:class:`~jaros.core.reasoning_boundary.ReasoningBoundary`. Built-in kinds are
registered at boot via :func:`register_builtins`; new agent modules dropped into
the shared-FS ``plugins/`` directory are imported and registered at runtime via
:func:`load_plugins` — no daemon restart required.

A plugin module declares a module-level ``KIND: str`` and a ``build(llm)``
factory returning a ``ReasoningBoundary``. :func:`load_plugins` is idempotent
across re-scans: a module file is imported and registered exactly once.

This module is part of the daemon's *composition root*; it wires the reasoning
side (LLM + boundaries) together but performs no side effects of its own and
opens no network channel.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from typing import Callable

from jaros.core import Decision, ReasoningBoundary, create_decision
from jaros.llm import LlmClient, LlmRequest

# A factory builds a fresh ReasoningBoundary for a resolved agent kind. Built-in
# factories may close over the shared LlmClient; plugin factories receive it.
AgentBoundaryFactory = Callable[[], ReasoningBoundary]


# #EXT-007-REQ-3 Start
class AgentRegistry:
    """Maps an agent ``kind`` to a factory producing a ``ReasoningBoundary``.

    The registry is the single lookup the daemon consults to turn an inbox job's
    declared ``kind`` into a runnable reasoning boundary.
    """

    def __init__(self) -> None:
        self._factories: dict[str, AgentBoundaryFactory] = {}
        # Absolute paths of plugin files already imported, so re-scans are
        # idempotent (a plugin is loaded + registered exactly once).
        self._loaded_plugins: set[str] = set()

    def register(self, kind: str, factory: AgentBoundaryFactory) -> None:
        """Register ``factory`` as the producer for agent ``kind``.

        Re-registering a kind replaces the prior factory (last-writer-wins),
        which keeps plugin reloads well-defined.
        """
        if not isinstance(kind, str) or not kind:
            raise ValueError("agent kind must be a non-empty string")
        self._factories[kind] = factory

    def resolve(self, kind: str) -> ReasoningBoundary:
        """Build and return a fresh ``ReasoningBoundary`` for ``kind``.

        Raises:
            KeyError: if no factory is registered for ``kind``.
        """
        factory = self._factories.get(kind)
        if factory is None:
            raise KeyError(f"no agent registered for kind {kind!r}")
        return factory()

    def has(self, kind: str) -> bool:
        """Return ``True`` iff a factory is registered for ``kind``."""
        return kind in self._factories

    def kinds(self) -> list[str]:
        """Return the registered agent kinds, sorted for deterministic output."""
        return sorted(self._factories)


class _AdvanceBoundary:
    """Built-in reasoning boundary that proposes advancing a job.

    It consults the :class:`~jaros.llm.LlmClient` (``complete``) over the job
    input — the LLM decides *what* note to attach — and emits a single inert
    ``advance`` :class:`~jaros.core.decision.Decision` whose payload names the
    state-machine events that should drive the job to completion. It performs no
    side effect: its sole output is data.
    """

    def __init__(self, llm: LlmClient, source: str = "advance") -> None:
        self._llm = llm
        self._source = source

    def decide(self, context: object) -> list[Decision]:
        prompt = f"advance job: {context!r}"
        response = self._llm.complete(LlmRequest(prompt=prompt))
        decision = create_decision(
            id=f"advance-{uuid.uuid4().hex}",
            source=self._source,
            kind="advance",
            payload={"events": ["start", "complete"], "note": response.text},
        )
        return [decision]


def register_builtins(registry: AgentRegistry, llm: LlmClient) -> None:
    """Register the built-in agent kinds against ``registry`` (REQ-3).

    Registers at least the ``"advance"`` kind, whose factory returns an
    :class:`_AdvanceBoundary` that consults ``llm`` and emits an ``advance``
    decision.
    """
    registry.register("advance", lambda: _AdvanceBoundary(llm))


def load_plugins(
    registry: AgentRegistry,
    plugins_dir: str | Path,
    llm: LlmClient,
) -> list[str]:
    """Import each ``*.py`` in ``plugins_dir`` and register its declared kind.

    Each plugin module must expose a module-level ``KIND: str`` and a
    ``build(llm) -> ReasoningBoundary`` factory. For every not-yet-loaded ``*.py``
    file the module is imported via :mod:`importlib.util`, its ``KIND`` is read,
    and a factory closing over ``llm`` (calling ``module.build(llm)``) is
    registered for that kind.

    Idempotent: a module file already imported in a prior scan is skipped (tracked
    by absolute path), so repeated scans never re-import or duplicate-register.

    Returns the list of kinds newly registered by this scan (for observability).
    """
    directory = Path(plugins_dir)
    newly_registered: list[str] = []
    if not directory.is_dir():
        return newly_registered

    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue  # skip dunder/private helper modules
        key = str(path.resolve())
        if key in registry._loaded_plugins:
            continue  # already loaded in a prior scan -> idempotent

        module_name = f"jaros_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        kind = getattr(module, "KIND", None)
        build = getattr(module, "build", None)
        if not isinstance(kind, str) or not kind or not callable(build):
            # A malformed plugin is recorded as seen (so it is not retried every
            # scan) but is not registered.
            registry._loaded_plugins.add(key)
            continue

        registry.register(kind, lambda build=build: build(llm))
        registry._loaded_plugins.add(key)
        newly_registered.append(kind)

    return newly_registered
# #EXT-007-REQ-3 End
