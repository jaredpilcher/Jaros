import { useState } from "react";
import { Route, Routes } from "react-router-dom";

import { useLiveSnapshot } from "./api";
import { Layout } from "./components/Layout";
import { Wizard, shouldAutoOpenTour } from "./components/Wizard";
import { Agents } from "./pages/Agents";
import { Evals } from "./pages/Evals";
import { Harness } from "./pages/Harness";
import { Help } from "./pages/Help";
import { Jobs } from "./pages/Jobs";
import { Overview } from "./pages/Overview";
import { Replay } from "./pages/Replay";
import { Schedules } from "./pages/Schedules";
import { StateMachine } from "./pages/StateMachine";

type El = (ctx: { snap: ReturnType<typeof useLiveSnapshot>; openGuide: () => void }) => JSX.Element;
const PAGES: { path: string; title: string; crumb?: string; el: El }[] = [
  { path: "/", title: "Overview", el: ({ snap, openGuide }) => <Overview snap={snap} onTour={openGuide} /> },
  { path: "/jobs", title: "Jobs", crumb: "submit & inspect", el: () => <Jobs /> },
  { path: "/agents", title: "Agents & Tools", crumb: "runtime extensions", el: () => <Agents /> },
  { path: "/replay", title: "Reproducibility", crumb: "decision log & replay", el: () => <Replay /> },
  { path: "/schedules", title: "Schedules", crumb: "native cron & interval", el: () => <Schedules /> },
  { path: "/evals", title: "Evaluations", crumb: "reproducible agent tests", el: () => <Evals /> },
  { path: "/state", title: "State Machine", crumb: "durable & replayable", el: () => <StateMachine /> },
  { path: "/harness", title: "Harness", crumb: "capability-safety", el: () => <Harness /> },
  { path: "/help", title: "Help & Docs", crumb: "guide · pictures · CLI", el: () => <Help /> },
];

export default function App() {
  const snap = useLiveSnapshot();
  const [tourOpen, setTourOpen] = useState(shouldAutoOpenTour);
  const openGuide = () => setTourOpen(true);

  return (
    <>
      <Routes>
        {PAGES.map((p) => (
          <Route
            key={p.path}
            path={p.path}
            element={
              <Layout snap={snap} title={p.title} crumb={p.crumb} onOpenGuide={openGuide}>
                {p.el({ snap, openGuide })}
              </Layout>
            }
          />
        ))}
      </Routes>
      <Wizard open={tourOpen} onClose={() => setTourOpen(false)} />
    </>
  );
}
