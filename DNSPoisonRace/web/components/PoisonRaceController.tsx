"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import PoisonRaceCanvas from "./PoisonRaceCanvas";
import EntropyCliff from "./EntropyCliff";
import SadDnsToggle from "./SadDnsToggle";
import GuessSpaceHeatmap from "./GuessSpaceHeatmap";
import ProvenancePanel from "./ProvenancePanel";
import QeaasCallout from "./QeaasCallout";
import StructuredData from "./StructuredData";
import {
  loadCliff,
  loadCollapse,
  loadRaceScenario,
  type CliffData,
  type CollapseData,
  type RaceScenario,
  type SourceKind,
} from "@/lib/replay";
import { deriveTrace } from "@/lib/scenario";
import { EFF_BITS_MAX, EFF_BITS_MIN } from "@/lib/constants";
import { WEB_URL } from "@/lib/urls";

const SOURCES: { id: SourceKind; label: string }[] = [
  { id: "fixed", label: "fixed (constant)" },
  { id: "prng", label: "weak PRNG" },
  { id: "csprng", label: "CSPRNG" },
  { id: "qrng", label: "QRNG (QEaaS)" },
];

const SOURCE_NOTE: Record<SourceKind, string> = {
  fixed:
    "A fixed TXID/port means zero entropy — the poisoner knows the answer before it asks. The forged flood lands almost immediately.",
  prng:
    "A weak PRNG has a short period, so its effective guess space is far smaller than the nominal 32 bits. Poisoning stays feasible well up the entropy slider.",
  csprng:
    "A strong CSPRNG fills the full guess space: above the cliff the attacker's flood is hopeless. It defends the race — but proves nothing about where the randomness came from.",
  qrng:
    "QRNG entropy delivered by QEaaS defends the race identically to a strong CSPRNG — and every draw ships a signed provenance receipt (shown below). Same defence, plus a paper trail.",
};

const STRUCTURED_DATA = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "DNS Poison Race",
  applicationCategory: "SecurityApplication",
  operatingSystem: "Any",
  url: WEB_URL,
  description:
    "Interactive client-side visualization of a DNS cache-poisoning entropy race: forged-answer flood vs authoritative reply, entropy cliff, SAD-DNS side-channel reveal, guess-space heatmap, and a signed QRNG provenance receipt.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
};

interface RaceOutcome {
  outcome: string;
  t_outcome: number;
  forged_packets: number;
}

/** The whole page (AC-6.1–6.5). Owns all state, loads P5's replay JSON on mount,
 * derives the animated flood trace from the selected source's descriptor + the
 * slider state (all logic in lib/scenario + lib/raceCore — none in this JSX), and
 * wires state to the four canvases + provenance panel + QEaaS callout. */
