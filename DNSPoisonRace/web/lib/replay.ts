// Typed loaders for P5's frozen replay JSON (public/replay/*.json). Each fetch
// applies the basePath prefix inline -- assetPrefix does NOT rewrite fetch()
// (plan P6 lib/replay.ts). Types match the frozen replay contract.

export type SourceKind = "fixed" | "prng" | "csprng" | "qrng";

export interface CliffPoint {
  effective_bits: number;
  poison_rate: number;
}

export interface CliffData {
  sources: Record<SourceKind, CliffPoint[]>;
  send_rate_pps: number;
}

export interface CollapsePoint {
  k: number;
  poison_rate: number;
}

export interface CollapseData {
  kind: string;
  series: CollapsePoint[];
}

export interface RaceScenario {
  kind: string;
  seed: number;
  txid_bits: number;
  port_bits: number;
  k: number;
  send_rate_pps: number;
  rtt: number;
  retransmit: number;
  parallel_queries: number;
  outcome: string;
  t_outcome: number;
  forged_packets: number;
}

const base = () => process.env.NEXT_PUBLIC_BASE_PATH ?? "";

async function fetchJson<T>(name: string): Promise<T> {
  const response = await fetch(`${base()}/replay/${name}.json`);
  if (!response.ok) {
    throw new Error(`replay recording not found: ${name} (P5 has not landed this recording yet)`);
  }
  return (await response.json()) as T;
}

export async function loadCliff(): Promise<CliffData> {
  return fetchJson<CliffData>("cliff");
}

export async function loadCollapse(): Promise<CollapseData> {
  return fetchJson<CollapseData>("collapse");
}

// P5 exported race_fixed|prng|csprng.json but not race_qrng.json (qrng defends
// identically to csprng at k=0 -- the null result); fall back to the csprng
// descriptor relabelled as qrng so the demo renders all four sources honestly.
export async function loadRaceScenario(kind: SourceKind): Promise<RaceScenario> {
  try {
    return await fetchJson<RaceScenario>(`race_${kind}`);
  } catch (err) {
    if (kind === "qrng") {
      const csprng = await fetchJson<RaceScenario>("race_csprng");
      return { ...csprng, kind: "qrng" };
    }
    throw err;
  }
}
