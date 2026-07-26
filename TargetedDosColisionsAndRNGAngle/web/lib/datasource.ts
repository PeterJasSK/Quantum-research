// AC-5: one interface, three impls -- same front-end, swappable data source.
// Tier A ships `sim` only (pure JS/TS, no infra). `live`/`replay` are Tier B
// scaffolding: interfaces exist now so components never need to change when
// Tier B lands, but they are not wired to real infra yet (see plan
// §Dependencies -- P4 has no WS layer today, P5 has not landed a replay set).
import { N_LINKS, SATURATION_UTILISATION, VICTIM_COLLAPSE_MBPS, LINK_CAPACITY_MBPS } from "./constants";

export interface SceneSample {
  linkUtil: number[]; // length N_LINKS, 0..1
  victimMbps: number;
  jainsIndex: number;
  rateLimiterActive: boolean;
  throttleActive: boolean;
}

export interface DataSource {
  kind: "sim" | "live" | "replay";
  sample(): SceneSample;
}

function jainsIndexOf(values: number[]): number {
  const sum = values.reduce((a, b) => a + b, 0);
  const sumSquares = values.reduce((a, b) => a + b * b, 0);
  if (sumSquares === 0) return 1;
  return (sum * sum) / (values.length * sumSquares);
}

/** Tier A: in-browser simulation driven by bucket-spread counts (see lib/ecmp.ts). */
export function simSampleFromBucketCounts(
  bucketCounts: number[],
  rateLimiterActive: boolean,
  throttleActive: boolean,
): SceneSample {
  const maxCount = Math.max(1, ...bucketCounts);
  const linkUtil = bucketCounts.map((c) => Math.min(1, c / (maxCount * (1 / SATURATION_UTILISATION))));
  const saturated = linkUtil.some((u) => u >= SATURATION_UTILISATION);
  const victimMbps = saturated ? VICTIM_COLLAPSE_MBPS * 0.3 : LINK_CAPACITY_MBPS * 0.8;
  return {
    linkUtil,
    victimMbps,
    jainsIndex: jainsIndexOf(bucketCounts.length ? bucketCounts : new Array(N_LINKS).fill(1)),
    rateLimiterActive,
    throttleActive,
  };
}

/** Tier B live (not implemented): would read from lib/ws.ts's controller stream. */
export function createLiveDataSource(): DataSource {
  return {
    kind: "live",
    sample() {
      throw new Error(
        "Tier B live data source is not wired yet -- no WebSocket server exists on the controller (plan OQ-2).",
      );
    },
  };
}

/** Tier B replay (not implemented): would read public/replay/*.json from P5. */
export function createReplayDataSource(): DataSource {
  return {
    kind: "replay",
    sample() {
      throw new Error(
        "Tier B replay data source is not wired yet -- P5 has not landed a recorded sweep subset.",
      );
    },
  };
}
