# Design — Dynamic Custom Tools and Namespaced Actions

Architectural context, system flows, and design specifications for dynamically registering and executing custom host actions.

## System Flows

The dynamic tooling system allows operators to plug new code into the Execution Plane. Each tool registers its own deterministic `validate()`/`execute()` into the gate and executor; capability-safety remains structural least-privilege via harness-granted handles (EXT-005), not a policy-engine permission layer.

> **Note (PRIME-001 revision):** the role-based permission *enforcer* described
> below (the `role_permission_gate` and `config/permissions.json` action
> allowlist) is **deprecated and removed** — Jaros is not an
> agent-authorization/governance product. The validation flow below now ends at
> the tool's own `validate()`; the "Check role permission" step is gone.

```text
Host System (Execution Plane)                   Daemon Sandbox (Execution Plane)
┌───────────────────────────┐                   ┌──────────────────────────────┐
│  plugins/tools/           │                   │  Dynamic Tool Registry       │
│  └─ account_reader.py    ─┼──(Boot Scan)─────►│  - Maps "db.accounts.read"   │
└───────────────────────────┘                   │  - Instantiates reader tool  │
                                                └──────────────┬───────────────┘
                                                               │
                                                       (Wires up hooks)
                                                               │
                                                               ▼
Reasoning Plane (Non-Deterministic)             Validation & Execution Gates
┌───────────────────────────┐                   ┌──────────────────────────────┐
│  Agent Thread (decide)    │                   │  Validation Gate             │
│  └─ Emits Decision JSON   │                   │  1. Check role permission    │
│     kind: db.accounts.read│                   │  2. Run tool.validate()      │
└─────────────┬─────────────┘                   └──────────────┬───────────────┘
              │                                                │
       (Decisions JSON)                                   (Accepted)
              │                                                │
              ▼                                                ▼
┌───────────────────────────┐                   ┌──────────────────────────────┐
│  Inbox (Atomic JSON)      │                   │  Pluggable Executor          │
│  └─ Ingested by Daemon    │                   │  - Runs tool.execute()       │
│     via shared volume     │                   │  - Safe database query/host  │
└───────────────────────────┘                   └──────────────────────────────┘
```

## Detailed Specifications

1. **Role Grant Storage** *(retained, EXT-005)*:
   The `Grants`/`GrantSpec` bundle carries a `role: str` that selects the agent's
   *capability handles* via `BUILTIN_ROLES` (structural least-privilege). This is
   a capability grant, not an authorization policy.

2. **Permission Check Hook** *(DEPRECATED — removed)*:
   The `role_permission_gate` validator that read `config/permissions.json` and
   rejected decisions outside a role's action allowlist is removed. Jaros does
   not enforce an authorization policy; isolation against hostile code is the
   host's job (process/container/VPC), and blast-radius is bounded by the
   capability handles an agent actually holds.

3. **Dynamic Import**:
   We scan `plugins/tools/` (or a configured folder) at boot time using standard-library `importlib.util` to safely exec and load tool modules. Any parsing error is contained, logged, and isolated so the daemon boots normally even if a tool has syntax errors.
