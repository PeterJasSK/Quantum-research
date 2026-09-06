#!/usr/bin/env python3
"""Critical Quantum Life — F7: the 30-second hardware validation of the ONE number.

Spends a tiny QC budget (10 circuits x 1000 shots ~ 30s) to prove the Canary's single health
metric — the witness margin above the classical null — is REAL, RESPONSIVE, and SELF-HEALING on
a live QPU, not just in Aer.

The 10-circuit trajectory has a built-in degradation event:
    gens 0-3  healthy   -> margin must sit ABOVE the null band          (REAL)
    gen  4    POKE      -> founder scrambled = entanglement loss -> dip  (RESPONSIVE)
    gens 5-9  recovery  -> margin climbs back toward baseline            (SELF-HEALING)

One job, 10 pubs, 1000 shots each. Classical surrogate null is analytic (3/sqrt(1000) ~ 0.095) —
no extra QC. Writes research_runs/canary_validate_<backend>.json with the per-gen margins + the
QPU seconds actually spent.

Run (SPENDS ~30s of QC budget — confirm before firing):
    python canary_validate.py --backend ibm_kingston --width 4 --shots 1000 --poke-gen 4
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import os
import sys
from typing import Any

from qiskit import transpile

import closed_loop as cl
if cl._AL not in sys.path:
    sys.path.insert(0, cl._AL)
import layout                                       # best_chain low-error picker

print = functools.partial(print, flush=True)

K_BAND = 3.0
GENS = 10
DEFAULT_MUT = cl.DEFAULT_MUT


def connect(name: str) -> Any:
    from qiskit_ibm_runtime import QiskitRuntimeService
    return QiskitRuntimeService().backend(name)


def build_trajectory(width: int, poke_gen: int, seed: int, death: str,
                     interaction: str, mut: float) -> tuple[list[Any], list[int]]:
    """The 10 generation circuits (poke scrambles the founder at poke_gen). Low `mut` keeps the
    healthy GHZ intact so the witness clears the null; the poke is the degradation event.
    Returns (circuits, geno_qubits)."""
    import stage4_qalife as q4
    geno = [q4.geno_q(k) for k in range(width)]
    circuits = []
    for g in range(GENS):
        thetas = cl.draw_thetas(None, width, mut, g, [], seed)
        poke = (g == poke_gen)
        qc, _ = cl.build_generation(width, width, thetas, poke, death, interaction,
                                    q4.AGING_DELTA, q4.DAMP_GAMMA)
        circuits.append(qc)
    return circuits, geno


def run_on_hardware(backend: Any, circuits: list[Any], chain: list[int],
                    shots: int) -> tuple[list[dict[str, int]], float, list[str]]:
    """Transpile onto the pinned low-error chain, submit ALL circuits as one job. Returns
    (counts_per_circuit, qpu_seconds, job_ids)."""
    from qiskit_ibm_runtime import SamplerV2 as Sampler
    isa = [transpile(qc, backend=backend, initial_layout=chain, optimization_level=1)
           for qc in circuits]
    sampler = Sampler(mode=backend)
    job = sampler.run(isa, shots=shots)
    print(f"  job {job.job_id()} — {len(isa)} circuits x {shots} shots ...")
    res = job.result()
    counts = [res[i].data.meas.get_counts() for i in range(len(isa))]
    try:
        qs = float(job.metrics()["usage"]["quantum_seconds"])
    except Exception:
        qs = float("nan")
    return counts, qs, [job.job_id()]


def analyse(counts: list[dict[str, int]], geno: list[int], shots: int,
            poke_gen: int) -> dict[str, Any]:
    band = K_BAND / math.sqrt(max(1, shots))
    rows = []
    for g, c in enumerate(counts):
        joint, sep, _ = cl.witness_gen(c, geno, shots)
        signal = joint - sep
        rows.append({"gen": g, "witness_signal": signal, "margin": signal - band,
                     "poke": g == poke_gen})
    healthy = [r["margin"] for r in rows if not r["poke"] and r["gen"] < poke_gen]
    poke_margin = next((r["margin"] for r in rows if r["poke"]), None)
    recovery = [r["margin"] for r in rows if r["gen"] > poke_gen]
    healthy_mean = sum(healthy) / len(healthy) if healthy else 0.0
    recov_mean = sum(recovery) / len(recovery) if recovery else 0.0
    real = all(m > 0 for m in healthy) and bool(healthy)
    responsive = poke_margin is not None and poke_margin < healthy_mean
    healing = recov_mean > poke_margin if poke_margin is not None else False
    return {"band": band, "rows": rows, "healthy_mean": healthy_mean,
            "poke_margin": poke_margin, "recovery_mean": recov_mean,
            "verdict": {"real": real, "responsive": responsive, "self_healing": healing,
                        "pass": real and responsive}}


def _print(res: dict[str, Any]) -> None:
    print(f"\n  gen  witness   margin   note   (null band ±{res['band']:.3f})")
    for r in res["rows"]:
        note = "<-- POKE" if r["poke"] else ("above" if r["margin"] > 0 else "IN BAND")
        print(f"  {r['gen']:3d}  {r['witness_signal']:+.3f}   {r['margin']:+.3f}   {note}")
    v = res["verdict"]
    print(f"\n  healthy margin mean {res['healthy_mean']:+.3f}   poke margin "
          f"{res['poke_margin']:+.3f}   recovery mean {res['recovery_mean']:+.3f}")
    print(f"  REAL (healthy above null): {'yes' if v['real'] else 'NO'}")
    print(f"  RESPONSIVE (poke dips):    {'yes' if v['responsive'] else 'NO'}")
    print(f"  SELF-HEALING (recovers):   {'yes' if v['self_healing'] else 'NO'}")
    print(f"\n  VALIDATION {'PASS' if v['pass'] else 'FAIL'}"
          f"  (pass = real + responsive)")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F7 — 30s hardware validation of the witness margin")
    ap.add_argument("--backend", type=str, required=True)
    ap.add_argument("--width", type=int, default=4)
    ap.add_argument("--shots", type=int, default=1000)
    ap.add_argument("--poke-gen", dest="poke_gen", type=int, default=4)
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.10,
                    help="healthy mutation; low keeps the GHZ intact so the witness clears the null")
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--death", choices=["unitary", "damping"], default="unitary")
    ap.add_argument("--interaction", choices=["none", "nn"], default="nn")
    ap.add_argument("--dry-run", action="store_true", help="Aer instead of QC (no budget spent)")
    args = ap.parse_args()

    circuits, geno = build_trajectory(args.width, args.poke_gen, args.seed, args.death,
                                      args.interaction, args.mut_scale)
    print(f"=== CQL F7 validation: {GENS} circuits x {args.shots} shots, W={args.width}, "
          f"poke@gen{args.poke_gen}, backend={args.backend}{' (DRY-RUN Aer)' if args.dry_run else ''} ===")

    if args.dry_run:
        counts = [cl.run_counts(qc, args.shots, None) for qc in circuits]
        qs, jobs, chain = 0.0, [], list(range(2 * args.width))
    else:
        backend = connect(args.backend)
        chain, cstats = layout.best_chain(backend, 2 * args.width)
        print(f"  chain {chain}  ({cstats})")
        counts, qs, jobs = run_on_hardware(backend, circuits, chain, args.shots)
        print(f"  QPU seconds spent: {qs:.2f}")

    res = analyse(counts, geno, args.shots, args.poke_gen)
    _print(res)

    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(cl.OUTPUT_DIR, f"canary_validate_{args.backend}.json")
    with open(path, "w") as f:
        json.dump({"backend": args.backend, "width": args.width, "shots": args.shots,
                   "poke_gen": args.poke_gen, "chain": chain, "qpu_seconds": qs,
                   "job_ids": jobs, **res}, f, indent=2, default=str)
    print(f"\n  -> {path}")


if __name__ == "__main__":
    main()
