"""Communication Fabric (EXT-006).

The only two sanctioned inter-agent channels: rigid typed queues and a shared
file system with a fixed layout. No direct agent-to-agent calls exist.
"""

from __future__ import annotations

from jaros.comms.fs import (
    LAYOUT_DIRS,
    LayoutViolationError,
    SharedFileSystem,
)
from jaros.comms.queue import Queue, QueueContractError

__all__ = [
    "Queue",
    "QueueContractError",
    "SharedFileSystem",
    "LayoutViolationError",
    "LAYOUT_DIRS",
]
