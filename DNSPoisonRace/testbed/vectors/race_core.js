// Source-of-truth JS mirror of the Python race engine (epic §3.6, plan P6).
//
// This file lives beside `gen_race_vectors.py` so the Python and JS races are
// reviewed together; `web/scripts/vendor-p6.mjs` copies it verbatim into
// `web/lib/raceCore.js`, and `web/scripts/check-parity.mjs` runs it over every
// row of `race_vectors.json` to prove the browser reproduces the Python
// outcomes before `next build` runs. DO NOT edit the vendored copy in `web/`;
// edit here and re-vendor.
//
// Mirrors, byte-for-byte in behaviour:
//   testbed/attacker/portable_prng.py   -> splitmix64, bounded
//   testbed/attacker/guessing.py        -> GuessStream
//   testbed/draw/sad_dns.py             -> sadDnsLeak, effectiveBits
//   testbed/sim/event_queue.py          -> EventQueue (min-heap keyed (time, seq))
//   testbed/sim/race.py                 -> runRace, runAttackRace
//   testbed/vectors/gen_race_vectors.py -> buildFloodVector (the _flood_vector adapter)
//
// PARITY HAZARDS (why this is not a naive port):
//  - Python ints are arbitrary-precision; JS `<<`/`|` are 32-bit SIGNED. Any
//    shift/or that can exceed 2^31 is done with `* 2**n + ...` on Numbers
//    (exact up to 2^53) or with BigInt. `1 << 32` in JS is 1, not 2^32.
//  - splitmix64 needs true 64-bit math -> BigInt with explicit & MASK64.
//  - Python `int(x)` truncates toward zero -> Math.trunc.
//  - IEEE-754 doubles agree across Python/JS ONLY if the operator order is
//    identical. Every float expression below mirrors the Python token order.

"use strict";

const MASK64 = (1n << 64n) - 1n;
const GOLDEN_GAMMA = 0x9e3779b97f4a7c15n;

// --- portable_prng.py ---

function splitmix64(state) {
  // state: BigInt -> [value: BigInt, nextState: BigInt]
  const nextState = (state + GOLDEN_GAMMA) & MASK64;
  let z = nextState;
  z = ((z ^ (z >> 30n)) * 0xbf58476d1ce4e5b9n) & MASK64;
  z = ((z ^ (z >> 27n)) * 0x94d049bb133111ebn) & MASK64;
  z = z ^ (z >> 31n);
  return [z, nextState];
}

function bounded(state, n) {
  // n: Number (power of two, <= 2**32) -> [index: Number, nextState: BigInt]
  if (n <= 0) throw new Error("n must be positive");
  const [value, nextState] = splitmix64(state);
  return [Number(value % BigInt(n)), nextState];
}

// --- guessing.py ---

class GuessStream {
  constructor(spaceSize, state) {
    this.spaceSize = spaceSize; // Number, up to 2**32
    this.state = typeof state === "bigint" ? state : BigInt(state);
    this._seen = new Set();
  }

  resetRound() {
    this._seen.clear();
  }

  next() {
    if (this._seen.size >= this.spaceSize) this.resetRound();
    for (;;) {
      const [guess, nextState] = bounded(this.state, this.spaceSize);
      this.state = nextState;
      if (!this._seen.has(guess)) {
        this._seen.add(guess);
        return guess;
      }
    }
  }
}

// --- sad_dns.py ---

function sadDnsLeak(portBits, k) {
  return Math.max(0, portBits - k);
}

function effectiveBits(txidBits, portBits, k) {
  return txidBits + sadDnsLeak(portBits, k);
}

// --- event_queue.py: min-heap keyed (time, seq); payload never compared ---

class EventQueue {
  constructor() {
    this._heap = [];
    this._seq = 0;
    this.now = 0.0;
  }

  _less(a, b) {
    return a.time < b.time || (a.time === b.time && a.seq < b.seq);
  }

