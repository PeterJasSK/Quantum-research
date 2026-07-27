"use client";

import { jainsIndex, polarizationIndex } from "@/lib/fairness";

/** Jain's-index gauge + polarization index + a per-link bar strip, all
 * recomputed in-browser from the real bucketed link-load counts (plan-8
 * Deliverable B) -- no fabricated numbers. */
export default function FairnessReadout({ linkLoad }: { linkLoad: number[] }) {
  const jains = jainsIndex(linkLoad);
  const polarization = polarizationIndex(linkLoad);
  const maxLoad = Math.max(1, ...linkLoad);

  return (
    <div className="panel flex flex-col gap-3 p-4">
      <h3 className="text-sm font-semibold text-(--color-heading)">Fairness</h3>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm text-(--color-text)">
        <dt>Jain&apos;s index</dt>
        <dd className="font-(family-name:--font-mono)">{jains.toFixed(3)}</dd>
        <dt>Polarization (max/mean)</dt>
        <dd className="font-(family-name:--font-mono)">{polarization.toFixed(3)}</dd>
      </dl>
      <div className="flex flex-wrap items-end gap-1 h-16">
        {linkLoad.map((load, i) => (
          <div
            key={i}
            className="w-2 rounded-t bg-(--color-primary)"
            style={{ height: `${Math.max(2, (load / maxLoad) * 100)}%` }}
            title={`link ${i}: ${load} flows`}
          />
        ))}
      </div>
    </div>
  );
}
