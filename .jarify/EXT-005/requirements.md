---
id: EXT-005
title: Architectural Harness
status: uncovered
priority: high
implementation: []
---

# Architectural Harness

The unyielding mediator every agent runs inside. The harness — not the agents — defines and enforces the rules: it grants capabilities, validates every action, and cannot be bypassed at runtime. Realizes Prime Directive tenet [PRIME-001 / REQ-5].

### [REQ-1] Mediated Agent Actions

Every action an agent takes is mediated by the harness and validated before it has any effect.

#### Acceptance Criteria
- [ ] Agents perform side effects only by requesting them through the harness.
- [ ] The harness validates each requested action against its rules before allowing it.
- [ ] Disallowed actions are refused and reported; they cause no effect.

### [REQ-2] Non-Bypassable Constraints

Agents cannot weaken, redefine, or circumvent the harness's constraints at runtime.

#### Acceptance Criteria
- [ ] Harness rules are not mutable by agent code at runtime.
- [ ] There is no agent-reachable path that performs a side effect without harness mediation.
- [ ] Attempts to bypass the harness fail closed (denied by default).

### [REQ-3] Capability-Scoped I/O Handles

Agents receive only the specific handles the harness grants them. They have no ambient access to queues, the file system, or the network.

#### Acceptance Criteria
- [ ] An agent is constructed with an explicit, minimal set of harness-granted handles.
- [ ] Agents have no access to global/ambient I/O (queues, fs, network) outside granted handles.
- [ ] Granted capabilities are revocable by the harness on teardown.

### [REQ-4] Architecturally-Defined Rules

Harness rules are defined in code/configuration, never negotiated by agents.

#### Acceptance Criteria
- [ ] The rule set is declared in the harness layer (code/config), not supplied by agents.
- [ ] Changing a rule is a harness-side change, reviewable independently of agents.
- [ ] The active rule set is introspectable for audit.
