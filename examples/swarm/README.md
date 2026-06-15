# Swarm reference demo — replay a hive, find the culprit (EXT-015)

The headline proof of the Prime Directive's apex purpose: a **swarm** of agents is
**reproducible** (replay the whole hive byte-identically, no model call) and
**accountable** (attribute any failure to the exact agent + decision that caused
it). A single agent is just the swarm of one.

This is a support-ticket triage hive:

```text
   planner ──► worker ──► reviewer        (each a ReasoningBoundary thread)
      │           │            │
      │  classify │  draft +   │  review
      ▼           ▼  HAND OFF  ▼
   ============ HARNESS: validate · mediate · RECORD (ordered · per-agent · hash-chained) ============
                          one durable decision log
                                   │
                       jaros replay │  (no model call)
                                   ▼
              byte-identical swarm state  +  "which agent, which decision"
```

- **`plugins/planner_agent.py`** (`planner`) — classifies the ticket.
- **`plugins/worker_agent.py`** (`worker`) — drafts a reply and **hands it off** to
  the reviewer. Submitting `{"bad": true}` seeds a **bad handoff**.
- **`plugins/reviewer_agent.py`** (`reviewer`) — reviews and finalizes.
- **`tools/handoff_tool.py`** (`swarm.handoff`) — the reviewer accepting a draft. A
  bad handoff is recorded (it is valid data) but **rejected on execution**, so
  replay reproduces it AND attributes it.

Every agent reaches the model through the one `LlmClient` interface; the demo uses
the **deterministic mock** by default (no model server needed). Point it at a real
small model by setting `config/llm.json` to `{"provider":"ollama"}` (and running
`ollama serve`) — no code change.

## Run it

```bash
DATA=/tmp/jaros-swarm
mkdir -p $DATA/plugins $DATA/tools
cp examples/swarm/plugins/*.py $DATA/plugins/
cp examples/swarm/tools/*.py   $DATA/tools/

JAROS_LLM_PROVIDER=default jaros serve --data-dir $DATA &

# a hive triaging two tickets + one seeded bad handoff
for t in "login fails" "double charge"; do
  jaros submit planner  --input "{\"ticket\":\"$t\"}" --data-dir $DATA
  jaros submit worker   --input "{\"ticket\":\"$t\"}" --data-dir $DATA
  jaros submit reviewer --input "{\"ticket\":\"$t\"}" --data-dir $DATA
done
jaros submit worker --input '{"ticket":"refund","bad":true}' --data-dir $DATA   # the culprit

# replay the WHOLE swarm and find who broke it
jaros replay --data-dir $DATA
#   replayed 7 recorded decisions across 3 agent(s) - model calls: 0
#       planner   2 ·  reviewer 2 ·  worker 3
#   reconstructed state : DONE
#   byte-identical      : yes
#   tamper-evident chain: intact
#   attribution [FAILURE] : agent 'worker' - the bad-handoff decision  (reviewer rejected the handoff)
#   (the exact decision index varies with how the concurrent jobs interleave;
#    what's stable is the attributed agent + reason.)
```

End-to-end in Docker (builds the image, runs the hive in a container, replays on
the host, asserts byte-identity + attribution):

```bash
python tests/integration/run_swarm_replay_demo.py
```

Also visible in the web console's **Reproducibility** page: the per-agent
breakdown and the attributed agent/decision, beside the durable decision log.
