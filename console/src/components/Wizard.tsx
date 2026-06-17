import { useState } from "react";
import { useNavigate } from "react-router-dom";

import shotOverview from "../../docs/screenshots/overview.png";
import shotJobs from "../../docs/screenshots/jobs.png";
import shotAgents from "../../docs/screenshots/agents.png";
import shotReplay from "../../docs/screenshots/reproducibility.png";

// #EXT-010-REQ-9 Start
const TOUR_KEY = "jaros.tour.v1";

/** Returns true the first time the console is opened (tour not yet completed). */
export function shouldAutoOpenTour(): boolean {
  try {
    return !localStorage.getItem(TOUR_KEY);
  } catch {
    return false;
  }
}

const STEPS: { shot: string; title: string; body: string }[] = [
  {
    shot: shotOverview,
    title: "Welcome to the Jaros console",
    body: "This drives a live Jaros node over the shared file system — no server, no database, no broker. Just files and threads. The header chips show the machine state and whether the console is connected to a data dir.",
  },
  {
    shot: shotJobs,
    title: "Everything starts with a job",
    body: "Submit a job on the Jobs page and watch it flow inbox → processed → outbox. A job is the only way work enters the system, written atomically to the shared inbox.",
  },
  {
    shot: shotAgents,
    title: "Extend it at runtime",
    body: "Drop an agent (it proposes inert Decision data) or a custom tool (it executes the action) into the watched folders and the daemon loads it on the next tick — no restart, no core edits.",
  },
  {
    shot: shotReplay,
    title: "Prove every run is reproducible",
    body: "Reproducibility replays any run from the recorded decision log — reconstructing it byte-identically with zero model calls. It is the one guarantee that sets Jaros apart. Click Replay there to see it.",
  },
];

export function Wizard({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [i, setI] = useState(0);
  const navigate = useNavigate();
  if (!open) return null;

  const step = STEPS[i];
  const last = i === STEPS.length - 1;

  function finish(go?: string) {
    try {
      localStorage.setItem(TOUR_KEY, new Date().toISOString());
    } catch {
      /* ignore */
    }
    setI(0);
    onClose();
    if (go) navigate(go);
  }

  return (
    <div className="modal-backdrop" onClick={() => finish()}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-shot">
          <img src={step.shot} alt={step.title} />
        </div>
        <div className="modal-body">
          <div className="modal-step">Step {i + 1} of {STEPS.length}</div>
          <h2>{step.title}</h2>
          <p>{step.body}</p>
        </div>
        <div className="modal-foot">
          <button className="link-btn" onClick={() => finish()}>Skip tour</button>
          <div className="modal-dots">
            {STEPS.map((_, k) => <span key={k} className={`d ${k === i ? "on" : ""}`} />)}
          </div>
          <div className="grow" />
          {i > 0 && <button onClick={() => setI((n) => n - 1)}>Back</button>}
          {last ? (
            <button className="primary" onClick={() => finish("/jobs")}>Start with a job →</button>
          ) : (
            <button className="primary" onClick={() => setI((n) => n + 1)}>Next</button>
          )}
        </div>
      </div>
    </div>
  );
}
// #EXT-010-REQ-9 End
