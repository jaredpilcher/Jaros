import { INITIAL_STATE, TRANSITIONS, type State } from "./model";
import type { LogEntry, TransitionLog } from "./log";
import { checksumOf } from "./log";

// #EXT-002-REQ-4 Start
/**
 * Crash recovery by log replay ([REQ-4]). After a process or node crash, the
 * current state is reconstructed deterministically by replaying the durable log
 * entries `1..N` in order. Replay is total and deterministic: the same log
 * always yields the same state.
 *
 * Torn / interrupted final commit: `TransitionLog.read()` already drops a
 * partially-written trailing line (a line with no terminating newline parses to
 * `null`). Recovery additionally validates each entry's `index` continuity and
 * `checksum`; an entry that is corrupt or out of sequence is treated as the torn
 * boundary and replay stops there, discarding it and anything after. The result
 * is the consistent state that existed immediately before the crash.
 */

/** Outcome of a recovery: the reconstructed state and how many entries applied. */
export interface RecoveryResult {
  /** The deterministically reconstructed current state. */
  readonly state: State;
  /** Number of log entries successfully replayed (the durable prefix). */
  readonly appliedCount: number;
  /** True if a torn/corrupt trailing entry was discarded during replay. */
  readonly discardedTornEntry: boolean;
}

/**
 * True when `entry` is internally consistent at the expected 1-indexed position:
 * its `index` matches, its `(from,event,to)` is a declared transition, and its
 * `checksum` matches the recomputed value. A failing entry marks the torn
 * boundary.
 */
function isEntryConsistent(entry: LogEntry, expectedIndex: number): boolean {
  if (entry.index !== expectedIndex) {
    return false;
  }
  const declaredTo = TRANSITIONS[entry.from]?.[entry.event];
  if (declaredTo === undefined || declaredTo !== entry.to) {
    return false;
  }
  return entry.checksum === checksumOf(entry.index, entry.from, entry.event, entry.to);
}

/**
 * Replay the durable log to reconstruct current state. Starts from
 * {@link INITIAL_STATE} and applies each consistent entry in order; the first
 * inconsistent (torn/corrupt/out-of-sequence) entry halts replay and is
 * discarded along with anything after it.
 */
export function recover(log: TransitionLog, initial: State = INITIAL_STATE): RecoveryResult {
  const entries = log.read();
  let state: State = initial;
  let applied = 0;
  let discardedTornEntry = false;

  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    const expectedIndex = i + 1;
    if (!isEntryConsistent(entry, expectedIndex)) {
      // Torn / interrupted boundary: discard this entry and the remainder.
      discardedTornEntry = true;
      break;
    }
    // Replay is anchored to the entry's own `from` so it is total even if the
    // supplied `initial` differs; the first entry must originate at `initial`.
    state = entry.to;
    applied++;
  }

  return { state, appliedCount: applied, discardedTornEntry };
}
// #EXT-002-REQ-4 End
