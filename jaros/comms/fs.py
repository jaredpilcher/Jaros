"""Shared file system with a fixed, validated layout (EXT-006 / REQ-2, REQ-4, REQ-6).

The shared file system is the durable exchange surface between agents. It has a
canonical layout of top-level directories; all file exchange uses
workspace-relative paths *within* that layout. Writes that try to escape the
workspace (via ``..`` traversal or absolute paths) are refused loudly with a
typed :class:`LayoutViolationError`.

It is backed by local/mounted files only — **no database or external service**
(EXT-006 / REQ-6) — keeping the zero-infrastructure tenet intact.

Canonical layout (relative to ``base_dir``)::

    state/        durable state-machine data
    inbox/        messages awaiting processing
    outbox/       messages produced for others
    artifacts/    durable work products
    agents/      agent payloads / config
    processed/    successfully handled inputs
    failed/       inputs that failed handling
"""

from __future__ import annotations

import os
from pathlib import Path

# #EXT-006-REQ-2 Start
#: The canonical top-level directories of the shared file system layout.
LAYOUT_DIRS: tuple[str, ...] = (
    "state",
    "inbox",
    "outbox",
    "artifacts",
    "agents",
    "processed",
    "failed",
)


# #EXT-006-REQ-4 Start
class LayoutViolationError(ValueError):
    """Raised when a path escapes the workspace or the layout is invalid.

    Covers both ``..`` traversal / absolute-path escapes at access time and
    structural validation failures from :meth:`SharedFileSystem.validate_layout`.
    """
# #EXT-006-REQ-4 End


class SharedFileSystem:
    """Access API for the shared file system rooted at ``base_dir``.

    All reads and writes go through :meth:`read` / :meth:`write`, which resolve
    workspace-relative paths and refuse any path that resolves outside
    ``base_dir``. Writes are atomic (temp file + ``os.replace``).
    """

    #: Re-exported so callers can reference the layout without importing the module constant.
    LAYOUT_DIRS: tuple[str, ...] = LAYOUT_DIRS

    def __init__(self, base_dir: str | os.PathLike[str]) -> None:
        self.base_dir: Path = Path(base_dir).resolve()

    def ensure_layout(self) -> None:
        """Create ``base_dir`` and every canonical layout directory.

        Idempotent: existing directories are left untouched.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for name in LAYOUT_DIRS:
            (self.base_dir / name).mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str | os.PathLike[str]) -> Path:
        """Resolve a workspace-relative ``path`` to an absolute path in base_dir.

        Raises:
            LayoutViolationError: if ``path`` is absolute or resolves (after
                ``..`` normalisation) outside ``base_dir``.
        """
        raw = Path(path)
        if raw.is_absolute():
            raise LayoutViolationError(
                f"absolute paths are not allowed: {path!r}"
            )
        candidate = (self.base_dir / raw).resolve()
        # Confine the resolved path strictly within base_dir (refuses `..` escapes).
        if candidate != self.base_dir and self.base_dir not in candidate.parents:
            raise LayoutViolationError(
                f"path escapes the workspace layout: {path!r}"
            )
        return candidate

    def read(self, path: str | os.PathLike[str]) -> str:
        """Read and return the text content of a workspace-relative ``path``.

        Raises:
            LayoutViolationError: if ``path`` escapes the workspace.
            FileNotFoundError: if the resolved file does not exist.
        """
        target = self._resolve(path)
        return target.read_text(encoding="utf-8")

    def write(self, path: str | os.PathLike[str], data: str) -> None:
        """Atomically write ``data`` to a workspace-relative ``path``.

        Parent directories within the workspace are created as needed. The write
        is atomic: data is written to a temp file in the same directory and then
        ``os.replace``-d into place.

        Raises:
            LayoutViolationError: if ``path`` escapes the workspace.
        """
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, target)

    def validate_layout(self) -> None:
        """Assert that ``base_dir`` exists and contains every layout directory.

        Raises:
            LayoutViolationError: if the base dir or any canonical directory is
                missing or is not a directory.
        """
        if not self.base_dir.is_dir():
            raise LayoutViolationError(
                f"base dir is missing or not a directory: {self.base_dir}"
            )
        for name in LAYOUT_DIRS:
            d = self.base_dir / name
            if not d.is_dir():
                raise LayoutViolationError(
                    f"missing canonical layout directory: {name!r}"
                )
# #EXT-006-REQ-2 End
