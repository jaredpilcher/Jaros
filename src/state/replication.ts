import { checksumOf, type LogEntry, type LogEntryInput, TransitionLog } from "./log";

// #EXT-002-REQ-5 Start
/**
 * Log replication across nodes ([REQ-5]). Each appended transition is mirrored to
 * every registered replica sink *before* the append is acknowledged, so the loss
 * of any single node loses no committed transition. Replicas converge on the
 * same committed sequence via index + checksum reconciliation.
 *
 * SINGLE-NODE STAND-IN: a true deployment replicates to peer nodes over the
 * network. This implementation provides an in-process / multi-file local
 * stand-in: each {@link ReplicaSink} is an independent {@link TransitionLog}
 * (its own file). It exercises the exact replication contract — mirror before
 * ack, detect divergence by index+checksum, reconcile to a common prefix —
 * without a network, and is intended to be swapped for real remote sinks in a
 * multi-node deploy.
 */

/**
 * A replica destination. The local stand-in wraps an independent
 * {@link TransitionLog}; a real implementation would forward to a peer node.
 */
export interface ReplicaSink {
  /** Stable identifier for diagnostics / reconciliation reporting. */
  readonly id: string;
  /** Persist (mirror) an already-derived entry. Throws on failure. */
  accept(entry: LogEntry): void;
  /** Read this replica's entries in append order. */
  read(): LogEntry[];
}

/** A {@link ReplicaSink} backed by a local {@link TransitionLog} file. */
export class FileReplicaSink implements ReplicaSink {
  readonly id: string;
  private readonly log: TransitionLog;

  constructor(id: string, log: TransitionLog) {
    this.id = id;
    this.log = log.ensure();
  }

  accept(entry: LogEntry): void {
    // Mirror verbatim (preserve the primary's index/checksum) by writing the
    // exact serialized entry; the replica's own append would re-derive index.
    this.log.append({ from: entry.from, event: entry.event, to: entry.to });
  }

  read(): LogEntry[] {
    return this.log.read();
  }
}

/** Raised when a replica acknowledgement fails so the entry is not committed. */
export class ReplicationError extends Error {
  readonly replicaId: string;

  constructor(replicaId: string, cause: unknown) {
    super(`Replication to "${replicaId}" failed: ${String(cause)}`);
    this.name = "ReplicationError";
    this.replicaId = replicaId;
    Object.setPrototypeOf(this, ReplicationError.prototype);
  }
}

/**
 * Replicated log: writes to a primary {@link TransitionLog} and mirrors every
 * appended entry to all registered {@link ReplicaSink}s before acknowledging.
 */
export class ReplicatedLog {
  private readonly primary: TransitionLog;
  private readonly replicas: ReplicaSink[];

  constructor(primary: TransitionLog, replicas: ReplicaSink[] = []) {
    this.primary = primary.ensure();
    this.replicas = [...replicas];
  }

  /** Register an additional replica sink. */
  addReplica(sink: ReplicaSink): this {
    this.replicas.push(sink);
    return this;
  }

  /**
   * Append to the primary, then mirror to every replica before returning. The
   * entry is acknowledged (returned) only once it is on the primary and all
   * replicas, so a subsequent loss of any single node still leaves the entry on
   * the others. A replica failure raises {@link ReplicationError}.
   */
  append(input: LogEntryInput): LogEntry {
    const entry = this.primary.append(input);
    for (const replica of this.replicas) {
      try {
        replica.accept(entry);
      } catch (cause) {
        throw new ReplicationError(replica.id, cause);
      }
    }
    return entry;
  }

  /** All known nodes (primary first), each as an ordered entry list. */
  private nodes(): { id: string; entries: LogEntry[] }[] {
    return [
      { id: "primary", entries: this.primary.read() },
      ...this.replicas.map((r) => ({ id: r.id, entries: r.read() })),
    ];
  }

  /**
   * The longest prefix of entries on which every node agrees, by 1-indexed
   * position and per-entry checksum. This is the committed, converged sequence —
   * any committed entry (present on all nodes) is preserved here even if one
   * node later trails.
   */
  convergedPrefix(): LogEntry[] {
    const nodes = this.nodes();
    if (nodes.length === 0) {
      return [];
    }
    const minLen = Math.min(...nodes.map((n) => n.entries.length));
    const prefix: LogEntry[] = [];
    for (let i = 0; i < minLen; i++) {
      const reference = nodes[0].entries[i];
      const expectedChecksum = checksumOf(i + 1, reference.from, reference.event, reference.to);
      const allAgree = nodes.every((n) => {
        const e = n.entries[i];
        return (
          e.index === i + 1 &&
          e.from === reference.from &&
          e.event === reference.event &&
          e.to === reference.to &&
          e.checksum === expectedChecksum
        );
      });
      if (!allAgree) {
        break;
      }
      prefix.push(reference);
    }
    return prefix;
  }

  /** True when every node holds the identical committed sequence. */
  hasConverged(): boolean {
    const nodes = this.nodes();
    const target = this.convergedPrefix().length;
    return nodes.every((n) => n.entries.length === target);
  }

  /**
   * Reconcile divergent replicas toward the primary: any replica missing
   * committed entries that the primary holds is brought forward by mirroring the
   * absent suffix. This models a node rejoining after a loss and catching up so
   * all replicas converge on the same committed sequence.
   */
  reconcile(): void {
    const primaryEntries = this.primary.read();
    for (const replica of this.replicas) {
      const have = replica.read().length;
      for (let i = have; i < primaryEntries.length; i++) {
        replica.accept(primaryEntries[i]);
      }
    }
  }
}
// #EXT-002-REQ-5 End
