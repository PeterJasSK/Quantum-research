"""Driver: SK QAOA teleport-vs-SWAP, noiseless Aer sim (+ manual HW path).

Flow:
  1. fixed-seed SK instance + exact optimum/worst (brute force)
  2. coarse seeded grid search for (gamma, beta) on the LOGICAL circuit
  3. run logical / teleport / swap arms on a noiseless AerSimulator
  4. approximation ratio (robust, normalised by worst-opt) per arm
  5. sign check: all three arms' mean energy agree within tolerance (the §4b gate)
  6. write run JSON under number-partitioning/research_runs/

HW is manual (epic §3): --backend transpiles + submits via QuantumLife/code
pipeline_common; never touched by the default sim path.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from qiskit import transpile
from qiskit_aer import AerSimulator

from sk_instance import make_instance, ising_couplings, energy, brute_force_optimum
from qaoa_sk import build_circuit

RUNS_DIR = os.path.join(os.path.dirname(__file__), "research_runs")


def _genome_counts(counts: dict[str, int]) -> dict[str, int]:
    """Collapse multi-register keys to the genome ("c") register.

    Registers are added qr,(anc),cr,(tel); Qiskit puts later-added cregs to the
    LEFT, space-separated. The genome register `c` is added before `tel`, so it
    is the RIGHTMOST space-separated token.
    """
    out: dict[str, int] = {}
    for key, v in counts.items():
        genome = key.split(" ")[-1]
        out[genome] = out.get(genome, 0) + v
    return out


def _herald_filter(counts: dict[str, int]) -> dict[str, int]:
    """Keep only tel==00...0 shots (leftmost token), return genome counts."""
    out: dict[str, int] = {}
    for key, v in counts.items():
        parts = key.split(" ")
        if len(parts) < 2:
            out[parts[-1]] = out.get(parts[-1], 0) + v
            continue
        tel = parts[0]
        if set(tel) <= {"0"}:
            genome = parts[-1]
            out[genome] = out.get(genome, 0) + v
    return out


def _mean_and_best(
    gcounts: dict[str, int], a: list[int], A: float
) -> tuple[float, float, str, int]:
    """(mean energy, best energy, best genome bits, shots kept)."""
    total = sum(gcounts.values())
    if total == 0:
        return float("nan"), float("nan"), "", 0
    esum = 0.0
    best_e = float("inf")
    best_bits = ""
    for bits, cnt in gcounts.items():
        e = energy(bits, a, A)
        esum += e * cnt
        if e < best_e:
            best_e, best_bits = e, bits
    return esum / total, best_e, best_bits, total


def _run_arm(
    arm: str, couplings, n, p, gammas, betas, shots, sim, herald=False
) -> dict[str, int]:
    qc = build_circuit(arm, couplings, n, p, gammas, betas, herald=herald)
    tqc = transpile(qc, sim)
    result = sim.run(tqc, shots=shots).result()
    counts = result.get_counts()
    return _herald_filter(counts) if (arm == "teleport" and herald) \
        else _genome_counts(counts)


def _approx_ratio(mean_e: float, opt: float, worst: float) -> float:
    """(worst - value) / (worst - opt), in [0,1]; 1.0 if worst==opt."""
    if worst == opt:
        return 1.0
    return (worst - mean_e) / (worst - opt)


def _grid_search(couplings, n, p, shots, sim, grid, a, A):
    """Coarse seeded grid over scalar (gamma, beta) applied to all p layers."""
    import math
    gammas_grid = [math.pi * t / grid for t in range(1, grid + 1)]
    betas_grid = [math.pi * t / (2 * grid) for t in range(1, grid + 1)]
    best = None
    for g in gammas_grid:
        for b in betas_grid:
            gc = _run_arm("logical", couplings, n, p, [g] * p, [b] * p, shots, sim)
            mean_e, _, _, _ = _mean_and_best(gc, a, A)
            if best is None or mean_e < best[0]:
                best = (mean_e, g, b)
    return best[1], best[2]


def main() -> None:
    ap = argparse.ArgumentParser(description="SK QAOA teleport vs SWAP")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--p", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--A", type=float, default=1.0)
    ap.add_argument("--grid", type=int, default=8, help="angle grid resolution")
    ap.add_argument("--herald", action="store_true", help="teleport post-select tel==0")
    ap.add_argument("--backend", type=str, default="", help="Heron backend (MANUAL HW)")
    ap.add_argument("--name", type=str, default="sk")
    args = ap.parse_args()

    a = make_instance(args.n, args.seed)
    opt, worst, opt_bits = brute_force_optimum(a, args.A)
    couplings = ising_couplings(a, args.A)

    if args.backend:
        _run_hardware(args, a, couplings, opt, worst, opt_bits)
        return

    sim = AerSimulator()
    gamma, beta = _grid_search(
        couplings, args.n, args.p, args.shots, sim, args.grid, a, args.A
    )
    gammas, betas = [gamma] * args.p, [beta] * args.p

    arms: dict[str, dict] = {}
    for arm in ("logical", "teleport", "swap"):
        herald = args.herald and arm == "teleport"
        gc = _run_arm(arm, couplings, args.n, args.p, gammas, betas,
                      args.shots, sim, herald=herald)
        mean_e, best_e, best_bits, kept = _mean_and_best(gc, a, args.A)
        arms[arm] = {
            "mean_energy": mean_e,
            "best_energy": best_e,
            "best_partition": best_bits,
            "shots_kept": kept,
            "approx_ratio_mean": _approx_ratio(mean_e, opt, worst),
            "approx_ratio_best": _approx_ratio(best_e, opt, worst),
        }

    # sign check: logical/teleport/swap mean energies agree within tolerance.
    means = [arms[x]["mean_energy"] for x in ("logical", "teleport", "swap")]
    spread = max(means) - min(means)
    tol = 0.05 * (worst - opt if worst > opt else 1.0)
    sign_check = {
        "logical_mean": means[0],
        "teleport_mean": means[1],
        "swap_mean": means[2],
        "spread": spread,
        "tolerance": tol,
        "agree": spread <= tol,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = {
        "meta": {
            "project": "number-partitioning",
            "study": "sk-qaoa-teleport-routing",
            "n": args.n, "p": args.p, "A": args.A,
            "seed": args.seed, "shots": args.shots, "grid": args.grid,
            "herald": args.herald, "sim": True, "backend": "aer_noiseless",
            "instance": a, "couplings": {f"{i},{j}": v for (i, j), v in couplings.items()},
            "angles": {"gamma": gamma, "beta": beta},
            "optimum": opt, "worst": worst, "optimum_partition": opt_bits,
            "timestamp": ts,
        },
        "arms": arms,
        "sign_check": sign_check,
    }
    os.makedirs(RUNS_DIR, exist_ok=True)
    path = os.path.join(RUNS_DIR, f"{args.name}_n{args.n}_p{args.p}_sim_{ts}.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"instance n={args.n} seed={args.seed}: {a}")
    print(f"optimum={opt} worst={worst} angles gamma={gamma:.3f} beta={beta:.3f}")
    for arm in ("logical", "teleport", "swap"):
        r = arms[arm]
        print(f"  {arm:>9}: approx(best)={r['approx_ratio_best']:.3f} "
              f"approx(mean)={r['approx_ratio_mean']:.3f} "
              f"best_E={r['best_energy']:.1f} kept={r['shots_kept']}")
    print(f"sign_check: spread={spread:.3f} tol={tol:.3f} agree={sign_check['agree']}")
    print(f"wrote {path}")


def _resolve_pipeline_common() -> None:
    """Add the Calibration study's pipeline_common to sys.path (it has moved
    between layouts; mirror research_qtree_teleport.py's search)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in ("code", os.path.join("old", "code"), os.path.join("new", "code")):
        p = os.path.normpath(
            os.path.join(here, "..", "..", "CalibrationGuidedHighYieldQRNG", cand))
        if os.path.exists(os.path.join(p, "pipeline_common.py")):
            if p not in sys.path:
                sys.path.insert(0, p)
            return
    raise RuntimeError("pipeline_common.py not found in CalibrationGuidedHighYieldQRNG")


