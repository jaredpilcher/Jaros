import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import type { Snapshot } from "../api";
import { Pill } from "./ui";

const NAV: { to: string; label: string; ico: string; badge?: (s: Snapshot | null) => number | undefined }[] = [
  { to: "/", label: "Overview", ico: "◎" },
  { to: "/jobs", label: "Jobs", ico: "▣", badge: (s) => s?.counts.inbox },
  { to: "/agents", label: "Agents & Tools", ico: "◆", badge: (s) => (s ? s.counts.plugins + s.counts.tools : undefined) },
  { to: "/replay", label: "Reproducibility", ico: "↻", badge: (s) => s?.counts.decisions },
  { to: "/schedules", label: "Schedules", ico: "⏱" },
  { to: "/state", label: "State Machine", ico: "⬡" },
  { to: "/harness", label: "Harness", ico: "▤" },
];

export function Layout({
  snap,
  title,
  crumb,
  children,
}: {
  snap: Snapshot | null;
  title: string;
  crumb?: string;
  children: ReactNode;
}) {
  const connected = !!snap?.connected;
  const state = snap?.status?.state;
  const active = snap?.status?.pool?.active ?? 0;
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">J</div>
          <div>
            <div className="name">JAROS</div>
            <div className="sub">console</div>
          </div>
        </div>
        {NAV.map((n) => {
          const badge = n.badge?.(snap);
          return (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              <span className="ico">{n.ico}</span>
              <span>{n.label}</span>
              {badge ? <span className="nav-badge">{badge}</span> : null}
            </NavLink>
          );
        })}
        <div className="sidebar-foot">
          zero-infrastructure runtime
          <br />
          files + threads · no server
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <h1>{title}</h1>
          {crumb && <span className="crumb">/ {crumb}</span>}
          <div className="spacer" />
          {state && <Pill tone={state === "FAILED" ? "bad" : "ok"}>state · {state}</Pill>}
          <Pill tone={active > 0 ? "warn" : "idle"}>{active} active</Pill>
          <Pill tone={connected ? "ok" : "bad"}>{connected ? "connected" : "no data dir"}</Pill>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
