"""The lightweight agent thread (EXT-003 / REQ-1, REQ-4).

An :class:`AgentThread` runs an agent body on a plain :class:`threading.Thread`
— no socket, no port, no server, no per-agent deployment. Spawning allocates
only an in-process thread; teardown joins it and releases the handle
deterministically and idempotently.

Fault containment is structural: the body is wrapped so that any unhandled
exception is caught, the agent is moved to ``failed`` with the error recorded,
the ``on_failed`` callback is fired, and nothing propagates out of the thread to
crash the process or disturb sibling agents.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable

from jaros.core.decision import Decision
from jaros.runtime.lifecycle import AgentState

# The agent body: a callable that does the agent's reasoning and may return a
# list of inert decisions (EXT-001). It performs no side effects directly.
AgentBody = Callable[[], "list[Decision] | None"]
FailureHook = Callable[["AgentThread", BaseException], None]


# #EXT-003-REQ-1 Start
# #EXT-003-REQ-4 Start
@dataclass
class AgentThread:
    """A single agent hosted on an in-process thread.

    Attributes:
        id: Stable identifier for this agent.
        body: The agent body executed once by :meth:`run`.
        on_failed: Optional hook fired (with this thread and the exception) when
            the body raises; the failure is contained, never propagated.
        state: Current lifecycle state.
        decisions: Inert decisions emitted by the body (captured on success).
        error: The contained exception, if the agent failed.
    """

    id: str
    body: AgentBody
    on_failed: FailureHook | None = None
    state: AgentState = AgentState.SPAWNED
    decisions: list[Decision] = field(default_factory=list)
    error: BaseException | None = None
    _thread: threading.Thread | None = field(default=None, repr=False)
    _torndown: bool = field(default=False, repr=False)

    @staticmethod
    def spawn(
        id: str,
        body: AgentBody,
        on_failed: FailureHook | None = None,
    ) -> "AgentThread":
        """Build an :class:`AgentThread` and allocate its (unstarted) thread.

        Allocates only a lightweight in-process thread — no network service,
        container, or port. The returned agent is in state ``spawned``.
        """
        agent = AgentThread(id=id, body=body, on_failed=on_failed)
        agent._thread = threading.Thread(
            target=agent.run, name=f"agent-{id}", daemon=True
        )
        return agent

    def start(self) -> None:
        """Start the underlying thread (runs :meth:`run` once)."""
        if self._thread is None:
            self._thread = threading.Thread(
                target=self.run, name=f"agent-{self.id}", daemon=True
            )
        self._thread.start()

    def run(self) -> None:
        """Execute the agent body exactly once, containing any failure.

        On success the agent ends in ``done`` and emitted decisions are captured.
        On an unhandled exception the agent ends in ``failed``, the error is
        recorded, and ``on_failed`` is fired — the exception never escapes this
        method, so the process and sibling agents survive.
        """
        self.state = AgentState.RUNNING
        try:
            emitted = self.body()
        except BaseException as exc:  # contain *everything*; never crash the process
            self.error = exc
            self.state = AgentState.FAILED
            if self.on_failed is not None:
                try:
                    self.on_failed(self, exc)
                except BaseException:
                    # A faulty hook must not itself crash the runtime.
                    pass
            return
        if emitted:
            self.decisions = list(emitted)
        self.state = AgentState.DONE

    def teardown(self) -> None:
        """Join the thread and release its handle. Idempotent.

        Deterministically reaps the thread and drops the reference. Safe to call
        repeatedly and regardless of whether the agent finished or failed; a
        never-started agent is simply marked ``torndown``.
        """
        if self._torndown:
            return
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join()
        self._thread = None
        self._torndown = True
        # Preserve a terminal failure outcome; otherwise mark cleanly reaped.
        if self.state != AgentState.FAILED:
            self.state = AgentState.TORNDOWN
# #EXT-003-REQ-4 End
# #EXT-003-REQ-1 End
