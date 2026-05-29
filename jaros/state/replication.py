"""Log replication across nodes (EXT-002 / REQ-5).

State survives the loss of any single node because every committed transition is
mirrored to more than one log before the append is acknowledged.

``ReplicatedLog`` wraps a *primary* :class:`~jaros.state.log.TransitionLog` and
zero or more *replica* sinks (also ``TransitionLog`` instances, typically
backed by distinct files/directories). Each :meth:`append` writes to the primary
and every replica before returning, so an acknowledged append exists on all
nodes. Convergence is checked by index + checksum:
:meth:`converged_prefix` returns the longest agreed prefix length,
:meth:`has_converged` reports full agreement, and :meth:`reconcile` re-applies
missing tail entries from the most-advanced log to any lagging replica.

.. note::

   This is a **single-node, file-backed stand-in** for a true multi-node
   deployment. The "replicas" are independent on-disk logs on the same host,
   not remote nodes reached over a network. It models the *semantics* of
   replication (mirror-before-ack, index+checksum convergence, no-loss on
   single-replica loss) so the rest of the system can depend on the contract;
   a production deploy would swap the file sinks for real remote peers without
   changing this interface.
"""

from __future__ import annotations

from jaros.state.log import LogEntry, TransitionLog


# #EXT-002-REQ-5 Start
class ReplicationError(RuntimeError):
    """Raised when replication cannot satisfy its mirror-before-ack contract."""


class ReplicatedLog:
    """A transition log mirrored to one or more replica sinks before ack.

    The ``primary`` is the authoritative local log; ``replicas`` are additional
    ``TransitionLog`` sinks that receive a copy of every appended entry. An
    :meth:`append` is acknowledged only after the primary *and* every replica
    have durably stored the entry.
    """

    def __init__(
        self,
        primary: TransitionLog,
        replicas: list[TransitionLog] | None = None,
    ) -> None:
        self.primary: TransitionLog = primary
        self.replicas: list[TransitionLog] = list(replicas or [])

    def add_replica(self, replica: TransitionLog) -> None:
        """Register an additional replica sink."""
        self.replicas.append(replica)

    def ensure(self) -> None:
        """Ensure the primary and every replica log file exists."""
        self.primary.ensure()
        for replica in self.replicas:
            replica.ensure()

    def append(self, entry: LogEntry) -> None:
        """Mirror ``entry`` to the primary and every replica, then acknowledge.

        Writes the primary first, then each replica, each via the underlying
        durable (fsync-ing) :meth:`TransitionLog.append`. Only after all sinks
        have stored the entry does this return — so a committed transition is
        never present on fewer than ``1 + len(replicas)`` logs.
        """
        self.primary.append(entry)
        for replica in self.replicas:
            replica.append(entry)

    def length(self) -> int:
        """Return the primary's entry count."""
        return self.primary.length()

    def _all_logs(self) -> list[TransitionLog]:
        return [self.primary, *self.replicas]

    def converged_prefix(self) -> int:
        """Return the length of the longest prefix all logs agree on.

        Two logs agree on position ``i`` iff their entries there have the same
        ``index`` and ``checksum``. The returned value is the largest ``k`` such
        that every log has identical entries for positions ``0..k-1``.
        """
        logs = self._all_logs()
        snapshots = [list(log.read()) for log in logs]
        shortest = min((len(s) for s in snapshots), default=0)
        prefix = 0
        for i in range(shortest):
            ref = snapshots[0][i]
            if all(
                snap[i].index == ref.index and snap[i].checksum == ref.checksum
                for snap in snapshots
            ):
                prefix += 1
            else:
                break
        return prefix

    def has_converged(self) -> bool:
        """Return ``True`` iff every log holds the identical entry sequence."""
        logs = self._all_logs()
        snapshots = [list(log.read()) for log in logs]
        lengths = {len(s) for s in snapshots}
        if len(lengths) != 1:
            return False
        return self.converged_prefix() == lengths.pop()

    def reconcile(self) -> None:
        """Bring every log up to the most-advanced log's full sequence.

        Picks the log with the longest valid (checksum-passing, index-continuous)
        entry sequence as the source of truth and appends any missing tail
        entries to every other log. This models recovery of a replica that
        missed appends (e.g. it was the node that was briefly lost) — after a
        :meth:`reconcile` the logs :meth:`has_converged`.

        Raises:
            ReplicationError: if logs diverge on an already-shared position
                (a genuine conflict that simple tail-append cannot reconcile).
        """
        logs = self._all_logs()
        snapshots = [list(log.read()) for log in logs]

        # Source of truth: the longest sequence.
        source_idx = max(range(len(logs)), key=lambda i: len(snapshots[i]))
        source = snapshots[source_idx]

        # Detect genuine conflicts on shared positions before mutating anything.
        for snap in snapshots:
            for i in range(min(len(snap), len(source))):
                if (
                    snap[i].index != source[i].index
                    or snap[i].checksum != source[i].checksum
                ):
                    raise ReplicationError(
                        f"divergent entry at position {i}; cannot reconcile by "
                        "tail-append"
                    )

        for log, snap in zip(logs, snapshots):
            for entry in source[len(snap):]:
                log.append(entry)
# #EXT-002-REQ-5 End
