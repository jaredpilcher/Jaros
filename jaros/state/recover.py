"""Crash recovery by deterministic log replay (EXT-002 / REQ-4).

After a process or node crash, current state is reconstructed by replaying the
durable transition log in order. Replay is deterministic and total: the final
``state`` field of the last *valid* entry is the recovered current state.

Validation during replay:

- **Index continuity** — entries must be numbered ``1, 2, 3, ...`` with no gap.
- **Checksum** — each entry's stored checksum must match its payload.

A torn/corrupt *trailing* entry (a partially-written final append, or a final
entry that fails checksum / breaks index continuity) is discarded, yielding the
consistent pre-crash state. Corruption *before* the trailing entry indicates a
non-recoverable log and raises :class:`RecoveryError`.
"""

from __future__ import annotations

from jaros.state.log import LogEntry, TransitionLog
from jaros.state.machine import assert_valid_state
from jaros.state.model import INITIAL_STATE, STATES


# #EXT-002-REQ-4 Start
class RecoveryError(ValueError):
    """Raised when the log is corrupt in a way replay cannot safely recover."""


def recover(log: TransitionLog) -> str:
    """Replay ``log`` to reconstruct the current state.

    Reads entries in order (``read`` already drops a torn trailing *line*),
    validates index continuity and per-entry checksums, discards a single
    corrupt/torn trailing entry, and returns the resulting state. An empty (or
    fully-discarded) log recovers to :data:`INITIAL_STATE`.

    Returns:
        str: the recovered current state.

    Raises:
        RecoveryError: if corruption is detected before the trailing entry
            (i.e. the log is not safely recoverable).
    """
    entries: list[LogEntry] = list(log.read())

    valid: list[LogEntry] = []
    expected_index = 1
    for pos, entry in enumerate(entries):
        is_last = pos == len(entries) - 1
        index_ok = entry.index == expected_index
        checksum_ok = entry.checksum_ok()
        state_ok = isinstance(entry.state, str) and entry.state in STATES

        if index_ok and checksum_ok and state_ok:
            valid.append(entry)
            expected_index += 1
            continue

        # Corruption. Tolerated only if this is the trailing entry (a torn /
        # interrupted final commit); otherwise the log is unrecoverable.
        if is_last:
            break
        raise RecoveryError(
            f"corrupt log entry at position {pos} (index={entry.index!r}): "
            f"index_ok={index_ok} checksum_ok={checksum_ok} state_ok={state_ok}"
        )

    state = valid[-1].state if valid else INITIAL_STATE
    # Final invariant: recovered state must be a declared state.
    return assert_valid_state(state)
# #EXT-002-REQ-4 End
