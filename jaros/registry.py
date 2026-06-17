"""Runtime agent registry + agent loading (EXT-007 / REQ-3).

The registry maps an agent ``name`` to a factory that produces a
:class:`~jaros.core.reasoning_boundary.ReasoningBoundary`. Built-in agents are
registered at boot via :func:`register_builtins`; new agent modules dropped into
the shared-FS ``agents/`` directory are imported and registered at runtime via
:func:`load_agents` — no daemon restart required.

An agent module declares a module-level ``NAME: str`` (the agent's name — the
value a job's ``agent`` field selects) and a ``build(llm)`` factory returning a
``ReasoningBoundary``. :func:`load_agents` is idempotent across re-scans: a
module file is imported and registered exactly once.

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

# A factory builds a fresh ReasoningBoundary for a resolved agent name. Built-in
# factories may close over the shared LlmClient; agent factories receive it.
AgentBoundaryFactory = Callable[[], ReasoningBoundary]


# #EXT-007-REQ-3 Start
class AgentRegistry:
    """Maps an agent ``name`` to a factory producing a ``ReasoningBoundary``.

    The registry is the single lookup the daemon consults to turn an inbox job's
    ``agent`` field into a runnable reasoning boundary.
    """

    def __init__(self) -> None:
        self._factories: dict[str, AgentBoundaryFactory] = {}
        # Absolute paths of agent files already imported, so re-scans are
        # idempotent (an agent is loaded + registered exactly once).
        self._loaded_agents: set[str] = set()

    def register(self, name: str, factory: AgentBoundaryFactory) -> None:
        """Register ``factory`` as the producer for the agent called ``name``.

        Re-registering a name replaces the prior factory (last-writer-wins),
        which keeps agent reloads well-defined.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("agent name must be a non-empty string")
        self._factories[name] = factory

    def resolve(self, name: str) -> ReasoningBoundary:
        """Build and return a fresh ``ReasoningBoundary`` for the agent ``name``.

        Raises:
            KeyError: if no agent is registered under ``name``.
        """
        factory = self._factories.get(name)
        if factory is None:
            raise KeyError(f"no agent registered with name {name!r}")
        return factory()

    def has(self, name: str) -> bool:
        """Return ``True`` iff an agent is registered under ``name``."""
        return name in self._factories

    def names(self) -> list[str]:
        """Return the registered agent names, sorted for deterministic output."""
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
            type="advance",
            payload={"events": ["start", "complete"], "note": response.text},
        )
        return [decision]


def register_builtins(registry: AgentRegistry, llm: LlmClient) -> None:
    """Register the built-in agents against ``registry`` (REQ-3).

    Registers at least the ``"advance"`` agent, whose factory returns an
    :class:`_AdvanceBoundary` that consults ``llm`` and emits an ``advance``
    decision. (The built-in agent's *name* and the decision *type* it emits are
    both ``"advance"`` — distinct concepts that happen to share a label.)
    """
    registry.register("advance", lambda: _AdvanceBoundary(llm))


def load_agents(
    registry: AgentRegistry,
    agents_dir: str | Path,
    llm: LlmClient,
) -> list[str]:
    """Import each ``*.py`` in ``agents_dir`` and register its declared name.

    Each agent module must expose a module-level ``NAME: str`` and a
    ``build(llm) -> ReasoningBoundary`` factory. For every not-yet-loaded ``*.py``
    file the module is imported via :mod:`importlib.util`, its ``NAME`` is read,
    and a factory closing over ``llm`` (calling ``module.build(llm)``) is
    registered under that name.

    Idempotent: a module file already imported in a prior scan is skipped (tracked
    by absolute path), so repeated scans never re-import or duplicate-register.

    Returns the list of agent names newly registered by this scan (for observability).
    """
    directory = Path(agents_dir)
    newly_registered: list[str] = []
    if not directory.is_dir():
        return newly_registered

    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue  # skip dunder/private helper modules
        key = str(path.resolve())
        if key in registry._loaded_agents:
            continue  # already loaded in a prior scan -> idempotent

        module_name = f"jaros_agent_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        name = getattr(module, "NAME", None)
        build = getattr(module, "build", None)
        if not isinstance(name, str) or not name or not callable(build):
            # A malformed agent is recorded as seen (so it is not retried every
            # scan) but is not registered.
            registry._loaded_agents.add(key)
            continue

        registry.register(name, lambda build=build: build(llm))
        registry._loaded_agents.add(key)
        newly_registered.append(name)

    return newly_registered
# #EXT-007-REQ-3 End
