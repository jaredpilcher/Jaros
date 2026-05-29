"""Agent lifecycle vocabulary for the Agent Thread Runtime (EXT-003 / REQ-1).

An agent is a lightweight in-process unit with a cheap spawn/run/teardown
lifecycle — never a service. This module defines the state vocabulary every
agent moves through and a *structural* :class:`RunnableAgent` Protocol that the
runtime depends on. The Protocol is deliberately neutral (no textual dependency
on any concrete ``agent*`` module): the pool and thread only ever rely on this
interface, so the no-server / comms checks stay satisfied.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable


# #EXT-003-REQ-1 Start
class AgentState(str, Enum):
    """The states an agent moves through during its lifecycle.

    ``spawned -> running -> (done | failed) -> torndown``. A failure is a
    terminal run outcome that is still torn down cleanly and reported.
    """

    SPAWNED = "spawned"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    TORNDOWN = "torndown"


@runtime_checkable
class RunnableAgent(Protocol):
    """Structural interface the runtime depends on to host an agent.

    The runtime never imports a concrete agent class; it only requires that an
    object expose this shape. ``run()`` executes the agent body once; ``teardown()``
    releases its resources deterministically and is safe to call more than once.
    """

    id: str
    state: AgentState

    def run(self) -> None:
        """Execute the agent body exactly once."""
        ...

    def teardown(self) -> None:
        """Release all resources deterministically (idempotent)."""
        ...
# #EXT-003-REQ-1 End
