# Implementation Tasks — Dynamic Custom Tools and Namespaced Actions

### [TASK-1] Implement the dynamic tool loader module

Provide the core utility to discover and dynamically load custom host execution tool classes from a watched filesystem path.

#### Steps
1. Create `jaros/execution/tools.py` with standard library `importlib.util` dynamic imports.
2. Scan the configured tools directory for `*.py` modules and resolve tool class objects exposing `NAME`, `validate`, and `execute` methods.
3. Catch, contain, and log module loading failures safely to prevent daemon startup crashes.

#### Implements
- [REQ-1] Dynamic Tool Loader
- [REQ-4] Anatomy of a Custom Tool Class

### [TASK-2] Integrate tool loader with the daemon

Hook the custom tool loading system into the core composition root during OS startup.

#### Steps
1. In `Daemon.__init__` of `jaros/daemon.py`, import and trigger `load_custom_tools`.
2. Target the watched shared filesystem `tools/` directory and feed it the active `harness` instance.

#### Implements
- [REQ-1] Dynamic Tool Loader

### [TASK-3] Enforce role-based permission gate — SUPERSEDED

> **SUPERSEDED by [TASK-5].** Implemented the `role_permission_gate` /
> `PolicyManager` authorization layer against the now-deprecated [REQ-3]. Retired
> by [TASK-5]. Do not extend this task.

Enforce strict security boundaries preventing agents from running custom actions unless their active role possesses permission.

#### Steps
1. In `jaros/execution/tools.py`, implement `role_permission_gate` validator.
2. Resolve the requesting agent's role from the Harness grants.
3. Match the decision's action namespace against the allowed actions list in `config/permissions.json`, and reject the decision if unauthorized.

#### Implements
- [REQ-3] Role-Based Permission Enforcer

### [TASK-4] Register tools in the gate and executor

Wire dynamic tool classes up as first-class citizens in the Execution Plane's validation and execution pipelines.

#### Steps
1. In `load_custom_tools`, wrap the tool's `validate()` method as a pure validation function and register it using `register_validator()`.
2. Register the tool's `execute()` method as the deterministic execution handler for `tool.NAME` in the global `executor` dispatcher.

#### Implements
- [REQ-2] Decoupled Gate & Executor Registration

### [TASK-5] Remove the role-based permission enforcer

Retire the authorization-gateway layer so the system aligns with the directive's
"not a governance product" boundary. This is the deprecation task for [REQ-3].

#### Steps
1. In `jaros/execution/tools.py`, delete the `#EXT-009-REQ-3` block (`PolicyManager`), the global `policy_manager`, `register_permission_gate`/`role_permission_gate`, and the `_permission_gate_registered` flag; simplify `load_custom_tools(tools_dir)` to scan + register tool validators/handlers only (drop the `harness` and `permissions_path` params and the gate registration call).
2. In `jaros/daemon.py`, update both `load_custom_tools(...)` calls to pass only the tools dir; replace the `policy_manager.get_policy()["assignments"]` role lookup with a fixed least-privilege default role (`GuestRole`) for spawned job kinds; remove the now-unused `policy_manager` import.
3. `git rm config/permissions.json` (and stop referencing `config/permissions.local.json`); update `tests/test_dynamic_tools.py` to drop the permission-gate and `PolicyManager` tests and the `permissions_path` argument; remove `REQ-3` from `.jarify/EXT-009/index.json`.
4. Update `docs/building-agents.md` and `docs/agent-playbook.md` to remove the role-permission/`permissions.json` enforcement sections, reframing capability-safety as structural least-privilege via harness handles. Run `pytest`.

#### Implements
- [REQ-3] Role-Based Permission Enforcer
