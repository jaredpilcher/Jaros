"""Durable decision log + deterministic replay (EXT-002 / REQ-6).

Reproducibility is record-and-replay of non-determinism. The only
non-deterministic input to a run is the model's output, captured as an inert,
serializable ``Decision`` (EXT-001). This module records each *accepted*
decision, in commit order, before its effects are observable, and replays the
recorded decisions through the deterministic executor — with **no model call** —
to reconstruct the run to byte-identical state. Crash recovery becomes a special
case of replay (see :func:`jaros.state.recover.recover_via_replay`).

The log is newline-delimited JSON, one record per line, durable by ``os.fsync``
on append, and tolerant of a single torn trailing line — mirroring
:class:`~jaros.state.log.TransitionLog`. Each record carries:

- ``index``     — 1-based, strictly increasing position;
- ``decision``  — the accepted decision serialized as ``{id, source, type,
  payload}`` (inert data only — EXT-001 guarantees it is JSON-serializable);
- ``checksum``  — SHA-256 over the record's canonical payload.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from jaros.core.decision import Decision, create_decision


# #EXT-002-REQ-6 Start
def _decision_to_dict(decision: Decision) -> dict[str, Any]:
    """Serialize an accepted ``Decision`` to inert JSON data."""
    return {
        "id": decision.id,
        "source": decision.source,
        "type": decision.type,
        "payload": decision.payload,
    }


def _decision_from_dict(data: dict[str, Any]) -> Decision:
    """Rebuild a ``Decision`` from a recorded dict (re-validates serializability)."""
    return create_decision(
        id=data["id"],
        source=data["source"],
        type=data["type"],
        payload=data["payload"],
    )


# The previous-checksum of the first (genesis) record: a fixed, all-zero sentinel.
GENESIS_PREV = "0" * 64


@dataclass(frozen=True)
class DecisionRecord:
    """A single durable record of one accepted decision.

    ``checksum`` covers ``index``, ``prev`` (the previous record's checksum), and
    the canonical ``decision`` payload. Including ``prev`` chains every record to
    the one before it (EXT-015 / REQ-4), so corruption of any field — or an
    insertion, deletion, reorder, or edit *anywhere* in the log — is detectable,
    not only a torn final line.
    """

    index: int
    decision: dict[str, Any]
    checksum: str
    prev: str = GENESIS_PREV

    @staticmethod
    def compute_checksum(index: int, prev: str, decision: dict[str, Any]) -> str:
        """Return the SHA-256 hex digest over the record's canonical payload."""
        payload = json.dumps(
            {"index": index, "prev": prev, "decision": decision},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def make(
        cls, index: int, decision: dict[str, Any], prev: str = GENESIS_PREV
    ) -> "DecisionRecord":
        """Build a record chained to ``prev`` with a freshly-computed checksum."""
        return cls(
            index=index,
            decision=decision,
            prev=prev,
            checksum=cls.compute_checksum(index, prev, decision),
        )

    def checksum_ok(self) -> bool:
        """Return ``True`` iff the stored checksum matches the payload + chain link."""
        return self.checksum == self.compute_checksum(
            self.index, self.prev, self.decision
        )

    def to_json(self) -> str:
        """Serialise to a single canonical JSON line (no trailing newline)."""
        return json.dumps(
            {
                "index": self.index,
                "prev": self.prev,
                "decision": self.decision,
                "checksum": self.checksum,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


class DecisionLog:
    """A durable, append-only, newline-delimited JSON decision log.

    The log lives at ``dir/filename``. It is append-only by construction: the
    only mutating operation is :meth:`append`, which opens the file in append
    mode, writes one JSON line, flushes, and ``os.fsync``s before returning.
    """

    def __init__(
        self,
        dir: str | os.PathLike[str],
        filename: str = "decisions.log",
    ) -> None:
        self.dir: Path = Path(dir)
        self.filename: str = filename
        self.path: Path = self.dir / filename
        # In-memory tail cache so appends are O(1), not O(n) (which would be O(n^2)
        # over a run — the exact cost a swarm of thousands of decisions can't pay).
        # ``read``/``verify_chain`` still do a full read (correct there); only the
        # append hot path uses the cache. Loaded lazily from disk on first use and
        # kept current on every append, under a lock so concurrent agents serialize.
        self._lock = threading.Lock()
        self._count: int | None = None
        self._last_checksum: str | None = None

    def ensure(self) -> None:
        """Create the parent directory and an empty log file if absent (idempotent)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.flush()
                os.fsync(fh.fileno())

    def _write_raw(self, record: DecisionRecord) -> None:
        """Durably write one JSON line + fsync (newline="" -> "\\n" bytes cross-OS)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        line = record.to_json() + "\n"
        with open(self.path, "a", encoding="utf-8", newline="") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def _load_tail_locked(self) -> None:
        """Populate the count + last-checksum cache from disk once (caller holds lock)."""
        if self._count is not None:
            return
        count = 0
        last = GENESIS_PREV
        for rec in self.read():
            count += 1
            last = rec.checksum
        self._count = count
        self._last_checksum = last

    def append(self, record: DecisionRecord) -> None:
        """Durably append ``record`` as one JSON line, fsync, then return.

        Thread-safe; keeps the tail cache current when it is already loaded.
        """
        with self._lock:
            self._write_raw(record)
            if self._count is not None:
                self._count += 1
                self._last_checksum = record.checksum

    def append_decision(self, decision: dict[str, Any]) -> "DecisionRecord":
        """Atomically append the next chained record in O(1) (amortized), thread-safe.

        Uses the cached tail (last checksum + count) instead of re-reading the whole
        log on every append, so a hive emitting thousands of decisions stays linear.
        Concurrent agents serialize on the lock, so the one log is a faithful,
        ordered transcript (EXT-015 / REQ-1).
        """
        with self._lock:
            self._load_tail_locked()
            assert self._count is not None
            index = self._count + 1
            prev = self._last_checksum or GENESIS_PREV
            record = DecisionRecord.make(index, decision, prev=prev)
            self._write_raw(record)
            self._count = index
            self._last_checksum = record.checksum
            return record

    def read(self) -> Iterator[DecisionRecord]:
        """Yield records in append order, tolerating a torn trailing line."""
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        if not raw:
            return
        ends_with_newline = raw.endswith("\n")
        lines = raw.split("\n")
        if ends_with_newline and lines and lines[-1] == "":
            lines.pop()
        last_index = len(lines) - 1
        for i, line in enumerate(lines):
            if line == "":
                continue
            is_torn_trailing = i == last_index and not ends_with_newline
            try:
                obj = json.loads(line)
                record = DecisionRecord(
                    index=obj["index"],
                    decision=obj["decision"],
                    checksum=obj["checksum"],
                    prev=obj.get("prev", GENESIS_PREV),
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                if is_torn_trailing:
                    continue
                continue
            yield record

    def length(self) -> int:
        """Return the number of well-formed records currently in the log."""
        return sum(1 for _ in self.read())


def record_decision(log: DecisionLog, decision: Decision) -> DecisionRecord:
    """Durably append ``decision`` to ``log`` as the next ordered, chained record.

    Returns the record written. Intended for use as the executor's ``on_accept``
    hook (EXT-001 / REQ-7), so the decision is recorded before its effects are
    observable. The new record is chained to the previous one's checksum
    (EXT-015 / REQ-4), making the per-agent account tamper-evident end-to-end.
    Appends in O(1) via the log's cached tail (no full re-read per decision).
    """
    return log.append_decision(_decision_to_dict(decision))


def read_decisions(log: DecisionLog) -> list[Decision]:
    """Return the recorded decisions in order, dropping a torn/corrupt trailing record.

    A trailing record that fails checksum or breaks index continuity is treated
    as an interrupted final append and discarded (mirroring crash recovery).
    Corruption *before* the trailing record raises :class:`ValueError`.
    """
    records = list(log.read())
    decisions: list[Decision] = []
    expected = 1
    for pos, rec in enumerate(records):
        is_last = pos == len(records) - 1
        if rec.index == expected and rec.checksum_ok():
            decisions.append(_decision_from_dict(rec.decision))
            expected += 1
            continue
        if is_last:
            break
        raise ValueError(
            f"corrupt decision record at position {pos} (index={rec.index!r})"
        )
    return decisions


# #EXT-015-REQ-4 Start
@dataclass(frozen=True)
class ChainResult:
    """Outcome of verifying the decision log's hash chain.

    ``ok`` is True iff every record's index is continuous, its checksum matches
    its payload, and its ``prev`` equals the previous record's checksum. On a
    break, ``position`` is the 1-based record index where it was detected and
    ``reason`` says what (insertion, deletion, reorder, or edit).
    """

    ok: bool
    length: int
    position: int | None = None
    reason: str | None = None


def verify_chain(log: DecisionLog) -> ChainResult:
    """Verify the log is an untampered, append-only hash chain (EXT-015 / REQ-4).

    Walks records in order confirming (1) index continuity from 1, (2) each
    record's stored checksum recomputes (no edit), and (3) each record's ``prev``
    equals the previous record's checksum (no insertion/deletion/reorder). Returns
    the first break, or ``ok=True`` over the whole log. Detection is end-to-end,
    not only a torn trailing record.
    """
    prev = GENESIS_PREV
    expected = 1
    count = 0
    for rec in log.read():
        count += 1
        if rec.index != expected:
            return ChainResult(
                False, count, expected,
                f"index discontinuity: expected {expected}, found {rec.index} "
                "(a record was inserted, deleted, or reordered)",
            )
        if not rec.checksum_ok():
            return ChainResult(False, count, expected, "record checksum mismatch (record was edited)")
        if rec.prev != prev:
            return ChainResult(
                False, count, expected,
                "broken hash chain: prev does not match the previous record "
                "(insertion, deletion, reorder, or edit upstream)",
            )
        prev = rec.checksum
        expected += 1
    return ChainResult(True, count)
# #EXT-015-REQ-4 End


def replay(
    decision_log: DecisionLog,
    apply: Callable[..., Any],
    **collaborators: Any,
) -> list[Any]:
    """Re-execute recorded decisions through the deterministic executor.

    Reads the recorded decisions in order and feeds each through ``apply`` (the
    deterministic :func:`jaros.execution.executor.apply`) with the supplied
    execution-plane ``collaborators`` — **no model call**. Returns the list of
    :class:`~jaros.execution.executor.ExecutionResult`. Because ``apply`` is a
    pure function of the decision plus collaborators, replaying the same log
    reconstructs the run to byte-identical state.

    The first parameter is named ``decision_log`` (not ``log``) so callers can
    pass a transition ``log=`` collaborator through to the handler without a
    name collision.
    """
    results: list[Any] = []
    for decision in read_decisions(decision_log):
        results.append(apply(decision, **collaborators))
    return results
# #EXT-002-REQ-6 End