export default function PoisonRaceController() {
  const [source, setSource] = useState<SourceKind>("csprng");
  const [effectiveBits, setEffectiveBits] = useState(EFF_BITS_MAX);
  const [sadDnsOn, setSadDnsOn] = useState(false);
  const [sadDnsLeakK, setSadDnsLeakK] = useState(8);
  const [parallelQueries, setParallelQueries] = useState(1);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(1);

  const [cliff, setCliff] = useState<CliffData | null>(null);
  const [collapse, setCollapse] = useState<CollapseData | null>(null);
  const [scenarios, setScenarios] = useState<Record<SourceKind, RaceScenario> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<RaceOutcome | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cliffData, collapseData, fixed, prng, csprng, qrng] = await Promise.all([
          loadCliff(),
          loadCollapse(),
          loadRaceScenario("fixed"),
          loadRaceScenario("prng"),
          loadRaceScenario("csprng"),
          loadRaceScenario("qrng"),
        ]);
        if (cancelled) return;
        setCliff(cliffData);
        setCollapse(collapseData);
        setScenarios({ fixed, prng, csprng, qrng });
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const derived = useMemo(() => {
    if (!scenarios) return null;
    return deriveTrace(scenarios[source], {
      source,
      effectiveBits,
      sadDnsOn,
      sadDnsLeakK,
      parallelQueries,
    });
  }, [scenarios, source, effectiveBits, sadDnsOn, sadDnsLeakK, parallelQueries]);

  const handleOutcome = useCallback((o: RaceOutcome) => setOutcome(o), []);

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-10 px-6 py-10">
      <StructuredData data={STRUCTURED_DATA} />

      {/* ---- hero ---- */}
      <header className="flex flex-col gap-6">
        <span className="eyebrow">
          <span className="eyebrow-rule" />
          DNS cache poisoning · an entropy race
        </span>
        <h1 className="hero-title max-w-4xl">
          How many entropy bits <span className="hero-accent">stop a cache poisoner?</span>
        </h1>
        <p className="max-w-3xl text-base leading-relaxed text-(--color-text)">
          When a resolver asks an authoritative server for a record, an off-path attacker can race it: spray forged
          answers guessing the resolver&apos;s 16-bit <strong>transaction ID</strong> and 16-bit <strong>source
          port</strong>. Guess both before the real reply lands and the lie is cached — every client that asks now gets
          the attacker&apos;s address.
        </p>
        <p className="max-w-3xl text-base leading-relaxed text-(--color-text)">
          The whole contest is entropy. Above the <strong>cliff</strong> the guess space is astronomically large and the
          flood loses; drop below it and poisoning is near-certain. This lab runs the race entirely in your browser —
          the same deterministic engine the Python testbed uses, gated on JS↔Python parity — so you can watch it, not
          just read about it.
        </p>
        <div className="flex flex-wrap gap-2">
          <span className="chip">off-path forged-answer flood</span>
          <span className="chip">TXID × port entropy</span>
          <span className="chip">SAD-DNS side channel</span>
          <span className="chip">signed quantum entropy</span>
        </div>
      </header>

      <div className="hairline" />

      {loadError && (
        <div className="panel p-5 text-sm text-(--color-danger)">
          Could not load the recorded replay data: {loadError}
        </div>
      )}

      {/* ---- controls ---- */}
      <section className="flex flex-col gap-4">
        <span className="eyebrow">
          <span className="eyebrow-rule" />
          Entropy source
        </span>
        <div className="panel flex flex-col gap-4 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <div className="flex flex-col gap-2 sm:flex-row" role="tablist" aria-label="Entropy source selector">
              {SOURCES.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  role="tab"
                  aria-selected={source === s.id}
                  onClick={() => setSource(s.id)}
                  className={`pill w-full px-3 py-2 text-xs sm:w-auto sm:px-4 sm:text-sm ${source === s.id ? "" : "opacity-70"}`}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-3 sm:gap-4">
              <button
                type="button"
                onClick={() => setRunning((r) => !r)}
                className="pill px-3 py-2 text-xs sm:px-4 sm:text-sm"
                aria-pressed={running}
              >
                {running ? "⏸ pause" : "▶ play"}
              </button>
              <label className="flex flex-1 items-center gap-2 text-xs text-(--color-text) sm:flex-none">
                speed
                <input
                  type="range"
                  min={0.25}
                  max={3}
                  step={0.25}
                  value={speed}
                  onChange={(e) => setSpeed(Number(e.target.value))}
                  aria-label="Animation speed"
                  className="min-w-0 flex-1 sm:flex-none"
                />
                <span className="w-8 shrink-0 font-(family-name:--font-mono)">{speed.toFixed(2)}×</span>
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-xs text-(--color-text)">
              <span>
                effective entropy bits ·{" "}
                <span className="font-(family-name:--font-mono)">{effectiveBits}</span>
              </span>
              <input
                type="range"
                min={EFF_BITS_MIN}
                max={EFF_BITS_MAX}
                step={1}
                value={effectiveBits}
                onChange={(e) => setEffectiveBits(Number(e.target.value))}
                aria-label="Effective entropy bits"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-(--color-text)">
              <span>
                parallel queries (birthday amplification) ·{" "}
                <span className="font-(family-name:--font-mono)">{parallelQueries}</span>
              </span>
              <input
                type="range"
                min={1}
                max={8}
                step={1}
                value={parallelQueries}
                onChange={(e) => setParallelQueries(Number(e.target.value))}
                aria-label="Parallel queries"
              />
            </label>
          </div>

          <p className="text-sm leading-relaxed text-(--color-text)">
            <strong>{SOURCES.find((s) => s.id === source)?.label}:</strong> {SOURCE_NOTE[source]}
          </p>
          {!derived && !loadError && <span className="text-xs text-(--color-text)">loading recorded race data…</span>}
        </div>
      </section>

      {/* ---- the race ---- */}
      {derived && (
        <>
          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <span className="eyebrow">
                <span className="eyebrow-rule" />
                The poison race
              </span>
              <span className="text-xs text-(--color-text) opacity-70">
                {outcome
                  ? `last outcome · ${outcome.outcome} @ t=${outcome.t_outcome.toFixed(3)}s · ${outcome.forged_packets.toLocaleString()} forged`
                  : "attacker flood vs authoritative reply"}
              </span>
            </div>
            <PoisonRaceCanvas trace={derived.trace} running={running} speed={speed} onOutcome={handleOutcome} />
          </section>

          <section className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_28rem]">
            <div className="flex flex-col gap-4">
              <span className="eyebrow">
                <span className="eyebrow-rule" />
                The entropy cliff
              </span>
              {cliff && collapse && (
                <EntropyCliff
                  cliff={cliff}
                  collapse={collapse}
                  source={source}
                  effectiveBits={effectiveBits}
                  sadDnsK={sadDnsLeakK}
                  sadDnsOn={sadDnsOn}
                />
              )}
              <SadDnsToggle on={sadDnsOn} k={sadDnsLeakK} onToggle={setSadDnsOn} onK={setSadDnsLeakK} />
            </div>
            <div className="flex flex-col gap-4">
              <span className="eyebrow">
                <span className="eyebrow-rule" />
                Guess-space heatmap
              </span>
              <GuessSpaceHeatmap
                trace={derived.trace}
                target={derived.target}
                spaceBits={derived.spaceBits}
                running={running}
                speed={speed}
              />
              <ProvenancePanel visible={source === "qrng"} />
            </div>
          </section>
        </>
      )}

      <div className="hairline" />

      {/* ---- QEaaS product callout ---- */}
      <QeaasCallout />
    </div>
  );
}
