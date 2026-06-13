import { Route, Routes } from "react-router-dom";

import { useLiveSnapshot } from "./api";
import { Layout } from "./components/Layout";
import { Agents } from "./pages/Agents";
import { Evals } from "./pages/Evals";
import { Harness } from "./pages/Harness";
import { Jobs } from "./pages/Jobs";
import { Overview } from "./pages/Overview";
import { Replay } from "./pages/Replay";
import { Schedules } from "./pages/Schedules";
import { StateMachine } from "./pages/StateMachine";

const PAGES: { path: string; title: string; crumb?: string; el: (snap: ReturnType<typeof useLiveSnapshot>) => JSX.Element }[] = [
  { path: "/", title: "Overview", el: (s) => <Overview snap={s} /> },
  { path: "/jobs", title: "Jobs", crumb: "submit & inspect", el: () => <Jobs /> },
  { path: "/agents", title: "Agents & Tools", crumb: "runtime extensions", el: () => <Agents /> },
  { path: "/replay", title: "Reproducibility", crumb: "decision log & replay", el: () => <Replay /> },
  { path: "/schedules", title: "Schedules", crumb: "native cron & interval", el: () => <Schedules /> },
  { path: "/evals", title: "Evaluations", crumb: "reproducible agent tests", el: () => <Evals /> },
  { path: "/state", title: "State Machine", crumb: "durable & replayable", el: () => <StateMachine /> },
  { path: "/harness", title: "Harness", crumb: "capability-safety", el: () => <Harness /> },
];

export default function App() {
  const snap = useLiveSnapshot();
  return (
    <Routes>
      {PAGES.map((p) => (
        <Route
          key={p.path}
          path={p.path}
          element={
            <Layout snap={snap} title={p.title} crumb={p.crumb}>
              {p.el(snap)}
            </Layout>
          }
        />
      ))}
    </Routes>
  );
}
