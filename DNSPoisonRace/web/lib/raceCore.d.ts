// Ambient types for the vendored CommonJS race mirror (lib/raceCore.js). Hand-
// written to give the authored TSX a typed surface without `any`; the .js itself
// is copied verbatim from testbed/vectors/race_core.js by vendor-p6.mjs and is
// never edited in web/.

export interface FloodParams {
  seed: number;
  txid: number;
  port: number;
  txid_bits: number;
  port_bits: number;
  k: number;
  rtt: number;
  retransmit: number;
  send_rate_pps: number;
  parallel_queries: number;
  retransmit_rounds: number;
  rtt_jitter_frac: number;
}

// One display-trace event. Compared fields are unaffected by the trace; `guess`
// is the effective index of a forged packet, `window` the poisoned window id.
export interface TraceEvent {
  time: number;
  kind: "forged" | "poisoned" | "resolved_legit";
  guess?: number;
  window?: number;
}

// A window round: [targetIndex, tOpen, tAuthoritative].
export type WindowRound = [number, number, number];

export interface FloodVector {
  seed: number;
  txid: number;
  port: number;
  eff_bits: number;
  rtt: number;
  retransmit: number;
  send_schedule: number[];
  parallel_queries: number;
  outcome: "poisoned" | "resolved_legit" | "window_closed";
  forged_packets: number;
  t_outcome: number;
  // display-only extras (present only when `trace` is truthy):
  windows_spec?: WindowRound[][];
  events?: TraceEvent[];
}

export function splitmix64(state: bigint): [bigint, bigint];
export function bounded(state: bigint, n: number): [number, bigint];

export class GuessStream {
  constructor(spaceSize: number, state: bigint | number);
  spaceSize: number;
  state: bigint;
  resetRound(): void;
  next(): number;
}

export function sadDnsLeak(portBits: number, k: number): number;
export function effectiveBits(txidBits: number, portBits: number, k: number): number;

export function runRace(
  seed: number,
  draw: [number, number],
  forgedGuess: [number, number],
  rtt: number,
  sendSchedule: number[],
): { outcome: string; t_outcome: number; forged_packets: number };

export function buildFloodVector(params: FloodParams, trace?: boolean): FloodVector;
