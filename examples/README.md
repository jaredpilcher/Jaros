# Examples

Drop-in example agents and tools for a running Jaros OS. They are loaded over the
shared file system at runtime — no daemon restart, no code changes to core.

| File | Where it goes | What it shows |
| --- | --- | --- |
| `agents/echo_agent.py` | `<data>/agents/` | An agent (`NAME = "echo"`) that emits an inert `advance` Decision driving a job to `DONE`. |
| `agents/greeter_agent.py` | `<data>/agents/` | An agent (`NAME = "greeter"`) that proposes a *custom tool* action (`demo.greet`). |
| `tools/greet_tool.py` | `<data>/tools/` | A custom Execution-Plane tool (`NAME = "demo.greet"`) with its own deterministic `validate()`/`execute()`. |

## Try it

Pick a throwaway data dir (never reuse one a daemon you don't own is using):

```bash
# stage the examples into the shared volume
mkdir -p /tmp/jaros-demo/agents /tmp/jaros-demo/tools
cp examples/agents/*.py /tmp/jaros-demo/agents/
cp examples/tools/*.py   /tmp/jaros-demo/tools/

# boot the OS, then from another shell submit work
export JAROS_DATA_DIR=/tmp/jaros-demo
jaros serve &
jaros submit advance --input '{}'
jaros submit echo    --input '{"msg": "hi"}'
jaros submit greeter --input '{"name": "Jaros"}'
jaros watch
```

Each accepted decision is recorded to `<data>/state/decisions.log`, so the run is
reproducible by replay (EXT-002 / REQ-6).

The integration scripts `tests/integration/run_local_demo.py` (no Docker) and
`tests/integration/run_container_demo.py` (Docker) automate exactly this flow
against a throwaway data dir and assert the results.
