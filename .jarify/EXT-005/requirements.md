---
id: EXT-005
title: Architectural Harness
status: partial
priority: high
implementation:
  - jaros/harness/capabilities.py
  - jaros/harness/rules.py
  - jaros/harness/harness.py
  - jaros/harness/__init__.py
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

### [REQ-5] Developer-Configurable Rule Set

Developers/operators can configure or extend the rule set when constructing the harness (boot time), without modifying core code — but agents still cannot change it at runtime. Configuration is a harness-side privilege; mutation by agents remains forbidden (see REQ-2).

#### Acceptance Criteria
- [ ] The `Harness` accepts a rule set (or rule overrides/extensions) at construction; absent any, it falls back to the built-in default rules.
- [ ] A developer can add or tighten a rule via this configuration path without editing harness internals.
- [ ] The configured rule set is frozen after construction; there is no agent-reachable API to mutate it at runtime (fails closed), and `describe_rules()` reflects the active configured set.

### [REQ-6] Capability-Safety Framing and Host Security Boundary

Capability scoping is **structural least-privilege** for correctness and
blast-radius control — *not* an adversarial sandbox against hostile code sharing
the interpreter. The directive ([PRIME-001 / P2] and the "is not" boundary) is
explicit: real isolation against hostile code is the **host's** job (process,
container, VPC). This requirement makes that framing load-bearing so the harness
neither markets nor relies on its in-process guards as an adversarial security
boundary.

#### Acceptance Criteria
- [ ] The harness's documentation and module/docstring language describe
      capability scoping as structural least-privilege and blast-radius control,
      and name the host (process/container/VPC) as the isolation boundary against
      hostile code.
- [ ] No spec text, docstring, or comment in the harness layer asserts that
      in-process guards stop a determined adversary sharing the interpreter
      (purge "sandbox"/"unbreakable"/"secure against hostile code" claims framed
      as adversarial).
- [ ] The guarantees the harness *does* claim — default-deny mediation, no
      ambient authority, an auditable record of every mediated action — remain
      enforced (REQ-1…REQ-5) and are stated as correctness/auditability
      properties, not as an adversarial sandbox.
