"""Rigid, typed message queue (EXT-006 / REQ-1, REQ-4, REQ-6).

Agents never call each other; they exchange work through queues governed by a
rigid, typed message contract. Every message is schema-validated *before* it is
stored, so a contract violation is rejected at enqueue time and never reaches a
consumer.

This queue is a plain in-process structure: it requires and contacts **no
external message broker or queue service** (EXT-006 / REQ-6) — the comms-layer
half of the zero-infrastructure tenet.

Semantics (explicitly specified):

- **Ordering**: strict FIFO. Messages are dequeued in the order they were
  enqueued.
- **Delivery**: at-least-once. ``dequeue`` removes and returns the head; if a
  consumer crashes after receiving but before durably acting, the message is
  gone from this in-memory queue, but the contract documents at-least-once so
  consumers must be idempotent. (No exactly-once guarantee is offered.)
- **Durability**: none. This is an in-memory queue; contents do not survive
  process restart. Durable exchange is the job of the shared file system
  (``jaros.comms.fs``).
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


# #EXT-006-REQ-4 Start
class QueueContractError(ValueError):
    """Raised when a message violates the queue's typed contract at enqueue.

    The offending message is rejected *before* storage, so a violating message
    is never observable by a consumer.
    """
# #EXT-006-REQ-4 End


# #EXT-006-REQ-1 Start
class Queue(Generic[T]):
    """A rigid, typed FIFO queue with enqueue-time contract validation.

    The queue is parameterised by a ``validator`` callable that enforces the
    message contract. ``enqueue`` runs the validator first and raises
    :class:`QueueContractError` on any violation, *before* the message is stored
    — guaranteeing only contract-valid messages are ever delivered.

    Semantics: in-memory, strict FIFO ordering, at-least-once delivery,
    non-durable (see module docstring).
    """

    def __init__(self, validator: Callable[[T], bool] | None = None) -> None:
        """Create a queue.

        Args:
            validator: Callable applied to each message at enqueue time. It may
                either return ``False`` / a falsy value to signal a contract
                violation, or raise its own exception (which is wrapped in a
                :class:`QueueContractError`). If ``None``, all messages are
                accepted.
        """
        self._validator = validator
        self._items: deque[T] = deque()

    def enqueue(self, msg: T) -> None:
        """Validate ``msg`` against the contract, then append it (FIFO tail).

        Raises:
            QueueContractError: if the message violates the contract. The
                message is not stored when this is raised.
        """
        if self._validator is not None:
            try:
                ok = self._validator(msg)
            except QueueContractError:
                raise
            except Exception as exc:  # validator signalled a violation by raising
                raise QueueContractError(
                    f"message rejected by contract validator: {exc}"
                ) from exc
            if not ok:
                raise QueueContractError(
                    f"message rejected by contract validator: {msg!r}"
                )
        self._items.append(msg)

    def dequeue(self) -> T:
        """Remove and return the head of the queue (FIFO).

        Raises:
            IndexError: if the queue is empty.
        """
        if not self._items:
            raise IndexError("dequeue from an empty queue")
        return self._items.popleft()

    def peek(self) -> T:
        """Return the head of the queue without removing it.

        Raises:
            IndexError: if the queue is empty.
        """
        if not self._items:
            raise IndexError("peek from an empty queue")
        return self._items[0]

    def __len__(self) -> int:
        return len(self._items)
# #EXT-006-REQ-1 End
