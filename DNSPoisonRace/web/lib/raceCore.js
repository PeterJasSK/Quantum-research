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

// --- race.py: run_attack_race (effective-index match) ---
// `_events` (optional array) collects a display trace for the canvas; the
// compared fields (outcome/t_outcome/forged_packets) are unaffected by it.

function runAttackRace(windowsSpec, guessStream, sendRatePps, _events) {
  const queue = new EventQueue();
  const windowTarget = {};
  const windowTAuth = {};
  const open = new Set();

  let windowId = 0;
  let maxTAuthoritative = 0.0;
  for (const queryWindows of windowsSpec) {
    for (const [targetIndex, tOpen, tAuthoritative] of queryWindows) {
      queue.push(tOpen, "window_open", [windowId, targetIndex, tAuthoritative]);
      if (tAuthoritative > maxTAuthoritative) maxTAuthoritative = tAuthoritative;
      windowId += 1;
    }
  }
  const totalWindows = windowId;

  const forgedCount = Math.trunc(maxTAuthoritative * sendRatePps);
  if (forgedCount > 0) {
    const step = maxTAuthoritative / forgedCount;
    for (let i = 0; i < forgedCount; i++) {
      const t = step * (i + 0.5);
      queue.push(t, "forged", guessStream.next());
    }
  }

  let forgedPackets = 0;
  let closedCount = 0;

  while (!queue.empty()) {
    const event = queue.pop();
    if (event.kind === "window_open") {
      const [wid, targetIndex, tAuthoritative] = event.payload;
      windowTarget[wid] = targetIndex;
      windowTAuth[wid] = tAuthoritative;
      open.add(wid);
      queue.push(tAuthoritative, "authoritative", wid);
    } else if (event.kind === "forged") {
      forgedPackets += 1;
      const guess = event.payload;
      if (_events) _events.push({ time: event.time, kind: "forged", guess });
      for (const wid of open) {
        if (guess === windowTarget[wid] && event.time < windowTAuth[wid]) {
          if (_events) _events.push({ time: event.time, kind: "poisoned", window: wid });
          return { outcome: "poisoned", t_outcome: event.time, forged_packets: forgedPackets, poisoned_window: wid };
        }
      }
    } else if (event.kind === "authoritative") {
      const wid = event.payload;
      if (open.has(wid)) {
        open.delete(wid);
        closedCount += 1;
        if (closedCount >= totalWindows) {
          if (_events) _events.push({ time: event.time, kind: "resolved_legit" });
          return { outcome: "resolved_legit", t_outcome: event.time, forged_packets: forgedPackets, poisoned_window: null };
        }
      }
    }
  }
  return { outcome: "window_closed", t_outcome: queue.now, forged_packets: forgedPackets, poisoned_window: null };
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
  const forgedCount = Math.trunc(maxTAuthoritative * send_rate_pps); // Python: int(...)
  const sendSchedule =
    forgedCount > 0
      ? Array.from({ length: forgedCount }, (_, i) => (maxTAuthoritative / forgedCount) * (i + 0.5))
      : [];

  const events = trace ? [] : null;
  const result = runAttackRace(windowsSpec, guessStream, send_rate_pps, events);

  const effBits = txid_bits + Math.max(0, port_bits - k);
  return {
    seed,
    txid,
    port,
    eff_bits: effBits,
    rtt,
    retransmit,
    send_schedule: sendSchedule,
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
