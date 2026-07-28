"use client";

import { jainsIndex, polarizationIndex } from "@/lib/fairness";

/** Jain's-index gauge + polarization index + a per-link bar strip, all
 * recomputed in-browser from the real bucketed link-load counts (plan-8
 * Deliverable B) -- no fabricated numbers. The strip flex-scales every link
 * into ONE row (no wrap), so a large fabric (~126 links at k=6) reads as a
 * single live histogram; bars tint green -> amber -> red by relative load so
 * hot spots / polarization are visible at a glance. */
export default function FairnessReadout({ linkLoad }: { linkLoad: number[] }) {
  const jains = jainsIndex(linkLoad);
  const polarization = polarizationIndex(linkLoad);
  const maxLoad = Math.max(1, ...linkLoad);

  const barColor = (frac: number) =>
    frac > 0.66 ? "var(--color-danger)" : frac > 0.33 ? "var(--color-warning)" : "var(--color-success)";

  return (
    <div className="panel card-hover flex flex-col gap-4 p-5">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-sm font-semibold text-(--color-heading)">Fairness</h3>
        <div className="flex gap-6">
          <div className="flex flex-col items-end">
            <span className="stat-num text-lg">{jains.toFixed(3)}</span>
            <span className="stat-label">Jain&apos;s index</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="stat-num text-lg">{polarization.toFixed(3)}</span>
            <span className="stat-label">polarization (max/mean)</span>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex h-24 w-full items-end gap-px overflow-hidden">
          {linkLoad.map((load, i) => {
            const frac = load / maxLoad;
            return (
              <div
                key={i}
                className="min-w-[2px] flex-1 rounded-t transition-[height] duration-300"
                style={{ height: `${Math.max(2, frac * 100)}%`, background: barColor(frac) }}
                title={`link ${i}: ${load} flows`}
              />
            );
          })}
        </div>
        <span className="text-[11px] text-(--color-text) opacity-60">
          {linkLoad.length} fabric links · height = share of delivered traffic
        </span>
      </div>
    </div>
  );
}
