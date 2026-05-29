// #EXT-002-REQ-1 Start
/**
 * The explicit state and transition model — the single source of truth for the
 * distributed state machine ([REQ-1]). The set of valid states and the set of
 * allowed `(state, event) -> nextState` transitions are declared here, in one
 * place, and never inferred by scattered application logic. Every other module
 * (enforcement, log, recovery, replication) consults this table; none invents
 * its own transitions.
 *
 * The model is deliberately introspectable: {@link listTransitions} flattens the
 * table into `(from, event, to)` triples so it can be dumped, audited, or
 * visualized (e.g. rendered to a graph).
 */

/** The enumerated set of declared states. The machine may never hold any other. */
export const STATES = ["PENDING", "RUNNING", "DONE", "FAILED"] as const;

/** A declared state. */
export type State = (typeof STATES)[number];

/** The enumerated set of events that may drive a transition. */
export const EVENTS = ["START", "COMPLETE", "FAIL", "RETRY"] as const;

/** An event that may drive a transition. */
export type Event = (typeof EVENTS)[number];

/**
 * The explicit transition table mapping `(state, event) -> nextState`. A pair
 * that is absent here is, by definition, not a permitted transition. This is the
 * single source of truth consulted by `transition()` in `./machine`.
 */
export const TRANSITIONS: Record<State, Partial<Record<Event, State>>> = {
  PENDING: { START: "RUNNING", FAIL: "FAILED" },
  RUNNING: { COMPLETE: "DONE", FAIL: "FAILED" },
  FAILED: { RETRY: "PENDING" },
  DONE: {},
};

/** The conventional initial state for a freshly created machine. */
export const INITIAL_STATE: State = "PENDING";

/** A single flattened transition: from a state, on an event, to a next state. */
export interface TransitionTriple {
  readonly from: State;
  readonly event: Event;
  readonly to: State;
}

/** True when `value` is one of the declared {@link STATES}. */
export function isState(value: unknown): value is State {
  return typeof value === "string" && (STATES as readonly string[]).includes(value);
}

/** True when `value` is one of the declared {@link EVENTS}. */
export function isEvent(value: unknown): value is Event {
  return typeof value === "string" && (EVENTS as readonly string[]).includes(value);
}

/**
 * Flatten {@link TRANSITIONS} into an ordered array of `(from, event, to)`
 * triples for visualization and audit. The order is deterministic (declaration
 * order of states, then events) so dumps are stable.
 */
export function listTransitions(): TransitionTriple[] {
  const triples: TransitionTriple[] = [];
  for (const from of STATES) {
    const byEvent = TRANSITIONS[from];
    for (const event of EVENTS) {
      const to = byEvent[event];
      if (to !== undefined) {
        triples.push({ from, event, to });
      }
    }
  }
  return triples;
}
// #EXT-002-REQ-1 End
