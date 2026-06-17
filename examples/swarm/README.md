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

The model's answer **drives** each decision — it isn't a cosmetic note. The LLM
decides *what* (a verdict); the decision bakes that verdict into the events, and
the deterministic executor decides *how* (the transitions):

- **`agents/planner_agent.py`** (`planner`) — an LLM triage gate. **ACCEPT** advances
  the ticket to `DONE`; **REJECT** (spam/abuse) drives it to `FAILED`.
- **`agents/worker_agent.py`** (`worker`) — drafts a reply, then the LLM judges its own
  confidence. A confident **YES** hands off cleanly; an unsure **NO** is a bad handoff.
  Submitting `{"bad": true}` also forces a bad handoff for the demo.
- **`agents/reviewer_agent.py`** (`reviewer`) — an LLM reviewer. **APPROVE** advances to
  `DONE`; **REVISE** drives the job to `BLOCKED` (needs revision).
- **`tools/handoff_tool.py`** (`swarm.handoff`) — the reviewer accepting a draft. A
  bad handoff is recorded (it is valid data) but **rejected on execution**, so
  replay reproduces it AND attributes it.

So a different model judgment yields a different recorded decision and a different
reconstructed state — and replay reproduces whichever the model chose, with no
model call. Every agent reaches the model through the one `LlmClient` interface;
the demo uses the **deterministic mock** by default (no model server — the mock
takes the happy path, so outcomes are deterministic for CI). Point it at a real
small model by setting `config/llm.json` to `{"provider":"ollama"}` (and running
`ollama serve`) — no code change.

For example, with a real model the planner gates spam to `FAILED` and a genuine
request to `DONE`, purely from the LLM's verdict:

```text
$ jaros submit planner --input '{"ticket":"BUY CHEAP CRYPTO NOW!!! claim your prize"}'
   planner verdict=reject  events=[start, fail]      -> FAILED
$ jaros submit planner --input '{"ticket":"can't log in after a password reset"}'
   planner verdict=accept  events=[start, complete]  -> DONE
```

## Run it

```bash
DATA=/tmp/jaros-swarm
mkdir -p $DATA/agents $DATA/tools
cp examples/swarm/agents/*.py $DATA/agents/
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
