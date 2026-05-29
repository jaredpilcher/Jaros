# Implementation Tasks — Architectural Harness

### [TASK-1] Implement the capability/handle model

Give agents only explicitly granted, revocable handles — no ambient I/O.

#### Steps
1. Create `src/harness/capabilities.ts` defining `Capability` types (e.g., `QueueSend`, `FsWrite`) and a `Grants` bundle of capabilities.
2. Implement `grant(spec)` and `revoke(grants)` in `capabilities.ts` that produce/invalidate scoped handles.
3. Ensure granted handles wrap the underlying queue/fs APIs so agents cannot reach the raw modules directly.

#### Implements
- [REQ-3] Capability-Scoped I/O Handles

### [TASK-2] Implement harness mediation and rule validation

Route every agent action through validation; fail closed.

#### Steps
1. Create `src/harness/harness.ts` with `request(agentId, action)` that validates `action` against the active rules and performs it only via granted handles.
2. Make validation default-deny: unknown or disallowed actions are refused and reported, with no side effect.
3. Spawn agents in `harness.ts` with only their `Grants`, passing no global queue/fs/network references.

#### Implements
- [REQ-1] Mediated Agent Actions
- [REQ-2] Non-Bypassable Constraints

### [TASK-3] Declare and expose the architectural rule set

Define rules in the harness layer and make them auditable.

#### Steps
1. Create `src/harness/rules.ts` exporting the rule set as code/config consumed by `harness.ts`; agents have no API to mutate it.
2. Add `describeRules()` in `rules.ts` returning the active rules for audit/introspection.
3. Add `src/harness/rules.test.ts` asserting agent code cannot alter the rule set at runtime.

#### Implements
- [REQ-4] Architecturally-Defined Rules
