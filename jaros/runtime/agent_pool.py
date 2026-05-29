"""The bounded, observable concurrent agent pool (EXT-003 / REQ-2, REQ-4).

The pool hosts many agents at once but never more than a configurable ``bound``
running concurrently. When the bound is reached, further spawn requests are
*queued* (backpressure) rather than allowed to grow unbounded; queued work is
admitted as running slots free up.

The pool is observable: :meth:`active` enumerates running agents and
:meth:`snapshot` reports every agent's id + state. Faults are contained per
:class:`~jaros.runtime.agent_thread.AgentThread`: a failing agent is reported via
``on_agent_failed`` while its siblings keep running, and :meth:`drain` reaps
everything deterministically.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import Callable

from jaros.runtime.agent_thread import AgentThread, FailureHook
from jaros.runtime.lifecycle import AgentState

# A factory produces a fresh agent on demand. The pool installs its own failure
# hook around the agent, so factories need not wire one up themselves.
AgentFactory = Callable[[], AgentThread]


@dataclass(frozen=True)
class AgentSnapshot:
    """An observable (id, state) pair for one agent."""

    id: str
    state: AgentState


# #EXT-003-REQ-2 Start
# #EXT-003-REQ-4 Start
class AgentPool:
    """A bounded pool of concurrently running agent threads.

    Args:
        bound: Maximum number of agents running concurrently (must be >= 1).
        on_agent_failed: Optional hook fired with ``(agent, exception)`` when a
            hosted agent's body raises. Failures are contained; siblings and the
            pool keep running.
    """

    def __init__(
        self,
        bound: int,
        on_agent_failed: FailureHook | None = None,
    ) -> None:
        if bound < 1:
            raise ValueError("bound must be >= 1")
        self._bound = bound
        self._on_agent_failed = on_agent_failed
        self._lock = threading.RLock()
        self._running: dict[str, AgentThread] = {}
        self._queue: deque[AgentFactory] = deque()
        # Every agent the pool has admitted, retained for observability/draining.
        self._known: list[AgentThread] = []

    @property
    def bound(self) -> int:
        """The configured maximum number of concurrently running agents."""
        return self._bound

    @property
    def pending(self) -> int:
        """Number of spawn requests queued behind the bound (backpressure)."""
        with self._lock:
            return len(self._queue)

    def submit(self, factory: AgentFactory) -> None:
        """Submit an agent factory for execution.

        If a running slot is free the agent is spawned immediately; otherwise the
        request is queued and admitted later as slots free (backpressure — the
        pool never exceeds ``bound`` concurrently running agents).
        """
        with self._lock:
            if len(self._running) < self._bound:
                self._spawn(factory)
            else:
                self._queue.append(factory)

    def active(self) -> list[AgentThread]:
        """Return the agents currently running (a snapshot list)."""
        with self._lock:
            return list(self._running.values())

    def snapshot(self) -> list[AgentSnapshot]:
        """Return an (id, state) snapshot of every agent the pool has admitted."""
        with self._lock:
            return [AgentSnapshot(id=a.id, state=a.state) for a in self._known]

    def drain(self) -> None:
        """Run all queued work to completion and tear down every agent.

        Repeatedly admits queued factories as slots free, joins each running
        agent, and tears it down deterministically. Returns once nothing is
        running and the backlog is empty.
        """
        while True:
            with self._lock:
                running = list(self._running.values())
                pending = len(self._queue)
            if not running and pending == 0:
                break
            for agent in running:
                agent.teardown()  # joins; _reap (via the hook below) frees the slot
        # Every admitted agent has finished; tear each down so its handle is
        # released deterministically and its terminal state is recorded (an
        # agent reaped between drain passes may still need its teardown call).
        with self._lock:
            known = list(self._known)
        for agent in known:
            agent.teardown()

    # --- internals ----------------------------------------------------------

    def _spawn(self, factory: AgentFactory) -> None:
        """Build an agent from ``factory``, wire reaping, and start it.

        Caller must hold ``self._lock``.
        """
        agent = factory()
        # Wrap any user failure hook so the pool both reports and reaps on fault.
        user_hook = agent.on_failed

        def _on_failed(a: AgentThread, exc: BaseException) -> None:
            if user_hook is not None:
                user_hook(a, exc)
            if self._on_agent_failed is not None:
                self._on_agent_failed(a, exc)

        agent.on_failed = _on_failed
        # Reap when the body finishes (success or contained failure) to free the
        # slot and admit queued work, without the caller having to join. The
        # thread targets the wrapper directly so reaping is guaranteed even if
        # the factory pre-created a thread bound to the bare ``run``.
        wrapped = self._wrap_run(agent)
        thread = threading.Thread(
            target=wrapped, name=f"agent-{agent.id}", daemon=True
        )
        object.__setattr__(agent, "_thread", thread)

        self._running[agent.id] = agent
        self._known.append(agent)
        thread.start()

    def _wrap_run(self, agent: AgentThread) -> Callable[[], None]:
        """Return a run wrapper that reaps the agent once its body returns."""
        original_run = AgentThread.run

        def _run() -> None:
            try:
                original_run(agent)
            finally:
                self._reap(agent.id)

        return _run

    def _reap(self, agent_id: str) -> None:
        """Free the slot held by ``agent_id`` and admit one queued factory."""
        with self._lock:
            self._running.pop(agent_id, None)
            if self._queue and len(self._running) < self._bound:
                self._spawn(self._queue.popleft())
# #EXT-003-REQ-4 End
# #EXT-003-REQ-2 End
