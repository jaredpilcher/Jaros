import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import shotOverview from "../../docs/screenshots/overview.png";
import shotJobs from "../../docs/screenshots/jobs.png";
import shotAgents from "../../docs/screenshots/agents.png";
import shotReplay from "../../docs/screenshots/reproducibility.png";
import shotSchedules from "../../docs/screenshots/schedules.png";
import shotEvals from "../../docs/screenshots/evaluations.png";
import shotState from "../../docs/screenshots/state-machine.png";
import shotHarness from "../../docs/screenshots/harness.png";

const GH = "https://github.com/jaredpilcher/Jaros/blob/main";

function Shot({ src, cap }: { src: string; cap: string }) {
  return (
    <figure>
      <img src={src} alt={cap} />
      <figcaption>{cap}</figcaption>
    </figure>
  );
}

// #EXT-010-REQ-9 Start
/** In-app documentation: a guided tour of every page (with pictures) plus a
 *  step-by-step CLI quickstart, so an operator never has to leave the console. */
export function Help() {
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return;
    const el = document.getElementById(hash.slice(1));
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [hash]);

  return (
    <div className="doc">
      <h2 id="start" className="anchor">Where to start</h2>
      <p>
        Jaros is a zero-infrastructure agent OS: a daemon turns inbox jobs into validated, durable
        state transitions over a shared file system — no server, database, or broker. This console is a
        live window onto one node. The fastest path:
      </p>
      <ol>
        <li><b>Submit a job</b> on the <i>Jobs</i> page — work only enters through a job.</li>
        <li><b>Install an agent or tool</b> on <i>Agents &amp; Tools</i> — loaded on the next tick, no restart.</li>
        <li><b>Replay the run</b> on <i>Reproducibility</i> — rebuild it byte-identically with zero model calls.</li>
      </ol>
      <p className="hint">First time here? Re-open the guided tour anytime with the <b>? Guide</b> button in the top bar.</p>

      <h2 id="overview" className="anchor">Overview</h2>
      <p>
        Your at-a-glance health panel: machine state, jobs processed/failed, decisions logged, throughput
        over recent ticks, the agent-thread pool, and the zero-infra runtime profile. The <b>Get started</b>
        checklist lights up each step as you complete the core loop.
      </p>
      <Shot src={shotOverview} cap="Overview — live health, throughput, and the get-started checklist" />

      <h2 id="jobs" className="anchor">Jobs</h2>
      <p>
        Submit a job (an agent <code>name</code> + JSON input) and it is written atomically to the shared
        <code> inbox/</code> — the only way work enters the system. Watch it flow inbox → processed → outbox.
        Use the preset buttons (<code>advance</code>, <code>echo</code>, <code>greeter</code>) for a one-click start.
      </p>
      <Shot src={shotJobs} cap="Jobs — submit, then watch the queue and outbox update live" />
      <pre className="cli">{`# the same thing from the CLI
jaros submit advance --input '{}' --data-dir $DATA
jaros status --data-dir $DATA      # state, processed, schedules`}</pre>

      <h2 id="agents" className="anchor">Agents &amp; Tools</h2>
      <p>
        Lists the agents loaded from <code>agents/</code> and the custom tools from <code>tools/</code>. Install a new
        one by name + Python source and the daemon picks it up on the next tick — no restart, no core edits.
        An <b>agent</b> proposes inert <code>Decision</code> data; a <b>tool</b> executes a namespaced action.
      </p>
      <Shot src={shotAgents} cap="Agents & Tools — loaded extensions and the runtime installer" />
      <pre className="cli">{`# install an agent from the CLI
jaros add-agent ./my_agent.py --data-dir $DATA
cp examples/readonly/agents/*.py $DATA/agents/   # or the read-only library`}</pre>

      <h2 id="replay" className="anchor">Reproducibility</h2>
      <p>
        The headline guarantee. Every accepted decision is recorded to <code>state/decisions.log</code>. Click
        <b> Replay</b> and Jaros re-applies that log through the runtime's <i>own</i> handlers into a fresh
        sandbox (never touching live data) and confirms the rebuilt run is <b>byte-identical</b> with
        <b> zero model calls</b>.
      </p>
      <Shot src={shotReplay} cap="Reproducibility — replay reconstructs a run byte-identically, no model call" />
      <pre className="cli">{`jaros replay --data-dir $DATA          # exit 0 reproducible, 1 divergence, 2 nothing
jaros replay --data-dir $DATA --json   # { decisions, modelCalls:0, byteIdentical, ok }`}</pre>

      <h2 id="schedules" className="anchor">Schedules</h2>
      <p>
        Run jobs on a native cron, fixed interval, or one-shot — no external scheduler. Create, pause, and
        delete schedules here; the daemon dispatches them and they are crash-safe (a restart neither
        double-fires nor skips).
      </p>
      <Shot src={shotSchedules} cap="Schedules — native cron / interval, crash-safe, no external cron" />

      <h2 id="evals" className="anchor">Evaluations</h2>
      <p>
        Reproducible, declarative agent tests: input → expected decision/result, with no model-grading
        flakiness. Click <b>Run eval suite</b> to run every case and see per-case checks. Exit code is 0 iff
        all pass, so the same suite gates CI.
      </p>
      <Shot src={shotEvals} cap="Evaluations — declarative, reproducible agent tests" />
      <pre className="cli">{`cp examples/readonly/evals/*.json $DATA/evals/
jaros eval --data-dir $DATA        # exit 0 iff all pass`}</pre>

      <h2 id="state" className="anchor">State Machine</h2>
      <p>
        The single source of truth. Every job advances through a declared state machine; only declared
        transitions are permitted, everything else is rejected. The durable, checksummed
        <code> transitions.log</code> records every committed transition — and is exactly what replay rebuilds.
      </p>
      <Shot src={shotState} cap="State Machine — declared transitions and the durable transition log" />

      <h2 id="harness" className="anchor">Harness</h2>
      <p>
        Capability-safety, made visible. Agents hold only the scoped capabilities the harness grants;
        every mediated action is default-deny. This page shows the mediation rules (action → required
        capability), the role → capability matrix, and the refusal audit of contained failures.
      </p>
      <Shot src={shotHarness} cap="Harness — mediation rules, roles, and the refusal audit" />

      <h2 id="cli" className="anchor">CLI quickstart</h2>
      <p>Everything in this console maps to a command. A linear path from install to a reproducible run:</p>
      <pre className="cli">{`# 1. install
pip install -e ".[dev]"
pytest                                   # full suite + architecture guardrails

# 2. run the node + your first job (use a throwaway data dir)
DATA=/tmp/jaros
jaros serve  --data-dir $DATA &
jaros submit advance --input '{}' --data-dir $DATA
jaros status --data-dir $DATA

# 3. extend at runtime
cp examples/readonly/agents/*.py $DATA/agents/
cp examples/readonly/tools/*.py  $DATA/tools/
jaros submit system-health --data-dir $DATA

# 4. schedule + evaluate
cp examples/readonly/schedules/*.json $DATA/schedules/
cp examples/readonly/evals/*.json     $DATA/evals/
jaros eval --data-dir $DATA

# 5. reproduce by replay — the headline guarantee
jaros replay --data-dir $DATA --json

# 6. open this console
cd console && npm install
JAROS_DATA_DIR=$DATA npm run dev          # http://localhost:5500`}</pre>

      <h2 id="more" className="anchor">Full documentation</h2>
      <p>Deeper references, all with runnable examples:</p>
      <ul>
        <li><a href={`${GH}/docs/console.md`} target="_blank" rel="noreferrer">Console guide</a> — this tour, with pictures</li>
        <li><a href={`${GH}/docs/getting-started.md`} target="_blank" rel="noreferrer">Getting started</a> — day one to production</li>
        <li><a href={`${GH}/docs/building-agents.md`} target="_blank" rel="noreferrer">Building agents</a> — write your own agent + tool</li>
        <li><a href={`${GH}/docs/agent-playbook.md`} target="_blank" rel="noreferrer">Agent playbook</a> — patterns and recipes</li>
      </ul>
    </div>
  );
}
// #EXT-010-REQ-9 End
