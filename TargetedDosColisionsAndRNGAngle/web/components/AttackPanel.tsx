"use client";

/** Side-stage control + live readout for the precision collision attacker that
 * runs *inside* the main fat-tree. Drives the attack on/off, shows the crafted
 * flood's parameters, and reports — from the real delivered-packet counts —
 * whether the crafted flows locked onto the target link (predictable salt) or
 * scattered harmlessly (CSPRNG/QRNG). */
export default function AttackPanel({
  enabled,
  onToggle,
  predictable,
  attackerIp,
  victimIp,
  targetLinkLabel,
  collisionSetSize,
  scanned,
  concentration,
  liveCongestion,
  computing,
}: {
  enabled: boolean;
  onToggle: (on: boolean) => void;
  predictable: boolean;
  attackerIp: string;
  victimIp: string;
  targetLinkLabel: string;
  collisionSetSize: number;
  scanned: number;
  concentration: number; // fraction of the flood that landed on the target link, 0..1
  liveCongestion: number; // live busiest-relative load on the victim's target link, 0..1
  computing: boolean;
}) {
  const locked = enabled && concentration > 0.5;
  const pct = Math.round(concentration * 100);
  const congPct = Math.round(liveCongestion * 100);
  const victimDown = liveCongestion >= 0.85;

  return (
    <aside className="panel card-hover flex flex-col gap-4 p-5">
      <div className="flex flex-col gap-1">
        <span className="eyebrow">
          <span className="eyebrow-rule" />
          Threat
        </span>
        <h2 className="text-lg font-semibold text-(--color-heading)">Precision collision attacker</h2>
      </div>

      <button
        type="button"
        onClick={() => onToggle(!enabled)}
        aria-pressed={enabled}
        className={`pill px-4 py-2 text-sm font-semibold ${enabled ? "text-(--color-danger)" : ""}`}
      >
        {enabled ? "■ stop attack" : "▶ launch attack"}
      </button>

      {!enabled ? (
        <p className="text-sm leading-relaxed text-(--color-text)">
          One compromised host in the fabric below floods a single victim with crafted flows, hunting for source
          ports whose ECMP hash steers every flow onto the <em>same</em> deep fabric link — funnelling the whole
          flood onto one physical link (of 9 equal-cost paths) to saturate it. Launch it and watch what the current
          salt source does to the attack.
        </p>
      ) : (
        <>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-(--color-text)">
            <dt className="font-semibold">attacker</dt>
            <dd className="font-(family-name:--font-mono) text-(--color-danger)">{attackerIp}</dd>
            <dt className="font-semibold">victim</dt>
            <dd className="font-(family-name:--font-mono) text-(--color-info)">{victimIp}</dd>
            <dt className="font-semibold">target link</dt>
            <dd className="break-all font-(family-name:--font-mono)">{targetLinkLabel}</dd>
            <dt className="font-semibold">collision set</dt>
            <dd className="font-(family-name:--font-mono)">
              {computing ? "searching…" : `${collisionSetSize} flows / ${scanned} scanned`}
            </dd>
          </dl>

          {/* LIVE tracker: how congested the victim's link is right now, from
              the real flowing packets. Climbs as the flood piles up. */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs text-(--color-text)">
              <span className="inline-flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span
                    className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
                    style={{ background: victimDown ? "var(--color-danger)" : "var(--color-success)" }}
                  />
                  <span
                    className="relative inline-flex h-2 w-2 rounded-full"
                    style={{ background: victimDown ? "var(--color-danger)" : "var(--color-success)" }}
                  />
                </span>
                victim link congestion (live)
              </span>
              <span className="font-(family-name:--font-mono)">{congPct}%</span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-(--color-border)">
              <div
                className="h-full rounded-full transition-[width] duration-500"
                style={{
                  width: `${congPct}%`,
                  background: victimDown
                    ? "var(--color-danger)"
                    : congPct > 45
                    ? "var(--color-warning)"
                    : "var(--color-success)",
                }}
              />
            </div>
            <span className="text-[11px] text-(--color-text) opacity-70">
              live load on the target link vs the fabric&apos;s busiest link
            </span>
          </div>

          <div className="flex items-center justify-between text-xs text-(--color-text)">
            <span>flood precision (on target link)</span>
            <span className="font-(family-name:--font-mono)">{computing ? "…" : `${pct}%`}</span>
          </div>

          <div
            className={`rounded-md px-3 py-2 text-sm font-semibold ${
              locked ? "text-(--color-danger)" : "text-(--color-success)"
            }`}
            role="status"
          >
            {locked ? "● LOCKED — one link saturated, victim starved" : "● SCATTERED — attack dissolved into background"}
          </div>

          <p className="text-sm leading-relaxed text-(--color-text)">
            {predictable ? (
              <>
                <strong>Predictable salt.</strong> The weak PRNG&apos;s salt is guessable, so the attacker solves the
                ECMP hash <em>offline</em>: every crafted flow picks the same aggregation and core switch and converges
                on the target link (dashed). The flood collapses into one red funnel down to the victim, whose
                legitimate traffic is starved. This is the targeted collision DoS.
              </>
            ) : (
              <>
                <strong>Unpredictable salt.</strong> Each switch draws an independent salt the attacker cannot know,
                so the same crafted flows hash to <em>random</em> aggregation/core choices and spray across all 9
                core→agg links into the victim&apos;s pod — each carries a small slice, no link saturates, the victim
                rides through. With <strong>QRNG via QEaaS</strong> every one of those salts also ships with a signed
                provenance receipt (below): the attack is defeated <em>and</em> the entropy is auditable.
                <span className="opacity-70"> (A strong CSPRNG defeats it equally — provenance is the extra.)</span>
              </>
            )}
          </p>
        </>
      )}
    </aside>
  );
}
