// Derivation layer between the controller's slider state and the vendored race
// mirror. Keeps ALL business logic out of JSX (plan hard constraint): the
// components receive a ready-built trace and only render it.
//
// NOTE ON SCOPE: this powers the *display* animation only. The parity gate
// (scripts/check-parity.mjs over lib/raceVectors.json) is what proves the JS
// race reproduces the Python outcomes; the visual space-shrinking heuristics
// below never touch that gate.
import { buildFloodVector, type FloodVector } from "@/lib/raceCore";
import type { RaceScenario, SourceKind } from "@/lib/replay";
import { RTT_JITTER_FRAC } from "@/lib/constants";

export interface ControllerState {
  source: SourceKind;
  effectiveBits: number;
  sadDnsOn: boolean;
  sadDnsLeakK: number;
  parallelQueries: number;
}

// Weak sources have a short period, so a fixed number of forged guesses covers a
// larger fraction of their *effective* space -- modelled as an entropy penalty so
// fixed/prng poison at higher slider positions than csprng/qrng (the epic story;
// display-only, never the parity path).
const SOURCE_PENALTY: Record<SourceKind, number> = {
  fixed: 8,
  prng: 4,
  csprng: 0,
  qrng: 0,
};

export interface DerivedTrace {
  trace: FloodVector;
  target: number; // effective index of the one correct cell
  spaceBits: number; // total guess-space bits used for the animation
  txidBits: number;
  portBits: number;
}

/** Build the animated flood trace for the current controller state from a P5
 * race descriptor. `trace=true` so raceCore emits the event list + windows_spec
 * the canvas/heatmap animate. */
export function deriveTrace(scenario: RaceScenario, state: ControllerState): DerivedTrace {
  const penalty = SOURCE_PENALTY[state.source];
  const leak = state.sadDnsOn ? state.sadDnsLeakK : 0;
  // Effective guess-space bits for the animation: the entropy slider, minus the
  // source-quality penalty, minus the SAD-DNS side-channel leak (raising k
  // collapses the space -> more poisoning).
  const spaceBits = Math.max(4, Math.min(32, state.effectiveBits - penalty - leak));

  const portBits = Math.min(16, spaceBits);
  const txidBits = spaceBits - portBits;
  const spaceSize = 2 ** spaceBits;

  // Fixed target roughly 0.37 into the space; split into (txid, port) so
  // buildFloodVector recomputes the same effective index.
  const targetIndex = Math.floor(spaceSize * 0.37);
  const portSpan = 2 ** portBits;
  const txid = Math.floor(targetIndex / portSpan);
  const port = targetIndex % portSpan;

  const trace = buildFloodVector(
    {
      seed: scenario.seed,
      txid,
      port,
      txid_bits: txidBits,
      port_bits: portBits,
      k: 0,
      rtt: scenario.rtt,
      retransmit: scenario.retransmit,
      send_rate_pps: scenario.send_rate_pps,
      parallel_queries: state.parallelQueries,
      retransmit_rounds: 1,
      rtt_jitter_frac: RTT_JITTER_FRAC,
    },
    true,
  );

  return { trace, target: targetIndex, spaceBits, txidBits, portBits };
}
