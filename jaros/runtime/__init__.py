"""Agent Thread Runtime (EXT-003).

Runs AI agents as lightweight in-process threads — cheap to spawn, cheap to tear
down, many at once — never as per-agent services. Owns the agent lifecycle, a
bounded observable pool, and fault containment.
"""

from __future__ import annotations

from jaros.runtime.agent_pool import AgentFactory, AgentPool, AgentSnapshot
from jaros.runtime.agent_thread import AgentBody, AgentThread, FailureHook
from jaros.runtime.lifecycle import AgentState, RunnableAgent

__all__ = [
    "AgentState",
    "RunnableAgent",
    "AgentThread",
    "AgentBody",
    "FailureHook",
    "AgentPool",
    "AgentFactory",
    "AgentSnapshot",
]
