#!/usr/bin/env python3
"""Critical Quantum Life — F3: quantum certification vs the classical surrogate.

The QUANTUM HONESTY GATE (epic honesty gate 3). It holds the ⟨X^{⊗W}⟩ genealogical
entanglement witness above a MATCHED classical measure-and-resend surrogate null band across
the whole run. That is the certificate that the aliveness is quantum, not classical stochastic
dynamics wearing a quantum costume. (POC: witness +0.87 on ibm_kingston vs classical null
±0.047, 29/30 gens above band.)

What is reused vs new
---------------------
- REUSED (not reimplemented): the single-sourced witness math — F0 logs ⟨X^{⊗W}⟩ per
  generation via q4.xbasis_witness_from_counts (AC-F3.1); the closed-loop control flow lives in
  closed_loop.run_closed_loop.
- NEW (this file): the classical measure-and-resend SURROGATE arm running F0's IDENTICAL closed
  loop (the surrogate=True hook swaps ONLY the readout — Q1/Q2), the null-band computation
  (AC-F3.2), the per-gen σ-margin report + pass/fail (AC-F3.3), and the witness-vs-surrogate
  panel data for F6/F7 (AC-F3.4).

Pass rule (epic §9 F3): pass = "witness stays ABOVE the null band", NOT "= 1". NISQ readout +
2q error pull the witness down; the surrogate defines what "0" looks like and the quantum arm
must beat it, allowing the poke gen + NISQ dips (certified iff ≥ CERT_FRAC of gens clear it).

Run (sim):
    cd THESIS/CriticalQuantumLife/code
    python closed_loop.py --arm closed --generations 15 --width 4 --poke-gen 8 --name cql_f3q
    python certify.py --quantum-run ../research_runs/cql_f3q_closed_*_run.json --name cql_f3
"""
from __future__ import annotations

import argparse
import functools
import glob
import json
import math
import os
import sys
from typing import Any

import numpy as np

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import closed_loop as cl                        # F0 engine (closed loop + surrogate=True hook)
if cl._AL not in sys.path:
    sys.path.insert(0, cl._AL)
import stage4_qalife as q4                       # noqa: F401  (single-sourced witness, via cl)

CERT_FRAC = 0.8         # Q4: gens above band / total to certify (allows poke dip + NISQ)
K_BAND = 3.0            # Q3: analytic null band k/sqrt(shots) (POC's 3-sigma convention)


# ---------------------------------------------------------------------------
# Surrogate arm (AC-F3.2) — the classical measure-and-resend null
# ---------------------------------------------------------------------------
def surrogate_witness(rng: np.random.Generator, width: int, shots: int,
                      k: float = K_BAND) -> tuple[float, float, float]:
    """Single measure-and-resend witness draw + its analytic null band. Thin wrapper over the
    F0 hook (cl.surrogate_readout, mirroring classical_life.witness_classical) so the readout is
    single-sourced. Returns (joint ≈ 0, separable ≈ 0, null_band = k/sqrt(shots))."""
    joint, sep, _ = cl.surrogate_readout(rng, width, shots)
    return joint, sep, k / math.sqrt(max(1, shots))


def run_surrogate_loop(sur_args: argparse.Namespace) -> dict[str, Any]:
    """Run F0's IDENTICAL closed loop with the surrogate readout substituted (arm='surrogate',
    per-gen witness_signal ≈ 0). client=None -> PRNG on sim; the only difference from the
    quantum arm is the collapsed (measure-and-resend) quantum resource (Q2)."""
    run, _ = cl.run_closed_loop(sur_args, client=None, surrogate=True)
    return run


