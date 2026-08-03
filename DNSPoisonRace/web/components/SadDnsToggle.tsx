"use client";

import { PORT_BITS } from "@/lib/constants";

/** SAD-DNS reveal (AC-6.3): a labelled toggle plus a k-bit slider. Kept a
 * separate control so the side-channel leak reads as a deliberate action --
 * raising k narrows the port entropy the attacker must guess, collapsing the
 * "safe" curve. Pure presentation; the parent owns the state. */
export default function SadDnsToggle({
  on,
  k,
  onToggle,
  onK,
}: {
  on: boolean;
  k: number;
  onToggle: (on: boolean) => void;
  onK: (k: number) => void;
}) {
  return (
    <div className="panel flex flex-col gap-3 p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-(--color-heading)">SAD-DNS side channel</span>
          <span className="text-xs text-(--color-text) opacity-75">
            Leak <span className="font-(family-name:--font-mono)">k</span> port bits via the ICMP rate-limit oracle
          </span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          onClick={() => onToggle(!on)}
          className={`relative h-7 w-12 shrink-0 rounded-full border border-(--color-border) transition-colors ${
            on ? "bg-(--color-danger)" : "bg-(--color-surface)"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-(--color-bg) transition-all ${
              on ? "left-[1.55rem]" : "left-0.5"
            }`}
          />
        </button>
      </div>
      <label className={`flex items-center gap-3 text-xs text-(--color-text) ${on ? "" : "opacity-40"}`}>
        <span className="w-24 shrink-0">
          leaked bits <span className="font-(family-name:--font-mono)">k = {k}</span>
        </span>
        <input
          type="range"
          min={0}
          max={PORT_BITS}
          step={1}
          value={k}
          disabled={!on}
          onChange={(e) => onK(Number(e.target.value))}
          aria-label="SAD-DNS leaked port bits (k)"
          className="min-w-0 flex-1"
        />
      </label>
      <p className={`text-xs italic text-(--color-text) ${on ? "opacity-80" : "opacity-50"}`}>
        {on
          ? "The port draw is no longer fully secret: effective entropy falls by k bits, dragging the safe CSPRNG curve toward the guessable line."
          : "Off: the resolver's source port is fully random. Flip it on to watch the side channel collapse the safe curve."}
      </p>
    </div>
  );
}
