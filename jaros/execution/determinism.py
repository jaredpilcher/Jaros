"""Executor handler determinism — the precondition behind byte-identical replay.

Byte-identical replay (EXT-002 / REQ-6) holds **because** executor handlers are
deterministic functions of the validated `Decision` plus execution-plane state.
A handler that reaches for the wall clock, a random source, or external mutable
I/O breaks that guarantee — replaying the recorded decisions would *not*
reconstruct the same state.

Jaros does not silently assume determinism; it makes the precondition
**checkable**: replaying the same decisions into fresh, isolated state must
agree. Disagreement flags a non-deterministic handler, which should be moved out
of the handler or captured as a decision (which *is* recorded and replayed).

Standard library only; no I/O of its own.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable


# #EXT-001-REQ-7 Start
def digest(value: Any) -> str:
    """Return a stable SHA-256 over a JSON-canonicalised value (repr fallback)."""
    try:
        canon = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except TypeError:
        canon = repr(value)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class NonDeterministicHandlerError(RuntimeError):
    """Raised when re-executing the same decisions yields divergent results."""


def replays_agree(replay_once: Callable[[], Any], runs: int = 2) -> bool:
    """Return ``True`` iff ``replay_once()`` yields equal artifacts across ``runs``.

    ``replay_once`` MUST perform a full replay into **fresh, isolated** state and
    return a comparable artifact (e.g. rebuilt transition-log bytes, or a list of
    output digests). Because each call is isolated, this safely detects handler
    non-determinism without corrupting live state: if two isolated replays of the
    same recorded decisions disagree, a handler is non-deterministic and the
    byte-identical guarantee does not hold for that run.
    """
    if runs < 2:
        return True
    baseline = replay_once()
    return all(replay_once() == baseline for _ in range(runs - 1))
# #EXT-001-REQ-7 End
