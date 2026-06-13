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
- ``decision``  — the accepted decision serialized as ``{id, source, kind,
  payload}`` (inert data only — EXT-001 guarantees it is JSON-serializable);
- ``checksum``  — SHA-256 over the record's canonical payload.
"""

from __future__ import annotations

import hashlib
import json
import os
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
        "kind": decision.kind,
        "payload": decision.payload,
    }


def _decision_from_dict(data: dict[str, Any]) -> Decision:
    """Rebuild a ``Decision`` from a recorded dict (re-validates serializability)."""
    return create_decision(
        id=data["id"],
        source=data["source"],
        kind=data["kind"],
        payload=data["payload"],
    )


@dataclass(frozen=True)
class DecisionRecord:
    """A single durable record of one accepted decision.

    ``checksum`` covers ``index`` and the canonical ``decision`` payload, so
    corruption of any field — or a torn final line — is detectable on replay.
    """

    index: int
    decision: dict[str, Any]
    checksum: str

    @staticmethod
    def compute_checksum(index: int, decision: dict[str, Any]) -> str:
        """Return the SHA-256 hex digest over the record's canonical payload."""
        payload = json.dumps(
            {"index": index, "decision": decision},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def make(cls, index: int, decision: dict[str, Any]) -> "DecisionRecord":
        """Build a record with a freshly-computed checksum."""
        return cls(
            index=index,
            decision=decision,
            checksum=cls.compute_checksum(index, decision),
        )

    def checksum_ok(self) -> bool:
        """Return ``True`` iff the stored checksum matches the payload."""
        return self.checksum == self.compute_checksum(self.index, self.decision)

    def to_json(self) -> str:
        """Serialise to a single canonical JSON line (no trailing newline)."""
        return json.dumps(
            {
                "index": self.index,
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

    def ensure(self) -> None:
        """Create the parent directory and an empty log file if absent (idempotent)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.flush()
                os.fsync(fh.fileno())

    def append(self, record: DecisionRecord) -> None:
        """Durably append ``record`` as one JSON line, fsync, then return."""
        self.dir.mkdir(parents=True, exist_ok=True)
        line = record.to_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

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
    """Durably append ``decision`` to ``log`` as the next ordered record.

    Returns the record written. Intended for use as the executor's ``on_accept``
    hook (EXT-001 / REQ-7), so the decision is recorded before its effects are
    observable.
    """
    next_index = log.length() + 1
    record = DecisionRecord.make(next_index, _decision_to_dict(decision))
    log.append(record)
    return record


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