  push(time, kind, payload) {
    const event = { time, seq: this._seq++, kind, payload };
    const h = this._heap;
    h.push(event);
    let i = h.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (this._less(h[i], h[p])) {
        const t = h[i];
        h[i] = h[p];
        h[p] = t;
        i = p;
      } else break;
    }
    return event;
  }

  pop() {
    const h = this._heap;
    const top = h[0];
    const last = h.pop();
    if (h.length > 0) {
      h[0] = last;
      let i = 0;
      const n = h.length;
      for (;;) {
        const l = 2 * i + 1;
        const r = 2 * i + 2;
        let s = i;
        if (l < n && this._less(h[l], h[s])) s = l;
        if (r < n && this._less(h[r], h[s])) s = r;
        if (s === i) break;
        const t = h[i];
        h[i] = h[s];
        h[s] = t;
        i = s;
      }
    }
    this.now = top.time;
    return top;
  }

  empty() {
    return this._heap.length === 0;
  }
}

// --- race.py: run_race (literal (txid, port) match) ---

function runRace(seed, draw, forgedGuess, rtt, sendSchedule) {
  // draw, forgedGuess: [txid, port]. `seed` unused (P1 contract), kept for signature.
  const queue = new EventQueue();
  queue.push(rtt, "authoritative", null);
  for (const sendTime of sendSchedule) queue.push(sendTime, "forged", forgedGuess);

  let forgedPackets = 0;
  while (!queue.empty()) {
    const event = queue.pop();
    if (event.kind === "forged") {
      forgedPackets += 1;
      const [gt, gp] = event.payload;
      if (gt === draw[0] && gp === draw[1]) {
        return { outcome: "poisoned", t_outcome: event.time, forged_packets: forgedPackets };
      }
    } else if (event.kind === "authoritative") {
      return { outcome: "resolved_legit", t_outcome: event.time, forged_packets: forgedPackets };
    }
  }
  return { outcome: "window_closed", t_outcome: queue.now, forged_packets: forgedPackets };
}

// --- race.py: run_attack_race (continuous-flood, analytic per-window) ---
// A window is live only during [tOpen, tAuthoritative]; gLive = sendRate *
// duration distinct guesses land in it (capped by guessBudget and by the
// space). The window is poisoned iff the target's rank in the flood's random
// distinct-guess order (guessStream.next()) falls within those gLive guesses,
// i.e. Bernoulli(gLive/spaceSize) -- the epic's analytic anchor. `_events`
// (optional) collects a display trace; compared fields are unaffected by it.

function runAttackRace(windowsSpec, guessStream, sendRatePps, guessBudget, attempts, _events) {
  const spaceSize = guessStream.spaceSize;
  const nAttempts = attempts === undefined || attempts === null ? 1 : attempts;

  const windows = [];
  let maxTAuthoritative = 0.0;
  let windowId = 0;
  for (const queryWindows of windowsSpec) {
    for (const [, tOpen, tAuthoritative] of queryWindows) {
      windows.push([tOpen, tAuthoritative, windowId]);
      if (tAuthoritative > maxTAuthoritative) maxTAuthoritative = tAuthoritative;
      windowId += 1;
    }
  }
  // Stable sort by tOpen (ES2019+): ties keep insertion (windowId) order,
  // matching Python's stable `sort(key=lambda w: w[0])`.
  windows.sort((a, b) => a[0] - b[0]);

  let forgedPackets = 0;
  for (const [tOpen, tAuthoritative, wid] of windows) {
    guessStream.resetRound();
    const duration = Math.max(0.0, tAuthoritative - tOpen);
    let gLive = Math.trunc(sendRatePps * duration); // Python: int(...)
    if (guessBudget !== null && guessBudget !== undefined) gLive = Math.min(gLive, guessBudget);
    gLive = Math.min(gLive, spaceSize);
    if (gLive <= 0) continue;
    const targetRank = guessStream.next();
    if (nAttempts <= 1) {
      // Single window: plain gLive/S Bernoulli.
      if (targetRank < gLive) {
        forgedPackets += targetRank + 1;
        const tHit = tOpen + ((targetRank + 0.5) / gLive) * duration;
        if (_events) _events.push({ time: tHit, kind: "poisoned", window: wid });
        return { outcome: "poisoned", t_outcome: tHit, forged_packets: forgedPackets, poisoned_window: wid };
      }
      forgedPackets += gLive;
    } else {
      // Kaminsky campaign: attempts independent windows folded to
      // pWin = 1-(1-p1)^attempts; the uniform picks hit + which attempt.
      const p1 = gLive / spaceSize;
      const u = targetRank / spaceSize;
      const pWin = 1.0 - Math.pow(1.0 - p1, nAttempts);
      if (u < pWin) {
        const attemptNo =
          p1 >= 1.0 ? 1 : Math.min(nAttempts, 1 + Math.trunc(Math.log1p(-u) / Math.log1p(-p1)));
        const within = targetRank % gLive;
        forgedPackets += (attemptNo - 1) * gLive + within + 1;
        const tHit = tOpen + (attemptNo - 1 + (within + 0.5) / gLive) * duration;
        if (_events) _events.push({ time: tHit, kind: "poisoned", window: wid });
        return { outcome: "poisoned", t_outcome: tHit, forged_packets: forgedPackets, poisoned_window: wid };
      }
      forgedPackets += nAttempts * gLive;
    }
  }
  if (_events) _events.push({ time: maxTAuthoritative, kind: "resolved_legit" });
  return { outcome: "resolved_legit", t_outcome: maxTAuthoritative, forged_packets: forgedPackets, poisoned_window: null };
}

