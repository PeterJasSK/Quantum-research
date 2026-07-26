"use client";

import { SATURATION_UTILISATION } from "@/lib/constants";

// AC-1: attacker, switch, N=4 links, victim topology diagram.
export default function TopologyView({ linkUtil }: { linkUtil: number[] }) {
  const width = 640;
  const height = 220;
  const attackerX = 40;
  const switchX = 220;
  const victimX = 560;
  const midY = height / 2;

  return (
    <div className="panel p-4">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Network topology">
        <text x={attackerX} y={midY - 40} fontSize={12} fill="var(--color-text)" textAnchor="middle">
          attacker
        </text>
        <circle cx={attackerX} cy={midY} r={16} fill="var(--color-info)" />

        <line x1={attackerX + 16} y1={midY} x2={switchX - 16} y2={midY} stroke="var(--color-border)" strokeWidth={2} />

        <text x={switchX} y={midY - 40} fontSize={12} fill="var(--color-text)" textAnchor="middle">
          switch (s1)
        </text>
        <rect x={switchX - 16} y={midY - 16} width={32} height={32} fill="var(--color-primary)" rx={4} />

        {linkUtil.map((util, i) => {
          const linkY = 40 + i * ((height - 80) / Math.max(1, linkUtil.length - 1));
          const saturated = util >= SATURATION_UTILISATION;
          return (
            <g key={i}>
              <line
                x1={switchX + 16}
                y1={midY}
                x2={victimX - 60}
                y2={linkY}
                stroke={saturated ? "var(--color-danger)" : "var(--color-success)"}
                strokeWidth={4}
              />
              <text x={victimX - 90} y={linkY - 6} fontSize={10} fill="var(--color-text)" textAnchor="middle">
                link{i} {Math.round(util * 100)}%
              </text>
            </g>
          );
        })}

        <text x={victimX} y={midY - 40} fontSize={12} fill="var(--color-text)" textAnchor="middle">
          victim
        </text>
        <circle cx={victimX - 40} cy={midY} r={16} fill="var(--color-warning)" />
      </svg>
    </div>
  );
}
