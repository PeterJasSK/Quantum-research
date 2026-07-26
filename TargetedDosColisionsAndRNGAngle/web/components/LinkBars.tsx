"use client";

import { SATURATION_UTILISATION } from "@/lib/constants";

export default function LinkBars({ linkUtil }: { linkUtil: number[] }) {
  return (
    <div className="panel flex flex-col gap-3 p-4">
      <h3 className="text-sm font-semibold text-(--color-heading)">Link utilisation</h3>
      <div className="flex items-end gap-3 h-32">
        {linkUtil.map((util, i) => {
          const pct = Math.round(Math.min(1, util) * 100);
          const saturated = util >= SATURATION_UTILISATION;
          return (
            <div key={i} className="flex flex-1 flex-col items-center gap-1">
              <div className="relative flex h-full w-full items-end rounded bg-(--color-border)">
                <div
                  className="w-full rounded transition-[height] duration-300"
                  style={{
                    height: `${pct}%`,
                    background: saturated ? "var(--color-danger)" : "var(--color-success)",
                  }}
                />
              </div>
              <span className="text-xs text-(--color-text)">
                link{i} {pct}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
