import { Link } from "react-router-dom";

import type { Snapshot } from "../api";
import { Card, Tip } from "./ui";

// #EXT-010-REQ-9 Start
/** A live, status-driven checklist that tells a new operator exactly what to do next. */
export function GetStarted({ snap, onTour }: { snap: Snapshot | null; onTour: () => void }) {
  const c = snap?.counts;
  const steps = [
    {
      done: !!snap?.connected,
      title: "Connect to a Jaros node",
      desc: snap?.connected ? "The console is reading a live data dir." : "Start a daemon: jaros serve --data-dir <dir>",
      to: "/help",
      cta: "Guide",
    },
    {
      done: !!c && c.processed > 0,
      title: "Submit your first job",
      desc: "Work only enters through a job. Try a built-in 'advance' job.",
      to: "/jobs",
      cta: "Open Jobs",
    },
    {
      done: !!c && c.agents + c.tools > 0,
      title: "Extend it at runtime",
      desc: "Install an agent or a custom tool — loaded on the next tick, no restart.",
      to: "/agents",
      cta: "Agents & Tools",
    },
    {
      done: !!c && c.decisions > 0,
      title: "Reproduce a run by replay",
      desc: "Rebuild a run byte-identically from the decision log, zero model calls.",
      to: "/replay",
      cta: "Reproducibility",
    },
  ];
  const nowIndex = steps.findIndex((s) => !s.done);
  const allDone = nowIndex === -1;

  return (
    <Card
      title={<>Get started <Tip text="A live checklist of the core Jaros loop. Each step lights up as you complete it." /></>}
      desc={allDone ? "You've completed the core loop — explore the rest from the sidebar." : "New here? Follow these four steps."}
      right={<button className="help-btn" onClick={onTour}>↺ Take the tour</button>}
    >
      <div className="checklist">
        {steps.map((s, i) => {
          const cls = s.done ? "done" : i === nowIndex ? "now" : "";
          return (
            <Link key={s.title} to={s.to} className={`check ${cls}`}>
              <span className="ck-box">{s.done ? "✓" : i + 1}</span>
              <div>
                <div className="ck-title">{s.title}</div>
                <div className="ck-desc">{s.desc}</div>
              </div>
              {!s.done && <span className="ck-cta">{s.cta} →</span>}
            </Link>
          );
        })}
      </div>
    </Card>
  );
}
// #EXT-010-REQ-9 End