def _run_hardware(args, a, couplings, opt, worst, opt_bits) -> None:
    """MANUAL hardware path (epic §3). Submitted by the user on QC.

    Transpiles each arm to the ISA and submits via the Calibration study's
    pipeline_common (same submission path the teleport study uses); records live
    calibration into meta. Never called by the default sim path.

    Feed-forward only: run_sampler reads the genome register `c`, not `tel`, so
    heralded post-selection is not available on this HW path.
    """
    _resolve_pipeline_common()
    from pipeline_common import connect, run_sampler, timestamp  # noqa: E402
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    if args.herald:
        print("WARNING: --herald ignored on HW (run_sampler reads only `c`); "
              "using feed-forward.")

    backend = connect(args.backend)
    print(f"Backend : {backend.name} ({backend.num_qubits} qubits)")

    # angles: reuse a quick logical grid on Aer before submitting.
    sim = AerSimulator()
    gamma, beta = _grid_search(
        couplings, args.n, args.p, args.shots, sim, args.grid, a, args.A
    )
    gammas, betas = [gamma] * args.p, [beta] * args.p

    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    ts = timestamp()
    arms: dict[str, dict] = {}
    for arm in ("teleport", "swap"):
        qc = build_circuit(arm, couplings, args.n, args.p, gammas, betas,
                           herald=False)
        isa = pm.run(qc)
        raw_meas, jobs_meta, total_qs = run_sampler(backend, isa, args.shots)
        gc: dict[str, int] = {}
        for b in raw_meas:               # each entry = genome register `c`
            gc[b] = gc.get(b, 0) + 1
        mean_e, best_e, best_bits, kept = _mean_and_best(gc, a, args.A)
        arms[arm] = {
            "mean_energy": mean_e, "best_energy": best_e,
            "best_partition": best_bits, "shots_kept": kept,
            "approx_ratio_mean": _approx_ratio(mean_e, opt, worst),
            "approx_ratio_best": _approx_ratio(best_e, opt, worst),
            "quantum_seconds": total_qs, "jobs_meta": jobs_meta,
            "logical_depth": qc.depth(),
        }

    try:
        from calibration_snapshot import read_snapshot  # noqa: E402
        calib = read_snapshot(backend)
    except Exception as e:
        calib = {"_error": str(e), "backend": backend.name}

    out = {
        "meta": {
            "project": "number-partitioning", "study": "sk-qaoa-teleport-routing",
            "n": args.n, "p": args.p, "A": args.A, "seed": args.seed,
            "shots": args.shots, "herald": False, "feedforward": True, "sim": False,
            "backend": backend.name, "instance": a,
            "angles": {"gamma": gamma, "beta": beta},
            "optimum": opt, "worst": worst, "optimum_partition": opt_bits,
            "timestamp": ts, "calibration": calib,
        },
        "arms": arms,
    }
    os.makedirs(RUNS_DIR, exist_ok=True)
    path = os.path.join(
        RUNS_DIR, f"{args.name}_n{args.n}_p{args.p}_{args.backend}_{ts}.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
