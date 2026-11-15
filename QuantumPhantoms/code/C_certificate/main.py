"""Section C: certificate. Runs first: the Bell map (C_certificate/bell_map.py) -> certificate.json + certified_bits.bin.

Set CIRCUIT below; that is the only switch. BELL-MAP is the certificate described here. GRAPH-BELL adds one Bell
inequality over the graph state of the chip region (C_certificate/graph_bell.py, entry "graph_bell" with its own
verdict) and runs one matching of the Bell map for the pool: the bit pool always comes from the Bell map.

One job measures CHSH on many disjoint pairs of the chip. It gives the run three things:
    certificate   one row per pair (S, sigma, certified = S > 2 by 3 sigma after Bonferroni over the measured pairs)
                  and a pooled verdict over the certified pairs: S_low = S_pooled - 3 sigma, Pironio's analytic
                  min-entropy per round f(S_low), certified_bits = rounds x f(S_low)
    bit pool      the raw outcomes of the certified pairs, Toeplitz-hashed to min(4096, certified_bits / 2) bits.
                  Section B draws the tumours from it and every random input of a B or D circuit is seeded from it
                  (common.runio.draw_bits); certificate.json "budget" records bits available against bits spent.
    pair map      S per measured coupler: the layout input of B and D in this run (common.qhard)

    fewer than MIN_PAIRS certified pairs, or S_low <= 2,
    or p_value_local >= 1e-6 (C_certificate/pbr.py)         FAILED: no bits, no tumours, no retry; the run stops
    passed, dry run                                          "certification-ready, not certified (simulated)"
    passed, live                                             a job-level Bell violation on that backend

Limits, stated with every use: settings are fixed per circuit and the pairs sit on one chip (no space-like
separation), so this is not device-independent; the pairs are selected on the same data that is pooled; f(S_low) is
an analytic rate at a 3-sigma lower value, not a composable security proof.

Chain (C-CHAIN): the circuits and the run name are hashed into <run>/commit.json before the job; after it the first
pulse of a public randomness beacon (drand quicknet, one GET) emitted after the commit seeds the extractor, so the
seed could not be known when the circuits were fixed. No network: logged as "beacon skipped", os.urandom is used.
Section G chains commit, pulse and certificate. The beacon is public: it dates the seed, it is not a secret.
"""
from __future__ import annotations

import json
import math
import os
import time
import urllib.request

import numpy as np

from C_certificate import bell_map as BM, graph_bell as GB, pbr as PBR
from common import quantum as Q, runio
from common.runio import Ctx

CIRCUIT = "BELL-MAP"  # BELL-MAP | GRAPH-BELL

CIRCUITS = {
    "BELL-MAP": {"matchings": None},                         # every matching of bell_map.MATCHINGS
    # QCAND (plans/feature-QCAND-*.md): n >= the pruned chip = every usable qubit
    "GRAPH-BELL": {"matchings": 1, "n": 156, "dry": {"n": 12}},
}
DRAND = {"chain": "drand quicknet", "genesis": 1692803367, "period": 3,      # checked against <url>/info on 2026-11-15
         "url": "https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971"}
MIN_PAIRS = 8                 # certified pairs a live run needs
DRY_MIN_PAIRS = 4             # the dry run measures 6 pairs
SCOPE = ("job-level; not device-independent; settings fixed per circuit, pairs on one chip, no space-like "
         "separation; pairs selected on the data that is pooled")
POOL = "bits extracted from Bell-test outcomes on one chip; job-level; not device-independent"


def f_hmin(S: float) -> float:
    """Pironio et al. 2010: min-entropy per round f(S) = 1 - log2(1 + sqrt(2 - S^2 / 4)), 0 for S <= 2."""
    if S <= 2.0:
        return 0.0
    S = min(S, 2.0 * math.sqrt(2.0))
    return 1.0 - math.log2(1.0 + math.sqrt(max(0.0, 2.0 - S * S / 4.0)))


