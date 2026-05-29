"""Durable, append-only transition log (EXT-002 / REQ-3).

Every accepted transition is persisted here *before* it is observable. The log
is newline-delimited JSON, one entry per line. Each entry carries:

- ``index``  — 1-based, strictly increasing per-entry position;
- ``event``  — the event that drove the transition;
- ``state``  — the resulting state after applying the event;
- ``checksum`` — a SHA-256 over the entry's canonical payload, used by recovery
  to detect a torn/corrupt trailing line.

Durability: :meth:`append` writes the line, ``flush``es, and ``os.fsync``s the
file descriptor before returning, so an acknowledged append has hit stable
storage. The API is strictly append-only — there is no update or delete.
:meth:`read` yields entries in order and tolerates a single torn trailing line
(a partially-written final entry from an interrupted append), which it silently
skips rather than raising.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# #EXT-002-REQ-3 Start
@dataclass(frozen=True)
class LogEntry:
    """A single durable transition record.

    ``checksum`` covers ``index``, ``event``, and ``state`` so corruption of any
    field — or a torn final line — is detectable during recovery.
    """

    index: int
    event: str
    state: str
    checksum: str

    @staticmethod
    def compute_checksum(index: int, event: str, state: str) -> str:
        """Return the SHA-256 hex digest over the entry's canonical payload."""
        payload = json.dumps(
            {"index": index, "event": event, "state": state},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def make(cls, index: int, event: str, state: str) -> "LogEntry":
        """Build an entry with a freshly-computed checksum."""
        return cls(
            index=index,
            event=event,
            state=state,
            checksum=cls.compute_checksum(index, event, state),
        )

    def checksum_ok(self) -> bool:
        """Return ``True`` iff the stored checksum matches the payload."""
        return self.checksum == self.compute_checksum(
            self.index, self.event, self.state
        )

    def to_json(self) -> str:
        """Serialise to a single canonical JSON line (no trailing newline)."""
        return json.dumps(
            {
                "index": self.index,
                "event": self.event,
                "state": self.state,
                "checksum": self.checksum,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


class TransitionLog:
    """A durable, append-only, newline-delimited JSON transition log.

    The log lives at ``dir/filename``. It is append-only by construction: the
    only mutating operation is :meth:`append`, which opens the file in append
    mode, writes one JSON line, flushes, and ``os.fsync``s before returning.
    """

    def __init__(
        self,
        dir: str | os.PathLike[str],
        filename: str = "transitions.log",
    ) -> None:
        self.dir: Path = Path(dir)
        self.filename: str = filename
        self.path: Path = self.dir / filename

    def ensure(self) -> None:
        """Create the parent directory and an empty log file if absent.

        Idempotent: an existing log is left untouched.
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.flush()
                os.fsync(fh.fileno())

    def append(self, entry: LogEntry) -> None:
        """Durably append ``entry`` as one JSON line, fsync, then return.

        The write is flushed and ``os.fsync``-d before returning so that a
        successful return means the entry is on stable storage. Append-only:
        no existing line is ever modified.
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        line = entry.to_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def read(self) -> Iterator[LogEntry]:
        """Yield entries in append order, tolerating a torn trailing line.

        A final line without a terminating newline is treated as a torn write
        from an interrupted append and is skipped. A trailing line that is
        non-empty but un-parseable as JSON is likewise skipped (only the *last*
        line may be torn; earlier garbage is not expected and is also skipped
        defensively). Earlier well-formed entries are always yielded.
        """
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        if not raw:
            return
        # Split keeping track of whether the file ends with a newline. A final
        # fragment that is not newline-terminated is a torn trailing write.
        ends_with_newline = raw.endswith("\n")
        lines = raw.split("\n")
        # split() leaves a trailing "" when the text ends with "\n"; drop it.
        if ends_with_newline and lines and lines[-1] == "":
            lines.pop()
        last_index = len(lines) - 1
        for i, line in enumerate(lines):
            if line == "":
                continue
            is_torn_trailing = i == last_index and not ends_with_newline
            try:
                obj = json.loads(line)
                entry = LogEntry(
                    index=obj["index"],
                    event=obj["event"],
                    state=obj["state"],
                    checksum=obj["checksum"],
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                # A torn trailing line is expected and tolerated; skip it.
                if is_torn_trailing:
                    continue
                # Defensive: skip other unparseable lines rather than crash.
                continue
            yield entry

    def length(self) -> int:
        """Return the number of well-formed entries currently in the log."""
        return sum(1 for _ in self.read())
# #EXT-002-REQ-3 End
