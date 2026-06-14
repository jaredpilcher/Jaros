import type { ReactNode } from "react";

export function Card({
  title,
  desc,
  right,
  children,
  pad = true,
}: {
  title?: ReactNode;
  desc?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  pad?: boolean;
}) {
  return (
    <div className="card">
      {(title || right) && (
        <div className="card-h">
          <div>
            {title && <div className="title">{title}</div>}
            {desc && <div className="desc">{desc}</div>}
          </div>
          {right && <div style={{ marginLeft: "auto" }}>{right}</div>}
        </div>
      )}
      <div className={pad ? "card-b" : ""}>{children}</div>
    </div>
  );
}

export function Stat({
  label,
  value,
  tone,
  foot,
}: {
  label: string;
  value: ReactNode;
  tone?: "green" | "red";
  foot?: ReactNode;
}) {
  return (
    <div className="card stat">
      <div className="label">{label}</div>
      <div className={`value ${tone ?? ""}`}>{value}</div>
      {foot && <div className="foot">{foot}</div>}
    </div>
  );
}

export type Tone = "ok" | "warn" | "bad" | "idle";

export function Pill({ tone, children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`pill ${tone ?? ""}`}>
      <span className="dot" />
      {children}
    </span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}

/** Bespoke SVG sparkline — no chart dependency. */
export function Sparkline({
  data,
  width = 220,
  height = 44,
  color = "var(--green)",
}: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}) {
  if (data.length < 2) return <svg width={width} height={height} />;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const span = max - min || 1;
  const step = width / (data.length - 1);
  const pts = data.map((d, i) => {
    const x = i * step;
    const y = height - 4 - ((d - min) / span) * (height - 8);
    return [x, y] as const;
  });
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} ${width},${height} 0,${height}`;
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <polygon points={area} fill={color} opacity={0.1} />
      <polyline points={line} fill="none" stroke={color} strokeWidth={1.8} strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r={2.6} fill={color} />
    </svg>
  );
}

const STATE_TONE: Record<string, Tone> = {
  PENDING: "idle",
  RUNNING: "warn",
  BLOCKED: "warn",
  DONE: "ok",
  FAILED: "bad",
};

export function StateBadge({ state }: { state?: string }) {
  if (!state) return <Pill tone="idle">unknown</Pill>;
  return <Pill tone={STATE_TONE[state] ?? "idle"}>{state}</Pill>;
}
