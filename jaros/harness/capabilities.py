"""Capability/handle model for the Architectural Harness (EXT-005 / REQ-3, REQ-6).

Agents hold no ambient power. They receive only the specific, scoped handles the
harness grants them; those handles wrap the underlying :class:`~jaros.comms.queue.Queue`
and :class:`~jaros.comms.fs.SharedFileSystem` so an agent can never reach the raw
modules, other queues, other paths, or the network.

Security boundary (EXT-005 / REQ-6): capability scoping here is **structural
least-privilege** for correctness and blast-radius control — a bug or bad
decision cannot touch what it was never granted. It is *not* an adversarial
sandbox against hostile code sharing the interpreter; real isolation against
hostile code is the host's job (process, container, VPC).

A capability is a small, frozen descriptor (``QueueSend``, ``QueueReceive``,
``FsWrite``, ``FsRead``). A :class:`GrantSpec` bundles the capabilities a single
agent is allowed, together with the concrete backing objects. :func:`grant`
turns a spec into a frozen :class:`Grants` bundle of scoped handles; :func:`revoke`
invalidates them so any subsequent use raises :class:`RevokedCapabilityError`
*before* any side effect occurs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jaros.comms.fs import SharedFileSystem
    from jaros.comms.queue import Queue


# #EXT-005-REQ-3 Start
class CapabilityError(Exception):
    """Base class for capability/handle errors."""


class RevokedCapabilityError(CapabilityError):
    """Raised when a revoked handle is used, before any side effect occurs."""


# --- Capability kinds -------------------------------------------------------
#
# Each capability kind is a frozen marker describing one permitted action class.
# They are deliberately tiny and immutable: agents may hold references to them
# but can neither mutate them nor manufacture new powers from them.


@dataclass(frozen=True, slots=True)
class QueueSend:
    """Capability to enqueue onto a specific queue."""

    name: str = "queue.send"


@dataclass(frozen=True, slots=True)
class QueueReceive:
    """Capability to dequeue/peek from a specific queue."""

    name: str = "queue.receive"


@dataclass(frozen=True, slots=True)
class FsWrite:
    """Capability to write to the shared file system."""

    name: str = "fs.write"


@dataclass(frozen=True, slots=True)
class FsRead:
    """Capability to read from the shared file system."""

    name: str = "fs.read"


Capability = QueueSend | QueueReceive | FsWrite | FsRead


# --- Scoped handles ---------------------------------------------------------
#
# Handles are the *only* objects an agent ever touches. They wrap the backing
# queue/fs, expose a minimal surface, honour revocation, and are frozen so the
# agent cannot swap out the backing object or otherwise reach the raw module.


class _RevocableHandle:
    """Mixin providing frozen attributes + a shared revocation flag.

    A handle is frozen after construction (``__setattr__``/``__delattr__`` raise)
    so an agent cannot rebind ``_backing`` to a different queue/fs or clear the
    revocation flag. Revocation flips a one-element mutable list shared with the
    owning :class:`Grants` bundle, so revoking the bundle revokes every handle.
    """

    _frozen: bool = False

    def _check_live(self) -> None:
        # ``_revoked`` is a single-element list shared across a bundle.
        if self._revoked[0]:
            raise RevokedCapabilityError(
                f"capability handle has been revoked: {type(self).__name__}"
            )

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_frozen", False):
            raise CapabilityError(
                f"capability handles are frozen; cannot set {name!r}"
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise CapabilityError("capability handles are frozen; cannot delete attributes")


class QueueSendHandle(_RevocableHandle):
    """Scoped send-only view of a backing :class:`~jaros.comms.queue.Queue`."""

    def __init__(self, backing: Queue[Any], revoked: list[bool]) -> None:
        object.__setattr__(self, "_backing", backing)
        object.__setattr__(self, "_revoked", revoked)
        object.__setattr__(self, "_frozen", True)

    def send(self, msg: Any) -> None:
        self._check_live()
        self._backing.enqueue(msg)


class QueueReceiveHandle(_RevocableHandle):
    """Scoped receive-only view of a backing :class:`~jaros.comms.queue.Queue`."""

    def __init__(self, backing: Queue[Any], revoked: list[bool]) -> None:
        object.__setattr__(self, "_backing", backing)
        object.__setattr__(self, "_revoked", revoked)
        object.__setattr__(self, "_frozen", True)

    def receive(self) -> Any:
        self._check_live()
        return self._backing.dequeue()

    def peek(self) -> Any:
        self._check_live()
        return self._backing.peek()


class FsWriteHandle(_RevocableHandle):
    """Scoped write-only view of a backing :class:`~jaros.comms.fs.SharedFileSystem`."""

    def __init__(self, backing: SharedFileSystem, revoked: list[bool]) -> None:
        object.__setattr__(self, "_backing", backing)
        object.__setattr__(self, "_revoked", revoked)
        object.__setattr__(self, "_frozen", True)

    def write(self, path: str, data: str) -> None:
        self._check_live()
        self._backing.write(path, data)


class FsReadHandle(_RevocableHandle):
    """Scoped read-only view of a backing :class:`~jaros.comms.fs.SharedFileSystem`."""

    def __init__(self, backing: SharedFileSystem, revoked: list[bool]) -> None:
        object.__setattr__(self, "_backing", backing)
        object.__setattr__(self, "_revoked", revoked)
        object.__setattr__(self, "_frozen", True)

    def read(self, path: str) -> str:
        self._check_live()
        return self._backing.read(path)


# --- Grant spec + bundle ----------------------------------------------------

#: Mapping of role names to their permitted capability types.
BUILTIN_ROLES: dict[str, tuple[type[Capability], ...]] = {
    "AdminRole": (FsRead, FsWrite, QueueSend, QueueReceive),
    "AnalystRole": (FsRead,),
    "ReporterRole": (FsWrite, QueueSend),
    "GuestRole": (FsRead,),
    "QueueSendRole": (QueueSend,),
    "QueueReceiveRole": (QueueReceive,),
    "FsWriteRole": (FsWrite,),
    "FsReadRole": (FsRead,),
    "FsRole": (FsRead, FsWrite),
}


@dataclass(frozen=True, slots=True)
class GrantSpec:
    """Declarative request for the capabilities a single agent should hold under a role.

    The harness (never the agent) supplies this. It names the role the agent
    is assigned to, and the concrete backing objects to scope them to.
    """

    role: str
    queue: Queue[Any] | None = None
    fs: SharedFileSystem | None = None

    def has(self, cap_type: type) -> bool:
        caps = BUILTIN_ROLES.get(self.role, ())
        return cap_type in caps


@dataclass(frozen=True, slots=True)
class Grants:
    """Immutable bundle of the scoped handles an agent actually holds.

    Only the handles populated here are reachable by the agent. ``_revoked`` is
    the shared revocation flag; :func:`revoke` flips it, invalidating every
    handle at once. The agent never receives a reference to the raw queue/fs.
    """

    queue_send: QueueSendHandle | None = None
    queue_receive: QueueReceiveHandle | None = None
    fs_write: FsWriteHandle | None = None
    fs_read: FsReadHandle | None = None
    role: str = ""
    _revoked: list[bool] = field(default_factory=lambda: [False])

    @property
    def revoked(self) -> bool:
        return self._revoked[0]


def grant(spec: GrantSpec) -> Grants:
    """Produce a frozen :class:`Grants` bundle of scoped handles from ``spec``.

    Only capabilities named in ``spec`` (and backed by a supplied queue/fs)
    yield a handle; everything else is ``None`` and thus unreachable.

    Raises:
        CapabilityError: if a capability is requested without its backing object.
    """
    revoked: list[bool] = [False]

    queue_send = queue_receive = fs_write = fs_read = None

    if spec.has(QueueSend):
        if spec.queue is None:
            raise CapabilityError("QueueSend requires a backing queue")
        queue_send = QueueSendHandle(spec.queue, revoked)
    if spec.has(QueueReceive):
        if spec.queue is None:
            raise CapabilityError("QueueReceive requires a backing queue")
        queue_receive = QueueReceiveHandle(spec.queue, revoked)
    if spec.has(FsWrite):
        if spec.fs is None:
            raise CapabilityError("FsWrite requires a backing file system")
        fs_write = FsWriteHandle(spec.fs, revoked)
    if spec.has(FsRead):
        if spec.fs is None:
            raise CapabilityError("FsRead requires a backing file system")
        fs_read = FsReadHandle(spec.fs, revoked)

    return Grants(
        queue_send=queue_send,
        queue_receive=queue_receive,
        fs_write=fs_write,
        fs_read=fs_read,
        role=spec.role,
        _revoked=revoked,
    )


def revoke(grants: Grants) -> None:
    """Invalidate every handle in ``grants``.

    After this returns, any use of any handle raises
    :class:`RevokedCapabilityError` before performing a side effect. Idempotent.
    """
    grants._revoked[0] = True
# #EXT-005-REQ-3 End
