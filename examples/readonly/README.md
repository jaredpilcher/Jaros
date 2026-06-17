# Read-only agent library

A set of purpose-built **read-only** agent systems you can run simultaneously on
one Jaros OS. Each agent only *proposes* inert `Decision` data; the work happens
in a matching **read-only tool** that performs no writes and mutates nothing.
Read-only is enforced two ways: structurally (spawn agents under a read-only
capability role — they hold no `FsWrite`/`QueueSend` handle) and by the tools
themselves (they only `read`/`scandir`/`stat`).

| Agent (`KIND`) | Decision kind / tool | Purpose (read-only) |
| --- | --- | --- |
| `system-health` | `sys.info` | Host platform / Python / CPU snapshot |
| `disk-monitor` | `fs.disk_usage` | Free / used bytes for a path |
| `inventory` | `fs.stat` | Directory inventory (names, sizes, types) |
| `text-metrics` | `text.count` | Line / word / char counts for a file |

```
examples/readonly/
  agents/    the agents (drop into <data>/agents/)
  tools/      the read-only tools (drop into <data>/tools/)
  schedules/  example schedules (drop into <data>/schedules/)
```

## Configure & run

Pick a throwaway data dir (never reuse one a daemon you don't own is using), and
stage the library into the shared volume:

```bash
DATA=/tmp/jaros-ro
mkdir -p $DATA/agents $DATA/tools $DATA/schedules
cp examples/readonly/agents/*.py   $DATA/agents/
cp examples/readonly/tools/*.py     $DATA/tools/

# boot the OS, then run any agent on demand
jaros serve --data-dir $DATA &
jaros submit system-health                        --data-dir $DATA
jaros submit disk-monitor --input '{"path":"."}'  --data-dir $DATA
jaros submit inventory    --input '{"path":"."}'  --data-dir $DATA
jaros submit text-metrics --input '{"path":"README.md"}' --data-dir $DATA
jaros watch --data-dir $DATA
```

All four run as independent lightweight threads under one daemon — many agent
systems, different purposes, simultaneously.

### Run them on a schedule (EXT-011)

Drop schedule files into `<data>/schedules/` and the daemon dispatches them
natively — no external cron:

```bash
cp examples/readonly/schedules/*.json $DATA/schedules/
# system-health runs every 30s; disk-monitor runs every 5 min (cron */5 * * * *)
jaros status --data-dir $DATA          # see the `schedules` array + next/last run
```

### Enforce read-only structurally

These agents need only `FsRead`. Spawn them under a read-only role so they hold
no write/queue handles — a misbehaving agent literally cannot write:

```python
from jaros.harness.capabilities import GrantSpec
harness.spawn("inventory", GrantSpec(role="FsReadRole", fs=shared_fs))
```

### In Docker (one node) and across containers (distributed)

```bash
# one container = one node; mount the staged data dir at /data
docker run -d --name jaros_ro -v $DATA:/data jaros

# multiple containers on the SAME shared dir coordinate over the file system:
# the first daemon to claim a job (inbox -> processed) runs it; siblings skip it
docker run -d --name jaros_ro_b -v $DATA:/data jaros
```

See the [web console](../../console/) to watch all of this live — submit jobs,
browse the decision log, and inspect schedules from the browser.
