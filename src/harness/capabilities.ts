import { Queue } from "../comms/queue";
import { SharedFileSystem } from "../comms/fs";

// #EXT-005-REQ-3 Start
/**
 * Capability-scoped I/O handles.
 *
 * An agent never receives a raw `Queue` or `SharedFileSystem`. Instead the
 * harness mints narrow, revocable *handles* — each handle exposes exactly one
 * verb (send / receive / write / read) bound to one underlying resource. The
 * agent holds the handle, not the resource, so it has no path back to the raw
 * module, sibling queues, or other file-system paths.
 *
 * Capabilities are *revocable*: on teardown the harness calls {@link revoke},
 * after which every granted handle fails closed — any use throws a
 * {@link RevokedCapabilityError} and performs no side effect.
 */

/** The four capability kinds an agent can be granted. */
export type CapabilityKind =
  | "QueueSend"
  | "QueueReceive"
  | "FsWrite"
  | "FsRead";

/** Raised when a handle is used after its grants have been revoked. */
export class RevokedCapabilityError extends Error {
  /** The capability kind that was attempted after revocation. */
  readonly capability: CapabilityKind;

  constructor(capability: CapabilityKind) {
    super(
      `Capability "${capability}" has been revoked; the handle can no longer be used.`
    );
    this.name = "RevokedCapabilityError";
    this.capability = capability;
    Object.setPrototypeOf(this, RevokedCapabilityError.prototype);
  }
}

/** A handle that lets an agent enqueue onto exactly one queue. */
export interface QueueSendHandle {
  readonly kind: "QueueSend";
  send(msg: unknown): void;
}

/** A handle that lets an agent dequeue from exactly one queue. */
export interface QueueReceiveHandle {
  readonly kind: "QueueReceive";
  receive(): Promise<unknown>;
}

/** A handle that lets an agent write under exactly one shared file system. */
export interface FsWriteHandle {
  readonly kind: "FsWrite";
  write(relativePath: string, data: string): void;
}

/** A handle that lets an agent read under exactly one shared file system. */
export interface FsReadHandle {
  readonly kind: "FsRead";
  read(relativePath: string): string;
}

/** Union of every handle type an agent may hold. */
export type CapabilityHandle =
  | QueueSendHandle
  | QueueReceiveHandle
  | FsWriteHandle
  | FsReadHandle;

/**
 * The minimal bundle of handles an agent is constructed with. Any absent field
 * means the agent has *no* access to that capability — there is no ambient
 * fallback to a global queue/fs/network.
 */
export interface Grants {
  readonly queueSend?: QueueSendHandle;
  readonly queueReceive?: QueueReceiveHandle;
  readonly fsWrite?: FsWriteHandle;
  readonly fsRead?: FsReadHandle;
}

/**
 * Declarative request for capabilities, naming the underlying resources to bind
 * each handle to. The harness owns the resources; the agent only names which of
 * the *offered* capabilities it should receive.
 */
export interface GrantSpec {
  /** Bind a send handle to this queue. */
  readonly queueSend?: Queue<unknown>;
  /** Bind a receive handle to this queue. */
  readonly queueReceive?: Queue<unknown>;
  /** Bind write/read handles to this shared file system. */
  readonly fs?: SharedFileSystem;
  /** Which fs verbs to grant when `fs` is supplied (default: none). */
  readonly fsWrite?: boolean;
  readonly fsRead?: boolean;
}

/**
 * A {@link Grants} bundle plus the means to revoke it. The harness keeps the
 * `revoke` function private to itself; agents only ever see {@link Grants}.
 */
export interface RevocableGrants {
  readonly grants: Grants;
  /** Invalidate every handle in the bundle. Idempotent. */
  revoke(): void;
}

/**
 * Mint a {@link RevocableGrants} bundle from a {@link GrantSpec}.
 *
 * Each requested handle closes over a shared `revoked` flag; once {@link revoke}
 * flips it, every handle throws {@link RevokedCapabilityError} on use before
 * touching the underlying resource. Handles wrap the resource so the agent can
 * never reach the raw `Queue`/`SharedFileSystem` instance.
 */
export function grant(spec: GrantSpec): RevocableGrants {
  const state = { revoked: false };

  const guard = (kind: CapabilityKind): void => {
    if (state.revoked) {
      throw new RevokedCapabilityError(kind);
    }
  };

  const grants: {
    queueSend?: QueueSendHandle;
    queueReceive?: QueueReceiveHandle;
    fsWrite?: FsWriteHandle;
    fsRead?: FsReadHandle;
  } = {};

  if (spec.queueSend) {
    const q = spec.queueSend;
    grants.queueSend = Object.freeze({
      kind: "QueueSend" as const,
      send(msg: unknown): void {
        guard("QueueSend");
        q.enqueue(msg);
      },
    });
  }

  if (spec.queueReceive) {
    const q = spec.queueReceive;
    grants.queueReceive = Object.freeze({
      kind: "QueueReceive" as const,
      async receive(): Promise<unknown> {
        guard("QueueReceive");
        return q.dequeue();
      },
    });
  }

  if (spec.fs && spec.fsWrite) {
    const fs = spec.fs;
    grants.fsWrite = Object.freeze({
      kind: "FsWrite" as const,
      write(relativePath: string, data: string): void {
        guard("FsWrite");
        fs.write(relativePath, data);
      },
    });
  }

  if (spec.fs && spec.fsRead) {
    const fs = spec.fs;
    grants.fsRead = Object.freeze({
      kind: "FsRead" as const,
      read(relativePath: string): string {
        guard("FsRead");
        return fs.read(relativePath);
      },
    });
  }

  const frozen = Object.freeze(grants);

  return {
    grants: frozen,
    revoke(): void {
      state.revoked = true;
    },
  };
}

/**
 * Convenience wrapper to revoke a {@link RevocableGrants} bundle. After this,
 * every handle in the bundle fails closed.
 */
export function revoke(grants: RevocableGrants): void {
  grants.revoke();
}
// #EXT-005-REQ-3 End
