# Design — Read-Only Agent Library

A library of independent read-only agent systems, each a drop-in plugin paired
with a drop-in read-only tool. They demonstrate "many agents, many purposes,
simultaneously" while staying strictly within the reasoning/execution boundary:
the agent proposes inert data, the tool performs only reads.

## Two layers of read-only

```text
   Reasoning Plane                 Execution Plane
   +-------------------+           +----------------------------+
   |  plugin agent     |  Decision |  read-only tool            |
   |  (KIND=...)       | ────────► |  validate() + execute()    |
   |  emits inert data |  (kind)   |  open('r') / scandir/stat  |
   +-------------------+           +----------------------------+
        held under FsReadRole            performs NO writes
        (no FsWrite / QueueSend)         (structural + by code)
```

- **Structural** — spawn the agent under a read-only role; it never receives a
  write/queue handle, so a bug cannot write (EXT-005 capability scoping).
- **By construction** — every tool's `execute` only reads, with entry/size caps.

## The library

```text
   system-health  ─► sys.info        host platform / python / cpu
   disk-monitor   ─► fs.disk_usage   total/used/free bytes for a path
   inventory      ─► fs.stat         directory entries, sizes, types
   text-metrics   ─► text.count      lines / words / chars of a file
```

```text
   examples/readonly/
     plugins/    drop into <data>/plugins/   (the agents)
     tools/      drop into <data>/tools/     (the read-only handlers)
     schedules/  drop into <data>/schedules/ (interval + cron examples, EXT-011)
```

## Running many at once

Each agent kind is independent; the daemon runs them as lightweight threads in
its bounded pool. Submitting jobs for all four (on demand, scheduled, or from the
console) runs four agent systems concurrently on one node. Across containers
sharing a data dir, the existing inbox→processed claim (EXT-002 / REQ-7) means
the first daemon to claim a job runs it and siblings skip it — read-only work
distributes for free.

## Prime Directive consistency

- Agents only propose `Decision` data; tools do the deterministic read. [REQ-1, P2]
- No infrastructure added — files + threads. [P3]
- Read-only is both structural (capability role) and behavioral (tool code),
  matching capability-safety as least-privilege, not a sandbox. [P2]
