---
id: EXT-009
title: Dynamic Custom Tools and Namespaced Actions
status: partial
priority: high
implementation:
  - jaros/execution/tools.py
  - jaros/harness/capabilities.py
  - jaros/core/decision_gate.py
---

# Dynamic Custom Tools and Namespaced Actions

Supports user-defined, namespaced custom actions (tools) dropped into the watched filesystem execution plane.

### [REQ-1] Dynamic Tool Loader

The system dynamically scans, imports, and instantiates Python tool modules dropped in the shared filesystem `tools/` directory at startup.

#### Acceptance Criteria
- [ ] Tool modules are loaded dynamically without modifying core OS source files or restarting the daemon.
- [ ] If a tool module is invalid or raises an error, the error is caught, contained, and logged without crashing the daemon.

### [REQ-2] Decoupled Gate & Executor Registration

Once a tool is loaded, its `validate` and `execute` methods are dynamically registered as first-class citizens in the global validation gate and executor pipelines.

#### Acceptance Criteria
- [ ] Decisions with `type` matching the tool's `NAME` (e.g. `"db.accounts.read"`) automatically trigger the tool's custom `validate()` gate during validation.
- [ ] If validation fails, the gate rejects the decision and halts execution.
- [ ] Validated decisions are dispatched to the tool's `execute()` handler inside the pluggable executor.

### [REQ-3] Role-Based Permission Enforcer — DEPRECATED

> **DEPRECATED (PRIME-001 revision — scope honesty, P2 framing).** This
> requirement built an action-allowlist *authorization gateway*: a
> `role_permission_gate` validator that loaded `config/permissions.json`, mapped
> each agent's role to a list of permitted action namespaces, and rejected any
> decision outside that list ("Security Gate"). The revised Prime Directive is
> explicit that Jaros is **not an agent-authorization gateway or governance
> product** — "it does not compete with policy gateways (AWS Bedrock AgentCore,
> Permit.io); it is a runtime that happens to be auditable." Capability-safety in
> Jaros is **structural least-privilege** via scoped handles (EXT-005), not a
> policy-engine permission layer. The enforcer (`role_permission_gate`,
> `PolicyManager`, `config/permissions.json`) is removed by the task linked
> below. Role-to-capability *grants* remain in EXT-005 (`BUILTIN_ROLES`,
> `GrantSpec`) as structural least-privilege; only the governance-style
> action-allowlist enforcement is retired. Retained here only as the deprecation
> anchor.

Custom actions are strictly governed by the agent's role. An agent can only execute a custom action if its spawned role permits that action key in `config/permissions.json`.

#### Acceptance Criteria
- [ ] The Harness spawner associates the spawned agent with its logical role.
- [ ] A security validation gate checks if the requesting agent's role is granted the namespaced action.
- [ ] If the role does not grant the action, the gate rejects it, failing closed.

### [REQ-4] Anatomy of a Custom Tool Class

A custom tool must be a pure Python class conforming to a specific, simple signature.

#### Acceptance Criteria
- [ ] Defines a class-level `NAME` string (e.g., `"db.accounts.read"`).
- [ ] Implements `validate(self, decision: Decision) -> ValidationResult` to perform side-effect-free payload checks.
- [ ] Implements `execute(self, decision: Decision, **collaborators: Any) -> Any` to perform the actual safe host action.
