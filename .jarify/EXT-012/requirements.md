---
id: EXT-012
title: Read-Only Agent Library
status: covered
priority: medium
implementation:
  - examples/readonly/tools/sys_info_tool.py
  - examples/readonly/tools/disk_usage_tool.py
  - examples/readonly/tools/dir_stat_tool.py
  - examples/readonly/tools/text_count_tool.py
  - examples/readonly/agents/system_health_agent.py
  - examples/readonly/agents/disk_monitor_agent.py
  - examples/readonly/agents/inventory_agent.py
  - examples/readonly/agents/text_metrics_agent.py
---

# Read-Only Agent Library

A curated, documented set of **read-only** agent systems that run simultaneously
on one Jaros OS for different purposes (health, disk, inventory, text metrics).
Each agent only proposes inert `Decision` data; the work happens in a matching
read-only tool that performs no writes. Read-only is enforced both structurally
(agents spawned under a read-only capability role hold no `FsWrite`/`QueueSend`
handle) and by the tools themselves. This realizes "many agents, many purposes"
on day one while staying within the Prime Directive's capability-safety
[PRIME-001 / P2] and reasoning/execution boundary [PRIME-001 / REQ-1].

### [REQ-1] Read-Only by Capability and by Tool

The agents and their tools only read; they never write, mutate, or escalate.

#### Acceptance Criteria
- [x] Each tool's `execute` performs only reads (`open(...,'r')`, `scandir`,
      `stat`, `shutil.disk_usage`, `platform`); it opens nothing for writing.
- [x] The agents emit only inert `Decision` data and hold no ambient I/O; they can
      be spawned under a read-only role (`FsReadRole`) with no write/queue handle.
- [x] Tool payloads are bounded (entry/size caps) so results stay inert and small.

### [REQ-2] Multi-Purpose Agent + Tool Set

A library of distinct read-only agents covers several operational purposes.

#### Acceptance Criteria
- [x] Includes `system-health` (`sys.info`), `disk-monitor` (`fs.disk_usage`),
      `inventory` (`fs.stat`), and `text-metrics` (`text.count`).
- [x] Each agent is a drop-in agent (`NAME` + `build(llm)`) and each tool a
      drop-in module (`NAME` + `validate` + `execute`), loadable at runtime.
- [x] Each agent proposes the decision type its tool handles, end to end.

### [REQ-3] Concurrent Multi-Agent Operation

Many of these agents run at once under a single daemon, as lightweight threads.

#### Acceptance Criteria
- [x] All four agents can be submitted and processed under one daemon with no
      failures, each producing its read-only result in the outbox.
- [x] A test drives the four agents concurrently and asserts the read-only outputs.
- [x] Operation composes with native scheduling (EXT-011) for unattended runs.

### [REQ-4] Configuration & Run Documentation

Operators can configure and run the library every way Jaros supports.

#### Acceptance Criteria
- [x] `examples/readonly/README.md` documents staging the agents/tools/schedules
      into a data dir and running on demand, on a schedule, and in Docker.
- [x] Example schedule files demonstrate interval and cron triggers for read-only
      agents (`schedules/system-health.json`, `schedules/disk-monitor.json`).
- [x] The docs show structural read-only enforcement (spawn under `FsReadRole`)
      and multi-container coordination over the shared file system.