def beacon(commit_unix: float) -> dict:
    """The first drand pulse emitted after the commit (round r is emitted at genesis + (r - 1) period). One GET; the
    response is kept verbatim. Any failure -> a note, no pulse."""
    r = int((commit_unix - DRAND["genesis"]) // DRAND["period"]) + 2
    at = DRAND["genesis"] + (r - 1) * DRAND["period"]
    time.sleep(max(0.0, at + 1.0 - time.time()))
    url = f"{DRAND['url']}/public/{r}"
    try:
        with urllib.request.urlopen(url, timeout=10) as f:
            text = f.read().decode()
        return {"chain": DRAND["chain"], "round": r, "round_unix": at, "url": url, "response": text,
                "pulse": json.loads(text)["randomness"]}
    except Exception as e:
        return {"chain": DRAND["chain"], "round": r, "url": url, "pulse": None,
                "note": f"beacon skipped ({e.__class__.__name__}): the extractor seed is os.urandom"}


def run(ctx: Ctx) -> None:
    from scipy.stats import norm

    cfg = CIRCUITS[CIRCUIT] if ctx.live else CIRCUITS[CIRCUIT] | CIRCUITS[CIRCUIT].get("dry", {})
    built, graph = None, None
    if CIRCUIT == "GRAPH-BELL":
        try:
            built = GB.build(ctx, cfg)
        except Q.Refused as e:
            graph = {"status": f"not run: {e}"}
    rows, info = BM.measure(ctx, cfg["matchings"], also=built["circuits"] if built else ())
    z_need = float(norm.isf(norm.sf(3.0) / len(rows)))                  # Bonferroni over the measured pairs
    for r in rows:
        r["certified"] = bool((r["S"] - 2.0) / r["sigma"] > z_need)
        r["p_no_signalling"] = PBR.no_signalling(r["_bits"])
        r["cross_talk"] = bool(r["p_no_signalling"] < PBR.P_CROSS_TALK)
    cert = [r for r in rows if r["certified"]]
    pooled = np.concatenate([r["_bits"] for r in (cert or rows)], axis=1)      # (4 settings, rounds per setting, 2)
    S, sigma = BM.chsh(pooled)
    S_low = S - 3.0 * sigma
    need = MIN_PAIRS if ctx.live else DRY_MIN_PAIRS
    shots = int(pooled.shape[1] // max(len(cert or rows), 1))
    pv = PBR.p_value(pooled, shots)
    passed = len(cert) >= need and S_low > 2.0 and pv["p_value_local"] < PBR.P_STOP
    if built:
        graph = GB.measure(ctx, built, shots)
    doc = {"circuit": CIRCUIT, "commit": info["commit"]["commit"], "chsh_S": S, "classical_bound": 2.0, "tsirelson_bound": 2.0 * math.sqrt(2.0),
           "backend": info["backend"] if ctx.live else info["label"], "job_id": info["job_id"], "label": info["label"],
           "scope": SCOPE, "chsh_settings": dict(BM.CHSH_SETTINGS), "shots_per_setting": shots,
           "pairs_measured": len(rows), "pairs_certified": len(cert), "pairs_needed": need, "z_needed": z_need,
           "sigma": sigma, "S_low": S_low, "p_value_local": pv["p_value_local"], "pbr": pv, "pairs": rows,
           "pair_map": {f"{r['qubits'][0]}-{r['qubits'][1]}": r["S"] for r in rows}}
    if graph:
        doc["graph_bell"] = graph
    if not passed:
        doc |= {"passed": False, "status": f"FAILED: {len(cert)} certified pairs (need {need}), S_low = {S_low:.3f} "
                                           f"(need > 2), p_value_local = {pv['p_value_local']:.1e} (need < "
                                           f"{PBR.P_STOP:.0e}): no bits, no tumours, no retry"}
    else:
        rounds = int(pooled.shape[0] * pooled.shape[1])
        hmin = f_hmin(S_low)
        m = int(min(BM.MAX_BITS, math.floor(rounds * hmin / 2)))
        pulse = beacon(info["commit"]["created_unix"])
        Q.log(pulse.get("note") or f"beacon: {pulse['chain']} round {pulse['round']}, the first pulse after the commit")
        seed = bytes.fromhex(pulse["pulse"]) if pulse["pulse"] else os.urandom(32)
        bits = BM.toeplitz(pooled.reshape(-1), m, seed)
        np.packbits(bits).tofile(ctx.path("certified_bits.bin"))
        doc |= {"passed": True, "rounds": rounds, "hmin_per_round": hmin, "certified_bits": rounds * hmin,
                "entropy_rigour": "analytic rate at a 3-sigma lower value, not a composable security proof",
                "pulse": pulse["pulse"], "beacon": pulse,
                "extractor": {"kind": "toeplitz", "seed_hex": seed.hex(), "output_bits": m, "input_bits": int(pooled.size),
                              "seed_source": (f"{pulse['chain']} round {pulse['round']} (first pulse after the commit)"
                                              if pulse["pulse"] else "os.urandom (beacon skipped)"),
                              "seed_expansion": "SHAKE-256 of the 32-byte seed"},
                "budget": {"available": m, "spent": {}},
                "pool": POOL + ("" if ctx.live else "; simulated"),
                "status": (f"Bell violation on hardware: {info['backend']}, job {info['job_id']} (job-level; not "
                           f"device-independent)") if ctx.live else "certification-ready, not certified (simulated)"}
    runio.save_json(ctx.path("certificate.json"), doc)
    Q.session(ctx).target.meta["pair_map"] = runio.pair_map(ctx.run_dir)
    print(f"  Bell map: {len(cert)} of {len(rows)} pairs certified (S - 2 > {z_need:.2f} sigma); pooled CHSH S = {S:.3f}"
          f" +- {sigma:.3f}, S_low = {S_low:.3f} (bound 2), p_value_local = {pv['p_value_local']:.1e}; "
          f"{sum(r['cross_talk'] for r in rows)} pairs flagged for cross-talk -> {doc['status']}")
    if graph and "value" in graph:
        print(f"  graph Bell: I = {graph['value']:.2f} +- {graph['sigma']:.2f} on {graph['n']} qubits (local bound "
              f"{graph['classical_bound']:.2f}, graph state {graph['quantum_bound']:.2f}) -> "
              f"{'violated' if graph['passed'] else 'not violated'} at 3 sigma; locality assumed (same chip)")
    if not passed:
        raise SystemExit(7)
    print(f"  bit pool: {doc['budget']['available']} bits from {doc['rounds']} rounds x {doc['hmin_per_round']:.3f} "
          f"bits of min-entropy, halved ({doc['pool']})")
