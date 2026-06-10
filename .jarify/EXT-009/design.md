# Design — Dynamic Custom Tools and Namespaced Actions

Architectural context, system flows, and design specifications for dynamically registering and executing custom host actions.

## System Flows

The dynamic tooling system allows operators to plug new code into the Execution Plane while keeping the Reasoning Plane entirely sandboxed. 

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

1. **Role Grant Storage**:
   We extend the `Grants` bundle class to contain a `role: str` parameter, allowing the validation gate and executor to retrieve the spawned agent's assigned role and perform security checks.
   
2. **Permission Check Hook**:
   We register a custom global validation gate check (`role_permission_gate`) that:
   - Identifies the role of the decision's source (agent).
   - Looks up the allowed actions for that role in the config (`config/permissions.json`).
   - Rejects the decision if the action is not allowed for that role.

3. **Dynamic Import**:
   We scan `plugins/tools/` (or a configured folder) at boot time using standard-library `importlib.util` to safely exec and load tool modules. Any parsing error is contained, logged, and isolated so the daemon boots normally even if a tool has syntax errors.
