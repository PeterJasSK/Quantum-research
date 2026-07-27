"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import LiveFatTree from "./LiveFatTree";
import FairnessReadout from "./FairnessReadout";
import ProvenancePanel from "./ProvenancePanel";
import {
  buildFattree,
  buildTrafficPlan,
  egressRouteNodes,
  fabricSalts,
  routeNodes,
} from "@/lib/fabric";
import { weakPrngSaltHex, csprngSaltHex } from "@/lib/salt";

// A weak PRNG with a short period only ever emits a handful of distinct salts.
const WEAK_POOL = 3;

const SALT_SOURCES = [
  { id: "weak-prng", label: "weak PRNG (shared salt)" },
  { id: "csprng", label: "CSPRNG (per-switch)" },
  { id: "qrng", label: "QRNG (per-switch)" },
] as const;

type SaltSourceId = (typeof SALT_SOURCES)[number]["id"];

const SOURCE_NOTE: Record<SaltSourceId, string> = {
  "weak-prng":
    "A weak PRNG has a short period, so it only ever emits a handful of distinct salts — here just 3, reused across all ~47 switches (a realistic same-image-same-seed fleet). Many switches share a key, so per-flow choices on stacked switches correlate: flows funnel onto the same links while parallel links sit idle. Watch the red hot spots and cold dead links appear side by side.",
  csprng:
    "Each switch draws its own independent CSPRNG salt. Hash choices at different hops are uncorrelated, so flows fan out across all parallel links. Watch the fabric stay uniformly warm — no persistent hot spots.",
  qrng:
    "Each switch draws an independent QRNG salt. Balancing is identical to CSPRNG (Experiment 4's null result) — the only extra QRNG buys is an attestable provenance receipt, shown below. It does not spread traffic 'better'.",
};

function mintFor(source: SaltSourceId): () => string {
  // Tier A: qrng shares csprng's client-side mint (both independent per switch).
  // QRNG's only extra is provenance, never "balances better".
  if (source !== "weak-prng") return csprngSaltHex;
  // weak PRNG: cycle a tiny pool so many switches share the same few salts.
  let i = 0;
  return () => weakPrngSaltHex(1 + (i++ % WEAK_POOL));
}

/** Plan-8 live demo: a full k=4 fat-tree with packets continuously flowing
 * along the real ECMP-hashed routes. Switching salt source re-derives every
 * switch's salt, recomputes routes, and restarts the stream so polarization
 * (weak PRNG) vs even balancing (CSPRNG/QRNG) is visible in motion. */
