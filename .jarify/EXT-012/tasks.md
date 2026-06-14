# Implementation Tasks — Read-Only Agent Library

### [TASK-1] Implement the read-only tools

Provide four read-only Execution-Plane tools, each performing only reads.

#### Steps
1. Create `examples/readonly/tools/sys_info_tool.py` (`sys.info`, platform/cpu via `platform`/`os`) and `disk_usage_tool.py` (`fs.disk_usage` via `shutil.disk_usage`, path-validated).
2. Create `examples/readonly/tools/dir_stat_tool.py` (`fs.stat` via `os.scandir`, entry-capped) and `text_count_tool.py` (`text.count` via `open(...,'r')`, size-capped); each exposes `NAME`/`validate`/`execute` and opens nothing for writing.

#### Implements
- [REQ-1] Read-Only by Capability and by Tool
- [REQ-2] Multi-Purpose Agent + Tool Set

### [TASK-2] Implement the read-only plugin agents

Provide a plugin agent per purpose that proposes its tool's decision kind.

#### Steps
1. Create `examples/readonly/plugins/{system_health,disk_monitor,inventory,text_metrics}_agent.py`, each with `KIND` and `build(llm)` returning a boundary whose `decide()` emits a single inert decision of the matching kind (`sys.info`/`fs.disk_usage`/`fs.stat`/`text.count`).
2. Keep the agents side-effect free — they consult context and emit `Decision` data only, holding no handles.

#### Implements
- [REQ-2] Multi-Purpose Agent + Tool Set

### [TASK-3] Document configuration and running

Show every supported way to configure and run the library.

#### Steps
1. Create `examples/readonly/README.md` covering staging into a data dir, on-demand `jaros submit`, scheduled runs (drop schedule files), structural read-only via `FsReadRole`, Docker, and multi-container coordination.
2. Add example schedules `examples/readonly/schedules/system-health.json` (interval) and `disk-monitor.json` (cron), demonstrating EXT-011 triggers for read-only agents.

#### Implements
- [REQ-4] Configuration & Run Documentation
- [REQ-3] Concurrent Multi-Agent Operation

### [TASK-4] Test the library end to end

Prove each agent runs read-only and that many run concurrently under one daemon.

#### Steps
1. Create `tests/test_readonly_agents.py` that loads each tool, builds each agent, runs `decide()` → gate → `executor.apply`, and asserts the read-only result shape.
2. Add a daemon integration test that stages all plugins + tools, submits all four kinds, ticks, and asserts `processed >= 4`, `failed == 0`, and an outbox result per kind.

#### Implements
- [REQ-1] Read-Only by Capability and by Tool
- [REQ-3] Concurrent Multi-Agent Operation
