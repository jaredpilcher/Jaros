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

### [TASK-3] Enforce role-based permission gate

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