export default function LoadBalanceController() {
  const [source, setSource] = useState<SaltSourceId>("weak-prng");
  const [routes, setRoutes] = useState<string[][]>([]);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [linkLoad, setLinkLoad] = useState<number[]>([]);

  const fabric = useMemo(() => buildFattree(), []);
  // Seeded once, reused for every salt source -> identical traffic every run.
  const traffic = useMemo(() => buildTrafficPlan(fabric), [fabric]);

  // Recompute the ordered node paths for every flow under the current salts:
  // east-west host<->host traffic plus north-south egress to the WAN gateways.
  useEffect(() => {
    let cancelled = false;
    const salts = fabricSalts(source, fabric, mintFor(source));
    (async () => {
      setRoutes([]);
      setLinkLoad([]);
      const paths: string[][] = [];
      for (const flow of traffic.east) {
        const nodes = await routeNodes(fabric, salts, flow);
        if (nodes.length > 0) paths.push(nodes);
      }
      for (const flow of traffic.egress) {
        const nodes = await egressRouteNodes(fabric, salts, flow);
        if (nodes.length > 0) paths.push(nodes);
      }
      if (!cancelled) setRoutes(paths);
    })();
    return () => {
      cancelled = true;
    };
  }, [source, fabric, traffic]);

  // LiveFatTree samples cumulative counts ~2.5x/sec.
  const onSample = useCallback((cumulative: number[]) => {
    setLinkLoad(cumulative);
  }, []);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <header className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold text-(--color-heading)">
          Live load balancing — entropy quality vs ECMP hash polarization
        </h1>
        <p className="text-sm leading-relaxed text-(--color-text)">
          A <strong>k=6 fat-tree</strong> data-center fabric — 2 WAN gateways, 9 core, 18 aggregation and 18 edge
          switches, 36 hosts — under a realistic <em>skewed</em> traffic mix, <em>no attacker, no defences</em>.
          Random hosts open east-west connections biased toward a few popular &quot;server&quot; hosts, and a large
          share of traffic heads north-south out through the WAN gateways. The plan is <strong>seeded</strong>, so
          the exact same flows run on every test — only the salt changes. Each flow is hashed at every switch to
          pick one of the parallel upward links (ECMP); the quality of the random <em>salt</em> feeding that hash
          decides whether traffic spreads out or collapses onto a few overloaded links.
        </p>
      </header>

      <div className="panel flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Salt source selector">
            {SALT_SOURCES.map((s) => (
              <button
                key={s.id}
                type="button"
                role="tab"
                aria-selected={source === s.id}
                onClick={() => setSource(s.id)}
                className={`pill px-4 py-2 text-sm ${source === s.id ? "" : "opacity-70"}`}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setRunning((r) => !r)}
              className="pill px-4 py-2 text-sm"
              aria-pressed={running}
            >
              {running ? "⏸ pause" : "▶ play"}
            </button>
            <label className="flex items-center gap-2 text-xs text-(--color-text)">
              speed
              <input
                type="range"
                min={0.25}
                max={3}
                step={0.25}
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                aria-label="Animation speed"
              />
              <span className="w-8 font-(family-name:--font-mono)">{speed.toFixed(2)}×</span>
            </label>
          </div>
        </div>

        <p className="text-sm leading-relaxed text-(--color-text)">
          <strong>{SALT_SOURCES.find((s) => s.id === source)?.label}:</strong> {SOURCE_NOTE[source]}
        </p>
        {routes.length === 0 && (
          <span className="text-xs text-(--color-text)">computing routes…</span>
        )}
      </div>

      <LiveFatTree fabric={fabric} routes={routes} running={running} speed={speed} onSample={onSample} />

      <FairnessReadout linkLoad={linkLoad} />

      <ProvenancePanel visible={source === "qrng"} />

      <section className="panel flex flex-col gap-3 p-5 text-sm leading-relaxed text-(--color-text)">
        <h2 className="text-lg font-semibold text-(--color-heading)">What am I looking at?</h2>
        <p>
          <strong>The topology (top to bottom).</strong> Hosts sit at the bottom. Each host connects up to one{" "}
          <span className="font-semibold text-(--color-warning)">edge</span> switch (top-of-rack). Edge switches
          connect up to the <span className="font-semibold text-(--color-info)">aggregation</span> switches in
          their pod, which connect up to the <span className="font-semibold text-(--color-primary)">core</span>{" "}
          spine that links pods together. At the very top, the core uplinks to a small{" "}
          <span className="font-semibold text-(--color-primary)">WAN gateway</span> tier — the border routers that
          carry internet-bound (north-south) traffic out of the datacenter. There are multiple parallel links at
          every tier — that redundancy is exactly what ECMP is meant to load-balance across.
        </p>
        <p>
          <strong>The packets.</strong> Each moving dot is a flow being forwarded. It climbs host → edge → agg →
          (for cross-pod traffic) core, then descends the mirror path down to the destination host. The route each
          packet takes is <em>not</em> random per-packet — it is the deterministic ECMP hash of that flow&apos;s
          5-tuple, keyed by each switch&apos;s salt. Same flow, same path every time (flow affinity).
        </p>
        <p>
          <strong>The link colours.</strong> A link&apos;s tint shows its <em>cumulative</em> share of traffic:
          <span className="font-semibold text-(--color-success)"> green</span> = lightly used,
          <span className="font-semibold text-(--color-warning)"> amber</span> = busy,
          <span className="font-semibold text-(--color-danger)"> red</span> = saturated. Links also thicken with
          live packet occupancy. Under the weak shared salt you will see a handful of links go red while others
          stay dim — that is <strong>hash polarization</strong>: correlated hash choices across stacked switches
          funnel unrelated flows onto the same physical links. Under CSPRNG/QRNG the whole fabric stays evenly
          warm.
        </p>
        <p>
          <strong>The fairness numbers.</strong> <em>Jain&apos;s index</em> is 1.0 when every link carries an equal
          share and drops toward 0 as load concentrates. <em>Polarization</em> is the busiest link&apos;s load
          divided by the mean — 1.0 is perfect, higher means worse hot spots. Both are computed live from the real
          delivered-packet counts, not scripted. Note: because the traffic itself is skewed (popular servers),
          even CSPRNG won&apos;t hit a perfect 1.0 — what matters is the <em>gap</em>: the weak PRNG is clearly
          worse, adding hash polarization on top of the natural skew.
        </p>
        <p className="text-xs italic">
          Single-switch caveat: entropy quality is invisible at one hop — SHA-256 spreads uniformly for any salt.
          Polarization is a multi-stage effect: only when two switches on a path share a salt do their hash choices
          correlate. The weak-PRNG case models a short-period generator emitting only a few distinct salts reused
          across the fleet; CSPRNG/QRNG use an independent salt per switch. QRNG&apos;s only advantage over CSPRNG
          is attestable provenance, not better balancing (Experiment 4 null result).
        </p>
      </section>
    </div>
  );
}
