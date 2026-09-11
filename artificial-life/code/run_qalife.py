#!/usr/bin/env python3
"""Stage 4 scale driver -- the full 2018 quantum-artificial-life model, ON HARDWARE.

Runs the model built + sim-verified in ``qalife.py`` on a 156-qubit Heron-r2, pushes
the population width, and reports the Month-4 headline:

  * QUANTUM headline -- genealogical entanglement depth: the largest width W whose witness
    <X^{otimes W}> over the genotype line beats the separable (classical) null by k*sigma.
    This is the observable with NO classical surrogate -- the 2018 paper's "entanglement
    spreads throughout generations", now scaled far past its ~4-qubit / 1-generation origin.
  * POPULATION context -- alive-count and deepest-surviving-lineage from the phenotype Z
    readout (a classical diagonal observable, reported as context, not as the quantum claim).

One circuit per (width, repeat) measures BOTH: genotypes in the X basis (H then read =
witness) and phenotypes in the Z basis (alive-count) -- different qubits, one job.

Reuses: certified Q-EaaS entropy (mutation angles), ``layout.best_chain`` + chain-quality
gate, ``pipeline_common`` connect/run_sampler. Fixed study parameters are module globals below.

Usage (omit --backend for the Aer sim; pass one to run on that hardware):
    cd artificial-life/code
    python run_qalife.py --widths 3,4,5 --steps 4 --death unitary
    python run_qalife.py --backend ibm_marrakesh --widths 4,6,8 --steps 4 \\
        --death unitary --name qalife_m4p2
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import sys
import types
from typing import Any

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

import qalife as q4

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
SIM = AerSimulator(method="density_matrix")   # density_matrix so the damping arm sims too
QEAAS_URL = "https://api.qeaas.eu/"

# --- fixed study parameters (edit here; no longer CLI knobs) -------------------
INTERACTION = "nn"          # interaction topology: none | nn | longrange
REPEATS = 1                 # repeats per width for sigma error bars (1 = single run)
K = 2.0                     # witness must beat the separable null by K*sigma to survive
MUT_SCALE = 0.10            # mutation strength (fraction of pi); small => witness survives deep
MAX_TWOQ_ERR = 0.05         # chain-quality gate: max 2-qubit error along the chain
MAX_READOUT_ERR = 0.15      # chain-quality gate: max readout error along the chain
ALLOW_BAD_CHAIN = False     # True bypasses the chain-quality gate

# --- reuse the submission pipeline + QRNG client (same probe as stage3) --------
for _cand in ("code", os.path.join("old", "code"), os.path.join("new", "code")):
    _p = os.path.normpath(os.path.join(_HERE, "..", "..", "CalibrationGuidedHighYieldQRNG", _cand))
    if os.path.exists(os.path.join(_p, "pipeline_common.py")):
        sys.path.insert(0, _p)
        break
try:
    from pipeline_common import connect, run_sampler, timestamp  # noqa: E402
except Exception:
    _stub = types.ModuleType("pipeline_common")
    for _a in ("connect", "run_sampler"):
        setattr(_stub, _a, lambda *x, **k: None)
    _stub.timestamp = lambda: "sim"
    sys.modules["pipeline_common"] = _stub
    from pipeline_common import connect, run_sampler, timestamp  # noqa: E402

from qrng_client import QRNGClient, QRNGUnavailable  # noqa: E402


# Mutation angles from the certified Q-EaaS stream (CD-7 fail-closed on hardware).
def qrng_thetas(client: QRNGClient, width: int, mut_scale: float, repeat: int) -> list[float]:
    """`width` mutation angles in [0, mut_scale*pi) from certified quantum entropy: each is a
    disjoint 4-byte slice theta_k = mut_scale*pi*(u32/2^32). QRNGUnavailable propagates (fail-closed)."""
    need = 4 * width
    flat = bytearray()
    while len(flat) < need:
        resp = client.fetch(size=32, fmt="hex")
        flat.extend(bytes.fromhex(resp.data))
    out = []
    for k in range(width):
        u = int.from_bytes(bytes(flat[4 * k:4 * k + 4]), "big")
        out.append(mut_scale * math.pi * (u / 2 ** 32))
    return out


# Full model + dual-basis readout: genotypes in X (witness), phenotypes in Z (alive-count).
def build_measured(width: int, steps: int, thetas: list[float], interaction: str,death: str, annotate: bool = False) -> QuantumCircuit:

    qc = q4.build_population(width, steps, thetas, interaction, death=death, measure=False,annotate=annotate)
    q4._bar(qc, annotate, "X-basis (witness)")

    for k in range(width):
        qc.h(q4.geno_q(k))
    n_data = 2 * width + (1 if death == "damping" else 0)
    creg = ClassicalRegister(n_data, "c")

    qc.add_register(creg)
    qc.measure(range(n_data), creg)

    return qc


def dump_circuit(width: int, steps: int, thetas: list[float], interaction: str, death: str,
                 name: str) -> None:
    """Build the smallest paper-faithful circuit, annotate each Darwinian operator, print the
    diagram + a gate->operator legend, and save the drawing + QASM to research_runs."""
    qc = build_measured(width, steps, thetas, interaction, death, annotate=True)
    print("\n--- CIRCUIT (each barrier = one Darwinian operator / individual) ---")
    print(f"  qubits: genotype g_k = 2k, phenotype p_k = 2k+1"
          + (f", shared bath = {q4.bath_q(width)}" if death == "damping" else ""))
    print("  gate -> Darwinian meaning:")
    print("    Ry(pi/2) on g_0        = FOUNDER  (ancestral genotype seeded on the equator)")
    print("    CX(g_{k-1} -> g_k)     = SELF-REPLICATION  (partial sigma_z clone, eta=1)")
    print("    Ry(theta_k) on g_k     = MUTATION  (theta from certified QRNG)")
    if death == "damping":
        print("    CX(g_k -> p_k)         = PHENOTYPE  (2nd partial clone)")
        print("    CRY+CX+reset(bath)     = DEATH  (amplitude damping of the phenotype -> |0> dark state)")
    else:
        print("    Ry(aged) on p_k        = PHENOTYPE + DEATH  (phenotype angle reduced by aging)")
    print("    SWAP(p_k, p_j)         = INTERACTION  (predation: phenotypes exchanged)")
    print("    H on g_k then measure  = witness readout (genotypes in X), phenotypes in Z")
    draw = qc.draw(output="text", fold=-1)
    print("\n" + str(draw))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    txt = os.path.join(OUTPUT_DIR, f"{name}_circuit_w{width}_s{steps}.txt")
    with open(txt, "w") as f:
        f.write(str(draw))
    try:
        from qiskit.qasm3 import dumps
        with open(os.path.join(OUTPUT_DIR, f"{name}_circuit_w{width}_s{steps}.qasm"), "w") as f:
            f.write(dumps(qc))
    except Exception as e:
        print(f"  (qasm export skipped: {e})")
    print(f"\n  circuit saved -> {txt}")


# Chain-quality gate: pick a low-error qubit chain, abort if 2q/readout error too high.
def gated_chain(backend: Any, nq: int) -> list[int]:
    from layout import best_chain
    try:
        qubit_list, qstats = best_chain(backend, nq)
    except RuntimeError as exc:
        print(f"[S4 ABORT] no clean chain of {nq} qubits: {exc}")
        raise SystemExit(1)
    print(f"Auto qubit chain (live calib): {qstats}")
    if not ALLOW_BAD_CHAIN:
        bad = []
        tq, ro = qstats.get("twoq_err_max"), qstats.get("readout_max")
        if tq is not None and tq > MAX_TWOQ_ERR:
            bad.append(f"twoq_err_max {tq:.4f} > {MAX_TWOQ_ERR}")
        if ro is not None and ro > MAX_READOUT_ERR:
            bad.append(f"readout_max {ro:.4f} > {MAX_READOUT_ERR}")
        if bad:
            print(f"[S4 ABORT] chain-quality gate failed: {'; '.join(bad)}. "
                  f"Pin a cleaner --backend or set ALLOW_BAD_CHAIN=True.")
            raise SystemExit(1)
    return qubit_list


def main() -> None:
    ap = argparse.ArgumentParser(description="QDEP Stage 4 -- full 2018 model at scale (HW driver)")
    ap.add_argument("--backend", type=str, default=None,
                    help="hardware backend name; omit to run on the density-matrix Aer sim")
    ap.add_argument("--widths", type=str, default="3,4,5", help="comma list of population widths to sweep")
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--death", choices=["unitary", "damping"], default="unitary")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print + save the annotated circuit (each Darwinian operator labeled) then run")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="with --dump-circuit: draw and exit, do NOT submit to hardware")
    ap.add_argument("--name", type=str, default="qalife_m4")
    args = ap.parse_args()
    args.sim = args.backend is None      # no --backend => density-matrix Aer sim

    if INTERACTION == "both":
        print("[S4] set INTERACTION to 'nn' or 'longrange' (not 'both') "
              "for a clean witness comparison.")
        raise SystemExit(2)

    widths = [int(w) for w in args.widths.split(",") if w.strip()]

    # --- certified entropy (fail-closed on hardware; sim may PRNG-fallback) --------
    client = None
    api_key = os.environ.get("QEAAS_API_KEY") or _read_env_key("QEAAS_API_KEY")
    qrng_url = os.environ.get("QEAAS_API_URL") or QEAAS_URL
    if api_key:
        client = QRNGClient(qrng_url, api_key)
        try:
            h = client.health()
            print(f"Q-EaaS  : {qrng_url}  health: {h.status}")
            if h.status != "ok" and not args.sim:
                print("[S4 ABORT] Q-EaaS not ok (fail-closed on hardware)."); raise SystemExit(1)
        except QRNGUnavailable as exc:
            if not args.sim:
                print(f"[S4 ABORT] Q-EaaS unavailable (fail-closed on hardware): {exc}")
                raise SystemExit(1)
            client = None
    elif not args.sim:
        print("[S4 ABORT] QEAAS_API_KEY not set (fail-closed on hardware)."); raise SystemExit(1)

    def thetas_for(width: int, repeat: int) -> list[float]:
        if client is not None:
            return qrng_thetas(client, width, MUT_SCALE, repeat)
        return q4._sim_thetas(width, 1000 * repeat + width, mut_scale=MUT_SCALE)

    # --- backend ---------------------------------------------------------------
    backend = None
    backend_name = "density_matrix_sim"
    if not args.sim:
        backend = connect(args.backend)
        backend_name = backend.name
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits)")

    #--- print circuit --------------------------
    if args.dump_circuit:
        W0 = widths[0]
        dump_circuit(W0, args.steps, thetas_for(W0, 0), INTERACTION, args.death, args.name)
        if args.draw_only:
            raise SystemExit(0)

    result: dict[str, Any] = {
        "meta": {"stage": 4, "model": "AlvarezRodriguez2018_full", "backend": backend_name,
                 "steps": args.steps, "interaction": INTERACTION,
                 "death": args.death, "mut_scale": MUT_SCALE, "delta": q4.AGING_DELTA,
                 "gamma": q4.DAMP_GAMMA, "alive_thresh": q4.ALIVE_THRESH, "shots": args.shots,
                 "repeats": REPEATS, "k": K, "widths": widths, "sim": args.sim},
        "by_width": {},
    }

    print(f"=== Stage 4 SCALE: widths={widths} steps={args.steps} interaction={INTERACTION} "
          f"death={args.death} on {backend_name} ===")

    witness_mean: list[float] = []
    witness_sig: list[float] = []
    sep_mean: list[float] = []

    # ---- main run ----
    for W in widths:
        nq = 2 * W + (1 if args.death == "damping" else 0)
        qubit_list: list[int] = []
        if not args.sim:
            qubit_list = gated_chain(backend, nq)

        w_reps, s_reps, alive_reps, deep_reps = [], [], [], []
        for r in range(REPEATS):
            thetas = thetas_for(W, r)

            qc = build_measured(W, args.steps, thetas, INTERACTION, args.death)
            # run: density-matrix Aer sim, or the hardware backend via the sampler pipeline
            if args.sim:
                counts = SIM.run(transpile(qc, SIM), shots=args.shots).result().get_counts()
            else:
                init = qubit_list if len(qubit_list) == qc.num_qubits else None
                pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                                  initial_layout=init)
                raw_meas, _jobs, _qs = run_sampler(backend, pm.run(qc), args.shots)
                counts = {}
                for s in raw_meas:               # run_sampler returns per-shot 'c' strings
                    counts[s] = counts.get(s, 0) + 1


            geno_qs = [q4.geno_q(k) for k in range(W)]
            joint, sep = q4.xbasis_witness_from_counts(counts, geno_qs)

            #-- translates from raw data to lineage ----------
            pz = q4.phenotype_z_from_counts(counts, W)
            w_reps.append(joint); s_reps.append(sep)
            alive_reps.append(q4.alive_population(pz))
            deep_reps.append(q4.deepest_surviving_lineage(pz))

        wm, ws = float(np.mean(w_reps)), float(np.std(w_reps))
        sm = float(np.mean(s_reps))
        # shot-noise floor added in quadrature to the repeat spread
        ws = math.sqrt(ws ** 2 + 1.0 / args.shots)
        witness_mean.append(wm); witness_sig.append(ws); sep_mean.append(sm)
        signal = wm - sm
        survives = signal > K * ws
        result["by_width"][str(W)] = {
            "witness_joint_mean": wm, "witness_joint_sigma": ws, "separable_mean": sm,
            "entanglement_signal": signal, "survives": bool(survives),
            "alive_mean": float(np.mean(alive_reps)), "deepest_mean": float(np.mean(deep_reps)),
        }
        print(f"  W={W:2}  witness<X^W>={wm:+.3f}+-{ws:.3f}  sep={sm:+.3f}  "
              f"signal={signal:+.3f}  {'ALIVE' if survives else 'dead '}  | "
              f"pop alive~{np.mean(alive_reps):.1f}/{W} deepest~{np.mean(deep_reps):.1f}")

    depth = q4.entanglement_depth(witness_mean, sep_mean, witness_sig, k=K)
    depth_W = widths[depth] if depth >= 0 else None
    result["meta"]["genealogical_entanglement_depth_W"] = depth_W
    print(f"\n  genealogical entanglement depth: "
          f"{'W=' + str(depth_W) if depth_W else 'none survived'} "
          f"(deepest width whose witness beats the classical null by {K}sigma)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tag = timestamp() if not args.sim else "sim"
    out = os.path.join(OUTPUT_DIR, f"{args.name}_{INTERACTION}_{args.death}_{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


def _read_env_key(name: str) -> str | None:
    for envp in (os.path.join(_HERE, "..", ".env"), os.path.join(_HERE, ".env")):
        p = os.path.normpath(envp)
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if line.strip().startswith(f"{name}="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None


if __name__ == "__main__":
    main()
