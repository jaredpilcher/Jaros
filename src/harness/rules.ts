import type { CapabilityKind } from "./capabilities";

// #EXT-005-REQ-4 Start
/**
 * Architecturally-defined rule set.
 *
 * The rules are declared *here*, in the harness layer, as code/config — never
 * supplied or negotiated by agents. Changing a rule is a harness-side edit to
 * this file, reviewable independently of any agent. The active set is exposed
 * (read-only) through {@link describeRules} for audit/introspection.
 *
 * A rule maps an action `type` to the single capability required to perform it.
 * The harness (`./harness`) consults this map to decide, default-deny, whether
 * a requested action is permitted and which granted handle must carry it out.
 */

/** The canonical action types the harness knows how to perform. */
export type ActionType =
  | "queue.send"
  | "queue.receive"
  | "fs.write"
  | "fs.read";

/** A single architectural rule: an action type and the capability it needs. */
export interface Rule {
  readonly action: ActionType;
  readonly requires: CapabilityKind;
  readonly description: string;
}

/**
 * The active rule set. `readonly` arrays/objects and a deep freeze at module
 * load make this immutable: agent code holding the exported value cannot add,
 * remove, or rewrite a rule at runtime (see {@link describeRules}).
 */
const RULES: readonly Rule[] = Object.freeze([
  Object.freeze({
    action: "queue.send",
    requires: "QueueSend",
    description: "Enqueue a message onto the agent's granted send queue.",
  }),
  Object.freeze({
    action: "queue.receive",
    requires: "QueueReceive",
    description: "Dequeue a message from the agent's granted receive queue.",
  }),
  Object.freeze({
    action: "fs.write",
    requires: "FsWrite",
    description: "Write a file under the agent's granted shared file system.",
  }),
  Object.freeze({
    action: "fs.read",
    requires: "FsRead",
    description: "Read a file under the agent's granted shared file system.",
  }),
]) as readonly Rule[];

/** Lookup index, built once, frozen — also not agent-mutable. */
const RULE_INDEX: ReadonlyMap<ActionType, Rule> = new Map(
  RULES.map((r) => [r.action, r])
);

/**
 * Resolve the rule for an action type, or `undefined` if no rule permits it.
 * An absent rule means default-deny in the harness.
 */
export function ruleFor(action: string): Rule | undefined {
  return RULE_INDEX.get(action as ActionType);
}

/**
 * Return the active rule set for audit/introspection. The result is a fresh,
 * deep-frozen snapshot: callers (including agent code) may read it but any
 * attempt to mutate it is a no-op (frozen) and never affects the real rules,
 * which are private to this module.
 */
export function describeRules(): readonly Rule[] {
  return Object.freeze(RULES.map((r) => Object.freeze({ ...r })));
}
// #EXT-005-REQ-4 End
