"""Bounded multi-node coordination over the shared file system (EXT-002 / REQ-7).

Jaros is single-node-first. Where more than one node participates, they
coordinate — claiming and handing off work — entirely over the shared file
system, with **no consensus service, message broker, or network client**. This
keeps the zero-infrastructure tenet intact (P3) and the scope honest (P4): there
is no cluster-scale replication layer, only files.

The single-node configuration runs with **zero coordination overhead**: claims
always succeed and touch no disk, because there is no contention. Multi-node
coordination uses an atomic ``O_CREAT | O_EXCL`` claim file per unit of work
under ``state/claims/`` — the filesystem itself is the arbiter.
"""

from __future__ import annotations

import os
from pathlib import Path


# #EXT-002-REQ-7 Start
class FileCoordinator:
    """Claim/hand-off coordination over the shared file system.

    Args:
        fs_base: Root of the shared file system layout (the daemon's data dir).
        node_id: Identifier for this node, written into the claim file.
        single_node: When ``True`` (default), coordination is a zero-overhead
            no-op — claims always succeed and no files are written. Set ``False``
            to enable bounded multi-node coordination over the shared FS.
    """

    def __init__(
        self,
        fs_base: str | os.PathLike[str],
        node_id: str = "node-1",
        *,
        single_node: bool = True,
    ) -> None:
        self.claims_dir: Path = Path(fs_base) / "state" / "claims"
        self.node_id = node_id
        self.single_node = single_node

    def try_claim(self, work_id: str) -> bool:
        """Atomically claim ``work_id`` for this node.

        Returns ``True`` if this node now owns the claim, ``False`` if another
        node already holds it. In single-node mode this is a zero-overhead no-op
        that always returns ``True`` (no contention is possible).
        """
        if self.single_node:
            return True
        self.claims_dir.mkdir(parents=True, exist_ok=True)
        path = self.claims_dir / f"{work_id}.claim"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(self.node_id)
            fh.flush()
            os.fsync(fh.fileno())
        return True

    def owner(self, work_id: str) -> str | None:
        """Return the node id that holds ``work_id``'s claim, or ``None``.

        In single-node mode the sole node owns everything, so this returns
        :attr:`node_id`.
        """
        if self.single_node:
            return self.node_id
        path = self.claims_dir / f"{work_id}.claim"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip() or None

    def release(self, work_id: str) -> None:
        """Release this node's claim on ``work_id`` so another node may take it.

        Idempotent and a no-op in single-node mode.
        """
        if self.single_node:
            return
        path = self.claims_dir / f"{work_id}.claim"
        try:
            path.unlink()
        except FileNotFoundError:
            pass
# #EXT-002-REQ-7 End