# ---------------------------------------------------------------------------
# Null band (AC-F3.2) + certification (AC-F3.1/3.3) + panel (AC-F3.4)
# ---------------------------------------------------------------------------
def null_band(shots: int, surrogate_gens: list[dict[str, Any]] | None,
              k: float = K_BAND) -> float:
    """AC-F3.2 null band. PRIMARY = analytic k/sqrt(shots) (Q3, POC's ±0.047 at k=3, 4096
    shots). If a surrogate run is supplied its empirical max|signal| corroborates it; the
    honest reported band is the LARGER of the two (never certify inside sampling noise)."""
    analytic = k / math.sqrt(max(1, shots))
    if not surrogate_gens:
        return analytic
    empirical = max((abs(r["witness_signal"]) for r in surrogate_gens), default=0.0)
    return max(analytic, empirical)


def empirical_surrogate_band(surrogate_gens: list[dict[str, Any]] | None) -> float | None:
    """max|surrogate_signal| over the surrogate run (corroboration only), or None."""
    if not surrogate_gens:
        return None
    return max((abs(r["witness_signal"]) for r in surrogate_gens), default=0.0)


def certify(quantum: dict[str, Any], surrogate: dict[str, Any] | None,
            args: argparse.Namespace) -> dict[str, Any]:
    """AC-F3.1/3.3/3.4. Pull the quantum witness_signal per gen (already logged by F0 via
    q4.xbasis_witness_from_counts), compute the band, count gens above it, the σ-margin
    stats, the pass/fail, and assemble the certification block + the F6/F7 panel."""
    qgens = quantum["generations"]
    sgens = surrogate["generations"] if surrogate else None
    shots = int(args.shots) if args.shots is not None else int(quantum["meta"]["shots"])
    band = null_band(shots, sgens, args.k)

    margins = [r["witness_signal"] - band for r in qgens]
    gens_total = len(qgens)
    gens_above = sum(1 for m in margins if m > 0.0)
    frac = (gens_above / gens_total) if gens_total else 0.0
    certified = frac >= args.cert_frac

    panel: list[dict[str, Any]] = []
    for i, r in enumerate(qgens):
        s_sig = float(sgens[i]["witness_signal"]) if sgens and i < len(sgens) else None
        panel.append({
            "gen": r["gen"],
            "quantum_signal": float(r["witness_signal"]),
            "surrogate_signal": s_sig,
            "null_band": band,
            "poke": bool(r.get("poke", False)),
        })

    return {
        "quantum_run": os.path.basename(args.quantum_run),
        "surrogate_run": (os.path.basename(args.surrogate_run)
                          if args.surrogate_run else "computed(sim)"),
        "certification": {
            "null_band": band,                                  # AC-F3.2
            "null_band_analytic": args.k / math.sqrt(max(1, shots)),
            "null_band_empirical_surrogate": empirical_surrogate_band(sgens),
            "k": args.k,
            "shots": shots,
            "cert_frac": args.cert_frac,
            "gens_total": gens_total,
            "gens_above_band": gens_above,                      # AC-F3.3
            "frac_above_band": frac,
            "witness_margin_mean": (float(np.mean(margins)) if margins else 0.0),
            "witness_margin_min": (float(np.min(margins)) if margins else 0.0),
            "certified": certified,                             # AC-F3.3
        },
        "panel": panel,                                         # AC-F3.4
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_certification(block: dict[str, Any], args: argparse.Namespace) -> str:
    """Sidecar <name>_certification.json into F0's research_runs dir."""
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(cl.OUTPUT_DIR, f"{args.name}_certification.json")
    with open(path, "w") as f:
        json.dump(block, f, indent=2, default=str)
    return path


def _resolve_run(pattern: str) -> str:
    """Accept an exact path or a glob (the manual-verify recipe uses *)."""
    if os.path.exists(pattern):
        return pattern
    matches = sorted(glob.glob(pattern))
    if not matches:
        print(f"[ABORT] no run JSON matches: {pattern}")
        raise SystemExit(1)
    return matches[-1]


def _surrogate_args_from(quantum_meta: dict[str, Any],
                         args: argparse.Namespace) -> argparse.Namespace:
    """Build a matched F0 args Namespace from the quantum run's meta so the surrogate loop is
    parametrically identical (width, generations, shots, seed, mut_scale, nbins, death,
    interaction, poke_gen). Death-channel delta/gamma default to the F0 defaults."""
    return argparse.Namespace(
        width=int(quantum_meta["width"]),
        generations=int(quantum_meta["generations"]),
        shots=int(quantum_meta["shots"]),
        seed=int(quantum_meta["seed"]),
        mut_scale=float(quantum_meta["mut_scale"]),
        nbins=int(quantum_meta["nbins"]),
        death=str(quantum_meta["death"]),
        interaction=str(quantum_meta["interaction"]),
        poke_gen=quantum_meta.get("poke_gen"),
        delta=q4.AGING_DELTA,
        gamma=q4.DAMP_GAMMA,
        name=args.name,
    )


def _print_report(quantum: dict[str, Any], surrogate: dict[str, Any] | None,
                  block: dict[str, Any]) -> None:
    c = block["certification"]
    print(f"  gen  quantum  surrogate    band   margin  note")
    sgens = surrogate["generations"] if surrogate else None
    for i, r in enumerate(quantum["generations"]):
        s = f"{sgens[i]['witness_signal']:+.3f}" if sgens and i < len(sgens) else "  -  "
        margin = r["witness_signal"] - c["null_band"]
        note = " <-- POKE" if r.get("poke") else ("" if margin > 0 else "  (in band)")
        print(f"  {r['gen']:3d}  {r['witness_signal']:+.3f}    {s:>7}   {c['null_band']:.3f}  "
              f"{margin:+.3f}{note}")
    print(f"\n  null band ±{c['null_band']:.3f}  (analytic {c['null_band_analytic']:.3f}, "
          f"empirical surrogate {c['null_band_empirical_surrogate']})")
    print(f"  gens above band: {c['gens_above_band']}/{c['gens_total']} "
          f"({c['frac_above_band']:.2f} >= {c['cert_frac']} ?)  "
          f"margin mean {c['witness_margin_mean']:+.3f}  min {c['witness_margin_min']:+.3f}")
    print(f"\n  CERTIFIED: {'yes' if c['certified'] else 'NO'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F3 — quantum certification vs classical surrogate")
    ap.add_argument("--quantum-run", dest="quantum_run", type=str, required=True,
                    help="F0/F5 closed-loop run JSON (exact path or glob)")
    ap.add_argument("--surrogate-run", dest="surrogate_run", type=str, default=None,
                    help="optional precomputed surrogate run JSON; else run the surrogate loop here")
    ap.add_argument("--shots", type=int, default=None, help="override; else from the quantum run meta")
    ap.add_argument("--k", type=float, default=K_BAND, help="null-band k (POC convention 3.0)")
    ap.add_argument("--cert-frac", dest="cert_frac", type=float, default=CERT_FRAC)
    ap.add_argument("--name", type=str, default="cql_f3")
    args = ap.parse_args()

    args.quantum_run = _resolve_run(args.quantum_run)
    with open(args.quantum_run) as f:
        quantum = json.load(f)
    if quantum["meta"]["arm"] not in ("closed", "closed-loop"):
        print(f"[WARN] --quantum-run arm is '{quantum['meta']['arm']}', expected 'closed'")

    if args.surrogate_run:
        args.surrogate_run = _resolve_run(args.surrogate_run)
        with open(args.surrogate_run) as f:
            surrogate = json.load(f)
    else:
        sur_args = _surrogate_args_from(quantum["meta"], args)
        print(f"=== CQL F3: running matched surrogate loop (measure-and-resend) "
              f"width={sur_args.width} generations={sur_args.generations} "
              f"shots={sur_args.shots} seed={sur_args.seed} ===")
        surrogate = run_surrogate_loop(sur_args)
        cl.write_run(surrogate, sur_args)

    block = certify(quantum, surrogate, args)
    _print_report(quantum, surrogate, block)
    print(f"\n  -> {write_certification(block, args)}")


if __name__ == "__main__":
    main()
