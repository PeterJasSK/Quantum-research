"use client";

import { LINK_CAPACITY_MBPS, VICTIM_COLLAPSE_MBPS } from "@/lib/constants";

export default function VictimThroughput({ victimMbps }: { victimMbps: number }) {
  const collapsed = victimMbps <= VICTIM_COLLAPSE_MBPS;
  const pct = Math.round(Math.min(1, victimMbps / LINK_CAPACITY_MBPS) * 100);
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-(--color-heading)">Victim throughput</h3>
      <div className="h-4 w-full rounded bg-(--color-border)">
        <div
          className="h-4 rounded transition-[width] duration-300"
          style={{
            width: `${pct}%`,
            background: collapsed ? "var(--color-danger)" : "var(--color-success)",
          }}
        />
      </div>
      <span className="text-xs text-(--color-text)">
        {victimMbps.toFixed(2)} Mbps -- {collapsed ? "collapsed" : "healthy"}
      </span>
    </div>
  );
}