// --- gen_race_vectors.py: _flood_vector adapter (windows_spec + send_schedule
//     derived from splitmix64), returns the full flood vector. `trace` toggles
//     collection of the display event list for the canvas. ---

function buildFloodVector(params, trace) {
  const {
    seed,
    txid,
    port,
    txid_bits,
    port_bits,
    k,
    rtt,
    retransmit,
    send_rate_pps,
    parallel_queries,
    retransmit_rounds,
    rtt_jitter_frac,
  } = params;

  const spaceSize = 2 ** (txid_bits + port_bits); // Python: 1 << (TXID_BITS + port_bits)
  let state = BigInt(seed);
  const windowsSpec = [];

  const target0 = txid * 2 ** port_bits + port; // Python: (txid << port_bits) | port
  let maxTAuthoritative = 0.0;
  for (let qIndex = 0; qIndex < parallel_queries; qIndex++) {
    const rounds = [];
    for (let roundIndex = 0; roundIndex < retransmit_rounds + 1; roundIndex++) {
      let targetIndex;
      if (qIndex === 0 && roundIndex === 0) {
        targetIndex = target0;
      } else {
        const r = bounded(state, spaceSize);
        targetIndex = r[0];
        state = r[1];
      }
      const tOpen = roundIndex * retransmit;
      const j = bounded(state, 1000000);
      const jitterUnit = j[0];
      state = j[1];
      const jitter = (jitterUnit / 1000000 - 0.5) * 2 * rtt_jitter_frac * rtt;
      const tAuthoritative = tOpen + rtt + jitter;
      rounds.push([targetIndex, tOpen, tAuthoritative]);
      if (tAuthoritative > maxTAuthoritative) maxTAuthoritative = tAuthoritative;
    }
    windowsSpec.push(rounds);
  }

  const guessStream = new GuessStream(spaceSize, state);

  const events = trace ? [] : null;
  // Flood vectors carry no guess budget and a single attempt (attempts=1),
  // mirroring the parity-vector generator; the campaign multiplier is an
  // experiment-path knob, exercised by the Python sweep, not the vectors.
  const result = runAttackRace(windowsSpec, guessStream, send_rate_pps, null, 1, events);

  const effBits = txid_bits + Math.max(0, port_bits - k);
  return {
    seed,
    txid,
    port,
    eff_bits: effBits,
    rtt,
    retransmit,
    // The analytic engine no longer enumerates packets, so no send_schedule is
    // built for flood mode (kept as [] for schema stability with run_race rows).
    send_schedule: [],
    parallel_queries,
    outcome: result.outcome,
    forged_packets: result.forged_packets,
    t_outcome: result.t_outcome,
    // display-only extras (ignored by the parity gate):
    windows_spec: trace ? windowsSpec : undefined,
    events: trace ? events : undefined,
  };
}

module.exports = {
  splitmix64,
  bounded,
  GuessStream,
  sadDnsLeak,
  effectiveBits,
  EventQueue,
  runRace,
  runAttackRace,
  buildFloodVector,
};
