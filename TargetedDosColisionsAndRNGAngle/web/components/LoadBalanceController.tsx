"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import LiveFatTree from "./LiveFatTree";
import FairnessReadout from "./FairnessReadout";
import AttackPanel from "./AttackPanel";
import ProvenancePanel from "./ProvenancePanel";
import QeaasCallout from "./QeaasCallout";
import {
  attackForce,
  buildFattree,
  buildTrafficPlan,
  craftAttackFlows,
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

// CSPRNG stays a fully working module (mint, notes, routing all intact) but is
// hidden from the selector — the demo contrasts weak PRNG vs QEaaS/QRNG.
const HIDDEN_SOURCES: SaltSourceId[] = ["csprng"];
// QRNG leads the selector: the demo opens on the QEaaS solution, then lets the
// visitor flip to the weak PRNG to see the failure it fixes.
const VISIBLE_ORDER: SaltSourceId[] = ["qrng", "weak-prng"];
const VISIBLE_SOURCES = VISIBLE_ORDER.map(
  (id) => SALT_SOURCES.find((s) => s.id === id)!,
).filter((s) => !HIDDEN_SOURCES.includes(s.id));

const SOURCE_NOTE: Record<SaltSourceId, string> = {
  "weak-prng":
    "A weak PRNG has a short period, so it only ever emits a handful of distinct salts — here just 3, reused across all ~47 switches (a realistic same-image-same-seed fleet). Many switches share a key, so per-flow choices on stacked switches correlate: flows funnel onto the same links while parallel links sit idle. It is also guessable — which is exactly what the collision attacker on the right needs.",
  csprng:
    "Each switch draws its own independent CSPRNG salt. Hash choices are uncorrelated, so flows fan out and the collision attack scatters. It works — but the entropy is opaque: nothing proves where each salt came from, how fresh it was, or that it was ever truly random. Nothing to hand an auditor.",
  qrng:
    "Each switch pulls an independent salt from QRNG entropy delivered by QEaaS (qeaas.eu). Traffic fans out and the attack scatters — and every draw ships with a signed provenance receipt (entropy epoch, request id, attestable quantum source), shown below. Provably-sourced, auditable randomness delivered as a service: the piece the fabric was missing.",
};

function mintFor(source: SaltSourceId): () => string {
  // Both csprng and qrng mint an independent salt per switch client-side; QRNG's
  // distinguishing value is the attestable provenance receipt it ships with, not
  // a different spread. (Balancing parity between the two is a footnote, not the
  // headline — see the provenance panel and README.)
  if (source !== "weak-prng") return csprngSaltHex;
  // weak PRNG: cycle a tiny pool so many switches share the same few salts.
  let i = 0;
  return () => weakPrngSaltHex(1 + (i++ % WEAK_POOL));
}

/** Unified live stage: a full k=6 fat-tree with packets continuously flowing
 * along the real ECMP-hashed routes (the load-balancing story), and — when the
 * attacker is launched — one host firing a crafted collision flood at a victim.
 * The salt source drives BOTH: weak/predictable salt polarizes balancing AND
 * lets the attacker lock a link; CSPRNG/QRNG spreads traffic AND scatters the
 * attack. QRNG's only extra is provenance. */
export default function LoadBalanceController() {
  const [source, setSource] = useState<SaltSourceId>("qrng");
  const [routes, setRoutes] = useState<string[][]>([]);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [linkLoad, setLinkLoad] = useState<number[]>([]);

  const [attack, setAttack] = useState(false);
  const [attackRoutes, setAttackRoutes] = useState<string[][]>([]);
  const [targetLink, setTargetLink] = useState<string | undefined>();
  const [collisionSetSize, setCollisionSetSize] = useState(0);
  const [scanned, setScanned] = useState(0);
  const [onTargetFraction, setOnTargetFraction] = useState(0);
  const [computingAttack, setComputingAttack] = useState(false);

  const fabric = useMemo(() => buildFattree(), []);
  // Seeded once, reused for every salt source -> identical traffic every run.
  const traffic = useMemo(() => buildTrafficPlan(fabric), [fabric]);
  const force = useMemo(() => attackForce(fabric), [fabric]);

  // Recompute the ordered node paths for every flow under the current salts:
  // east-west host<->host traffic plus north-south egress to the WAN gateways.
  // When the attacker is on, also build its crafted flood — solved against the
  // salt the attacker *believes* (== real salt only when it is predictable).
  useEffect(() => {
    let cancelled = false;
    const salts = fabricSalts(source, fabric, mintFor(source));
    // Attacker's belief: it can reconstruct a weak/guessable salt, but never a
    // fresh CSPRNG/QRNG draw -> model that as an independent (wrong) salt set.
    const believedSalts =
      source === "weak-prng" ? salts : fabricSalts("csprng", fabric, csprngSaltHex);
    (async () => {
      setComputingAttack(attack);
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
      if (cancelled) return;
      setRoutes(paths);

      if (attack) {
        const plan = await craftAttackFlows(fabric, salts, believedSalts, force);
        if (cancelled) return;
        setAttackRoutes(plan.routes);
        setTargetLink(plan.targetLink);
        setCollisionSetSize(plan.collisionSetSize);
        setScanned(plan.scanned);
        setOnTargetFraction(plan.onTargetFraction);
        setComputingAttack(false);
      } else {
        setAttackRoutes([]);
        setTargetLink(undefined);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source, fabric, traffic, force, attack]);

  // LiveFatTree samples cumulative counts ~2.5x/sec.
  const onSample = useCallback((cumulative: number[]) => {
    setLinkLoad(cumulative);
  }, []);

  // Live congestion on the victim's target link, sampled from the real flowing
  // packets (linkLoad updates ~2.5x/sec): the busiest-link-relative load on the
  // link the attacker is hammering. Rises toward 1.0 as the flood piles up under
  // a predictable salt; stays low when the flood scatters. Purely a live display
  // — the locked/scattered verdict uses the exact onTargetFraction instead.
  const liveCongestion = useMemo(() => {
    if (!targetLink || linkLoad.length === 0) return 0;
    const idx = fabric.linkIds.indexOf(targetLink);
    if (idx < 0) return 0;
    const max = Math.max(1, ...linkLoad);
    return linkLoad[idx] / max;
  }, [targetLink, linkLoad, fabric]);

  const targetLinkLabel = targetLink ? targetLink.replace("-", " ↔ ") : "—";

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-10 px-6 py-10">
      {/* ---- hero ---- */}
      <header className="flex flex-col gap-6">
        <span className="eyebrow">
          <span className="eyebrow-rule" />
          ECMP salt-collision link flooding · a rotation-cadence defence
        </span>
        <h1 className="hero-title max-w-4xl">
          The attacker <span className="hero-accent">in the gap</span>.
        </h1>
        <p className="max-w-3xl text-base leading-relaxed text-(--color-text)">
          Data-center fabrics spread traffic across parallel links by hashing each flow with a secret{" "}
          <em>salt</em>. Guess that salt and you can hand-pick flows that <strong>all hash to the same link</strong> —
          then a <strong>single host, no botnet</strong>, floods that one link and starves a victim, slipping clean
          under the rate limits and connection caps built to stop volumetric floods.
        </p>
        <p className="max-w-3xl text-base leading-relaxed text-(--color-text)">
          The fix is to keep moving the target: <strong>rotate the salt faster than the attacker can reconstruct
          it</strong> — a cadence you can actually compute, not folklore. This live lab lets you watch the attack
          land under a weak, guessable salt, then dissolve the moment the salt becomes strong and fresh. Serving that
          entropy through <strong>QEaaS</strong> adds the last piece: every salt draw ships a signed receipt proving
          where the randomness came from.
        </p>

        <div className="flex flex-wrap gap-2">
          <span className="chip">single-host DoS · no botnet</span>
          <span className="chip">evades rate limits</span>
          <span className="chip">computable rotation cadence</span>
          <span className="chip">signed quantum entropy</span>
        </div>
      </header>

      <div className="hairline" />

      {/* ---- controls ---- */}
      <section className="flex flex-col gap-4">
        <span className="eyebrow">
          <span className="eyebrow-rule" />
          Entropy source
        </span>
        <div className="panel flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Salt source selector">
            {VISIBLE_SOURCES.map((s) => (
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
          {routes.length === 0 && <span className="text-xs text-(--color-text)">computing routes…</span>}
        </div>
      </section>

      {/* ---- live stage ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <span className="eyebrow">
            <span className="eyebrow-rule" />
            Live fabric
          </span>
          <span className="text-xs text-(--color-text) opacity-70">
            main stage · load balancing &nbsp;|&nbsp; side panel · precision collision attacker
          </span>
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="flex flex-col gap-6">
          <LiveFatTree
            fabric={fabric}
            routes={routes}
            attackRoutes={attackRoutes}
            attacker={force.attacker}
            victim={force.victim}
            targetLink={targetLink}
            running={running}
            speed={speed}
            onSample={onSample}
          />
          <FairnessReadout linkLoad={linkLoad} />

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { n: "47", l: "switches (+2 WAN)" },
              { n: "36", l: "hosts" },
              { n: "9", l: "equal-cost paths / pod" },
              { n: "100%", l: "attestable QRNG draws" },
            ].map((s) => (
              <div key={s.l} className="panel card-hover flex flex-col gap-1 p-4">
                <span className="stat-num">{s.n}</span>
                <span className="stat-label">{s.l}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-6">
          <AttackPanel
            enabled={attack}
            onToggle={setAttack}
            predictable={source === "weak-prng"}
            attackerIp={fabric.hostToIp[force.attacker]}
            victimIp={fabric.hostToIp[force.victim]}
            targetLinkLabel={targetLinkLabel}
            collisionSetSize={collisionSetSize}
            scanned={scanned}
            concentration={onTargetFraction}
            liveCongestion={liveCongestion}
            computing={computingAttack}
          />
          <ProvenancePanel visible={source === "qrng"} />
          </div>
        </div>
      </section>

      {/* ---- explainer ---- */}
      <section className="flex flex-col gap-4">
        <span className="eyebrow">
          <span className="eyebrow-rule" />
          How it works
        </span>
        <div className="panel card-hover flex flex-col gap-3 p-6 text-sm leading-relaxed text-(--color-text)">
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
          <strong>The attacker.</strong> When launched, the{" "}
          <span className="font-semibold text-(--color-danger)">red-ringed</span> host{" "}
          (<span className="font-semibold text-(--color-danger)">ATTACKER</span>) floods the{" "}
          <span className="font-semibold text-(--color-info)">VICTIM</span> with crafted flows — all share one
          destination, only the source port varies. It sweeps source ports <em>offline</em> to find a{" "}
          <em>collision set</em>: ports whose ECMP hash steers the flow onto the <em>same</em> deep
          core→aggregation link (the dashed <span className="text-(--color-danger)">target link</span>), chosen deep
          in the fabric precisely because that is the tier ECMP is meant to spread load across (9 equal-cost paths
          into the victim&apos;s pod here). Under a predictable salt every crafted flow converges there — a red funnel
          collapses onto the victim while the rest of the fabric stays calm. Under CSPRNG/QRNG the attacker&apos;s
          guessed salt is wrong, the same ports hash to random paths, and the flood sprays across all 9 links —
          each carrying a negligible slice. A single host targeting one link, no botnet.
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
        <p>
          <strong>Where QEaaS comes in.</strong> Weak entropy is the root cause of both failures above — the
          polarized fabric and the landed attack. Fixing it means every switch needs an <em>independent, strong,
          fresh</em> salt, and in a regulated or multi-tenant setting you also need to <em>prove</em> it was. QEaaS
          serves exactly that: per-switch quantum entropy over a simple API, each draw stamped with a signed
          provenance receipt (entropy epoch, request id, attestable source) you can hand an auditor. Select{" "}
          <strong>QRNG</strong> above to see the receipt live — strong balancing, scattered attack, and a paper trail
          for the randomness underneath it.
        </p>
        <p className="text-xs italic opacity-80">
          Footnotes (honest scope). (1) Single-switch caveat: entropy quality is invisible at one hop — SHA-256
          spreads uniformly for any salt; polarization is a multi-stage effect that only appears when switches on a
          path share a salt. (2) In this threat model a good CSPRNG spreads traffic and blunts the attack just as
          well as QRNG; QRNG&apos;s distinguishing contribution here is attestable provenance and deliver-as-a-service
          deployability, not a better hash.
        </p>
        </div>
      </section>

      <div className="hairline" />

      {/* ---- QEaaS product callout (findings-grounded) ---- */}
      <QeaasCallout />
    </div>
  );
}
