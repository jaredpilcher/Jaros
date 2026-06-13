# Implementation Tasks — Architectural Harness

### [TASK-1] Implement the capability/handle model

Give agents only explicitly granted, revocable handles — no ambient I/O.

#### Steps
1. Create `jaros/harness/capabilities.py` defining capability kinds (`QueueSend`, `QueueReceive`, `FsWrite`, `FsRead`), a `Grants` bundle, a `GrantSpec`, and `grant(spec)`/`revoke(grants)` that produce/invalidate SCOPED handles wrapping the underlying `Queue`/`SharedFileSystem`.
2. Make revoked handles raise `RevokedCapabilityError` before any side effect; freeze granted handles so agents cannot reach raw modules.

#### Implements
- [REQ-3] Capability-Scoped I/O Handles

### [TASK-2] Implement harness mediation and rule validation

Route every agent action through validation; fail closed.

#### Steps
1. Create `jaros/harness/harness.py` with a `Harness` whose `request(agent_id, action)` validates `action` against the active rules and performs it only via granted handles.
2. Make validation default-deny: unknown/disallowed actions are refused and recorded, with no side effect; add `spawn(agent_id, grant_spec) -> AgentContext` giving the agent only its `Grants` (no global queue/fs/network refs) and `teardown(agent_id)` revoking them.

#### Implements
- [REQ-1] Mediated Agent Actions
- [REQ-2] Non-Bypassable Constraints

### [TASK-3] Declare and expose the architectural rule set

Define rules in the harness layer and make them auditable.

#### Steps
1. Create `jaros/harness/rules.py` exporting the rule set (mapping action types to required capabilities) as code, deep-frozen at import, with no agent-facing mutation API.
2. Add `describe_rules()` returning a snapshot for audit; add a test asserting agent code cannot mutate the rule set at runtime.

#### Implements
- [REQ-4] Architecturally-Defined Rules

### [TASK-4] Make the rule set developer-configurable at construction

Let developers configure/extend rules at boot without editing core, while keeping them agent-immutable.

#### Steps
1. In `jaros/harness/harness.py`, have `Harness.__init__` accept an optional `rules` (or `rule_overrides`) parameter; when omitted, fall back to the built-in default rules from `jaros/harness/rules.py`.
2. Deep-freeze the resulting rule set after construction so there is no agent-reachable mutation path; `describe_rules()` reflects the configured set.
3. Add a test constructing a `Harness` with an extra/tighter rule and asserting it is enforced, plus a test that agent code still cannot mutate the configured rules at runtime.

#### Implements
- [REQ-5] Developer-Configurable Rule Set

### [TASK-5] Reframe harness capability language as least-privilege, not a sandbox

Align harness docs and docstrings with the directive: structural least-privilege
and blast-radius control, with the host as the security boundary.

#### Steps
1. In `jaros/harness/harness.py` and `jaros/harness/capabilities.py`, revise module/class docstrings to describe scoped handles as structural least-privilege + blast-radius control, and add a short "Security boundary" note stating that isolation against hostile code is delegated to the host (process/container/VPC).
2. Remove or qualify any "sandbox"/"unbreakable"/"secure against hostile code" phrasing that implies an adversarial in-process boundary; keep default-deny/fail-closed described as correctness + auditability properties.
3. Grep `jaros/harness/**` for `sandbox`, `unbreakable`, and `secure` and confirm remaining uses are framed as least-privilege/auditability, not adversarial isolation.

#### Implements
- [REQ-6] Capability-Safety Framing and Host Security Boundary
