"""Tests for the rigid typed queue (EXT-006 / REQ-1, REQ-4)."""

from __future__ import annotations

import pytest

from jaros.comms.queue import Queue, QueueContractError


def _is_task_message(msg: object) -> bool:
    """A minimal rigid contract: a dict with str 'kind' and str 'payload'."""
    return (
        isinstance(msg, dict)
        and isinstance(msg.get("kind"), str)
        and isinstance(msg.get("payload"), str)
    )


def test_fifo_ordering():
    q: Queue[int] = Queue()
    for n in (1, 2, 3):
        q.enqueue(n)
    assert [q.dequeue(), q.dequeue(), q.dequeue()] == [1, 2, 3]


def test_peek_does_not_remove():
    q: Queue[str] = Queue()
    q.enqueue("a")
    q.enqueue("b")
    assert q.peek() == "a"
    assert len(q) == 2
    assert q.dequeue() == "a"


def test_enqueue_rejects_contract_violation_not_stored():
    q: Queue[dict] = Queue(validator=_is_task_message)
    q.enqueue({"kind": "work", "payload": "do-it"})
    with pytest.raises(QueueContractError):
        q.enqueue({"kind": "work"})  # missing payload -> violation
    # The violating message must not have been stored.
    assert len(q) == 1
    assert q.dequeue() == {"kind": "work", "payload": "do-it"}


def test_validator_raising_is_wrapped():
    def strict(msg: object) -> bool:
        raise ValueError("nope")

    q: Queue[int] = Queue(validator=strict)
    with pytest.raises(QueueContractError):
        q.enqueue(1)
    assert len(q) == 0


def test_dequeue_empty_raises():
    q: Queue[int] = Queue()
    with pytest.raises(IndexError):
        q.dequeue()


def test_peek_empty_raises():
    q: Queue[int] = Queue()
    with pytest.raises(IndexError):
        q.peek()
