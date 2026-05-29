import { isState, TRANSITIONS, type Event, type State } from "./model";
import type { LogEntry, TransitionLog } from "./log";

// #EXT-002-REQ-2 Start
/**
 * Transition enforcement ([REQ-2]). Only transitions present in the explicit
 * model (`./model`) are permitted; every other `(state, event)` pair is rejected
 * with a typed {@link UndefinedTransitionError} and causes no mutation. The
 * machine can therefore never enter a state outside the declared set.
 */

/**
 * Typed error raised when `transition()` is asked for a `(state, event)` pair
 * that is not declared in {@link TRANSITIONS}. Carrying the offending pair lets
 * callers diagnose without parsing the message.
 */
export class UndefinedTransitionError extends Error {
  readonly state: State;
  readonly event: Event;

  constructor(state: State, event: Event) {
    super(`No transition declared for state "${state}" on event "${event}".`);
    this.name = "UndefinedTransitionError";
    this.state = state;
    this.event = event;
    Object.setPrototypeOf(this, UndefinedTransitionError.prototype);
  }
}

/**
 * Typed error raised when an invariant is violated: the machine is observed
 * holding a value that is not one of the declared {@link State}s. This should be
 * impossible in normal operation and indicates corruption.
 */
export class InvalidStateError extends Error {
  readonly value: unknown;

  constructor(value: unknown) {
    super(`Value "${String(value)}" is not a declared state.`);
    this.name = "InvalidStateError";
    this.value = value;
    Object.setPrototypeOf(this, InvalidStateError.prototype);
  }
}

/**
 * Invariant check: assert `value` is one of the declared states. Used on entry
 * and exit of {@link transition} so an undeclared state can never propagate.
 * Throws {@link InvalidStateError} otherwise.
 */
export function assertValidState(value: unknown): asserts value is State {
  if (!isState(value)) {
    throw new InvalidStateError(value);
  }
}

/**
 * Pure transition function. Returns the next state iff `(state, event)` exists in
 * {@link TRANSITIONS}; otherwise throws {@link UndefinedTransitionError} and
 * performs no mutation. The invariant is asserted on the incoming state and on
 * the computed next state.
 */
export function transition(state: State, event: Event): State {
  assertValidState(state);
  const next = TRANSITIONS[state][event];
  if (next === undefined) {
    throw new UndefinedTransitionError(state, event);
  }
  assertValidState(next);
  return next;
}
// #EXT-002-REQ-2 End

// #EXT-002-REQ-3 Start
/**
 * Atomic commit ([REQ-3]). Validate the transition, then append it to the
 * durable log, then apply it. The transition becomes observable only after the
 * append succeeds: if the append throws, the new state is NOT applied and the
 * error propagates — either the transition is both logged and applied, or
 * neither.
 *
 * @returns the new state together with the persisted log entry.
 */
export function commit(
  log: TransitionLog,
  state: State,
  event: Event
): { state: State; entry: LogEntry } {
  // 1. Validate (no mutation, no I/O on rejection).
  const next = transition(state, event);
  // 2. Durably append BEFORE applying. A throw here leaves caller state intact.
  const entry = log.append({ from: state, event, to: next });
  // 3. Only now is the transition observable.
  return { state: next, entry };
}
// #EXT-002-REQ-3 End
