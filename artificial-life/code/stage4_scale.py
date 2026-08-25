#!/usr/bin/env python3
"""Stage 4 scale driver -- the full 2018 quantum-artificial-life model, ON HARDWARE.

Runs the model built + sim-verified in ``stage4_qalife.py`` on a 156-qubit Heron-r2, pushes
the population width, and reports the Month-4 headline:

  * QUANTUM headline -- genealogical entanglement depth: the largest width W whose witness
    <X^{otimes W}> over the genotype line beats the separable (classical) null by k*sigma.
    This is the observable with NO classical surrogate -- the 2018 paper's "entanglement
    spreads throughout generations", now scaled far past its ~4-qubit / 1-generation origin.
  * POPULATION context -- alive-count and deepest-surviving-lineage from the phenotype Z
    readout (a classical diagonal observable, reported as context, not as the quantum claim).

One circuit per (width, repeat) measures BOTH: genotypes in the X basis (H then read =
witness) and phenotypes in the Z basis (alive-count) -- different qubits, one job.

Reuses, unchanged: the certified Q-EaaS entropy stream (CD-7 fail-closed) for mutation
angles; ``layout.best_chain`` + the Month-3 chain-quality gate (dead-edge / bad-readout
abort); ``pipeline_common`` connect/run_sampler.

Usage:
    cd artificial-life/code
    python stage4_scale.py --sim --widths 3,4,5 --steps 4 --interaction nn --death unitary
    python stage4_scale.py --no-sim --backend ibm_marrakesh --widths 4,6,8 --steps 4 \\
        --interaction nn --death unitary --repeats 3 --name qalife_m4p2
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
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

import stage4_qalife as q4

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
SIM = AerSimulator(method="density_matrix")   # density_matrix so the damping arm sims too
QEAAS_URL_DEFAULT = "https://api.qeaas.eu/"

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


# ---------------------------------------------------------------------------
# Mutation angles from the certified Q-EaaS stream (CD-7 fail-closed on hardware)
# ---------------------------------------------------------------------------
def qrng_thetas(client: QRNGClient, width: int, mut_scale: float, repeat: int) -> list[float]:
    """`width` mutation angles in [0, mut_scale*pi) from certified quantum entropy (CD-7).
    Fetch 32-byte hex blocks until 4*width bytes are in hand; theta_k = mut_scale*pi*(u32/2^32)
    from a disjoint 4-byte slice. Small mut_scale keeps the genealogical GHZ witness alive
    deep (mutation = small variation). Fail-closed: QRNGUnavailable propagates."""
    need = 4 * width
    flat = bytearray()
    while len(flat) < need:
        resp = client.fetch(size=32, fmt="hex")        # raises QRNGUnavailable -> abort
        flat.extend(bytes.fromhex(resp.data))
    out = []
    for k in range(width):
        u = int.from_bytes(bytes(flat[4 * k:4 * k + 4]), "big")
        out.append(mut_scale * math.pi * (u / 2 ** 32))
    return out


# ---------------------------------------------------------------------------
# Circuit: full model + dual-basis readout (genotypes X = witness, phenotypes Z = alive)
# ---------------------------------------------------------------------------
def build_measured(width: int, steps: int, thetas: list[float], interaction: str,
                   death: str, delta: float, gamma: float, routing: str = "swap",
                   annotate: bool = False) -> QuantumCircuit:
    qc = q4.build_population(width, steps, thetas, interaction, death=death, founder_equator=True,
                             delta=delta, gamma=gamma, measure=False, annotate=annotate,
                             routing=routing)
    q4._bar(qc, annotate, "X-basis (witness)")
    for k in range(width):
        qc.h(q4.geno_q(k))                 # rotate genotypes to the X basis for the witness
    # measure only the DATA qubits (geno/pheno + damping bath) into a named 'c' register;
    # teleport corridor ancillas are mid-circuit-measured into 'tel' and excluded here.
    n_data = 2 * width + (1 if death == "damping" else 0)
    from qiskit import ClassicalRegister
    creg = ClassicalRegister(n_data, "c")
    qc.add_register(creg)
    for q in range(n_data):
        qc.measure(q, creg[q])
    return qc


def dump_circuit(width: int, steps: int, thetas: list[float], interaction: str, death: str,
                 delta: float, gamma: float, name: str, routing: str = "swap") -> None:
    """Build the smallest paper-faithful circuit, annotate each Darwinian operator, print the
    diagram + a gate->operator legend, and save the drawing + QASM to research_runs."""
    qc = build_measured(width, steps, thetas, interaction, death, delta, gamma,
                        routing=routing, annotate=True)
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
    if routing == "teleport" and interaction == "longrange":
        print("    teleported SWAP(p_k,p_j) = INTERACTION  (long-range predation, constant-depth")
        print("                               3x teleport-CNOT over 2 corridor ancillas + feed-fwd)")
    else:
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


# ---------------------------------------------------------------------------
# chain-quality gate (Month-3 fix, copied so this file stands alone)
# ---------------------------------------------------------------------------
def gated_chain(backend: Any, nq: int, args: argparse.Namespace) -> list[int]:
    from layout import best_chain
    try:
        qubit_list, qstats = best_chain(backend, nq)
    except RuntimeError as exc:
        print(f"[S4 ABORT] no clean chain of {nq} qubits: {exc}")
        raise SystemExit(1)
    print(f"Auto qubit chain (live calib): {qstats}")
    if not args.allow_bad_chain:
        bad = []
        tq, ro = qstats.get("twoq_err_max"), qstats.get("readout_max")
        if tq is not None and tq > args.max_twoq_err:
            bad.append(f"twoq_err_max {tq:.4f} > {args.max_twoq_err}")
        if ro is not None and ro > args.max_readout_err:
            bad.append(f"readout_max {ro:.4f} > {args.max_readout_err}")
        if bad:
            print(f"[S4 ABORT] chain-quality gate failed: {'; '.join(bad)}. "
                  f"Pin a cleaner --backend or bypass with --allow-bad-chain.")
            raise SystemExit(1)
    return qubit_list


# ---------------------------------------------------------------------------
# Dispatch: sim (density-matrix Aer) or Heron-r2
# ---------------------------------------------------------------------------
def run_counts(qc: QuantumCircuit, shots: int, args: argparse.Namespace,
               backend: Any, qubit_list: list[int]) -> dict[str, int]:
    if args.sim:
        raw = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
        # with a teleport 'tel' register present, get_counts keys are "<c> <tel>" (space
        # separated; 'c' added last => leftmost). Collapse onto the 'c' register only.
        counts: dict[str, int] = {}
        for key, cnt in raw.items():
            c = key.split()[0] if " " in key else key
            counts[c] = counts.get(c, 0) + cnt
        return counts
    init = qubit_list if (qubit_list and len(qubit_list) == qc.num_qubits) else None
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend, initial_layout=init)
    isa = pm.run(qc)
    raw_meas, _jobs, _qs = run_sampler(backend, isa, shots)
    counts: dict[str, int] = {}
    for s in raw_meas:                       # run_sampler returns per-shot 'c' strings
        counts[s] = counts.get(s, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="QDEP Stage 4 -- full 2018 model at scale (HW driver)")
    ap.add_argument("--sim", action="store_true", help="density-matrix Aer instead of hardware")
    ap.add_argument("--no-sim", dest="sim", action="store_false")
    ap.set_defaults(sim=True)
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--widths", type=str, default="3,4,5", help="comma list of population widths to sweep")
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--interaction", choices=["none", "nn", "longrange", "both"], default="nn")
    ap.add_argument("--routing", choices=["swap", "teleport"], default="swap",
                    help="how the longrange interaction SWAP is realized (teleport = Phase-2b, TODO)")
    ap.add_argument("--death", choices=["unitary", "damping"], default="unitary")
    ap.add_argument("--delta", type=float, default=q4.AGING_DELTA)
    ap.add_argument("--gamma", type=float, default=q4.DAMP_GAMMA)
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.10,
                    help="mutation strength (fraction of pi); small => witness survives deep")
    ap.add_argument("--alive-thresh", dest="alive_thresh", type=float, default=q4.ALIVE_THRESH)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--repeats", type=int, default=3, help="repeats for sigma error bars")
    ap.add_argument("--k", type=float, default=2.0, help="witness must beat null by k*sigma")
    ap.add_argument("--max-twoq-err", dest="max_twoq_err", type=float, default=0.05)
    ap.add_argument("--max-readout-err", dest="max_readout_err", type=float, default=0.15)
    ap.add_argument("--allow-bad-chain", dest="allow_bad_chain", action="store_true", default=False)
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=None)
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print + save the annotated circuit (each Darwinian operator labeled) then run")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="with --dump-circuit: draw and exit, do NOT submit to hardware")
    ap.add_argument("--name", type=str, default="qalife_m4")
    args = ap.parse_args()

    if args.routing == "teleport" and args.interaction != "longrange":
        print("[S4] --routing teleport only affects the long-range interaction SWAP; "
              "use --interaction longrange (nn/none route trivially).")
        raise SystemExit(2)
    if args.interaction == "both":
        print("[S4] run --interaction nn and --interaction longrange as separate invocations "
              "for a clean witness comparison.")
        raise SystemExit(2)

    widths = [int(w) for w in args.widths.split(",") if w.strip()]

    # --- certified entropy (fail-closed on hardware; sim may PRNG-fallback) --------
    client = None
    api_key = os.environ.get("QEAAS_API_KEY") or _read_env_key("QEAAS_API_KEY")
    qrng_url = args.qrng_url or os.environ.get("QEAAS_API_URL") or QEAAS_URL_DEFAULT
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
            return qrng_thetas(client, width, args.mut_scale, repeat)
        return q4._sim_thetas(width, 1000 * repeat + width, mut_scale=args.mut_scale)

    # --- backend ---------------------------------------------------------------
    backend = None
    backend_name = "density_matrix_sim"
    if not args.sim:
        backend = connect(args.backend)
        backend_name = backend.name
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits)")

    if args.dump_circuit:
        W0 = widths[0]
        dump_circuit(W0, args.steps, thetas_for(W0, 0), args.interaction, args.death,
                     args.delta, args.gamma, args.name, routing=args.routing)
        if args.draw_only:
            raise SystemExit(0)

    result: dict[str, Any] = {
        "meta": {"stage": 4, "model": "AlvarezRodriguez2018_full", "backend": backend_name,
                 "steps": args.steps, "interaction": args.interaction, "routing": args.routing,
                 "death": args.death, "mut_scale": args.mut_scale, "delta": args.delta,
                 "gamma": args.gamma, "alive_thresh": args.alive_thresh, "shots": args.shots,
                 "repeats": args.repeats, "k": args.k, "widths": widths, "sim": args.sim},
        "by_width": {},
    }

    print(f"=== Stage 4 SCALE: widths={widths} steps={args.steps} interaction={args.interaction} "
          f"death={args.death} on {backend_name} ===")

    witness_mean: list[float] = []
    witness_sig: list[float] = []
    sep_mean: list[float] = []

    for W in widths:
        nq = 2 * W + (1 if args.death == "damping" else 0)
        qubit_list: list[int] = []
        if not args.sim:
            qubit_list = gated_chain(backend, nq, args)

        w_reps, s_reps, alive_reps, deep_reps = [], [], [], []
        for r in range(args.repeats):
            thetas = thetas_for(W, r)
            qc = build_measured(W, args.steps, thetas, args.interaction, args.death,
                                args.delta, args.gamma, routing=args.routing)
            counts = run_counts(qc, args.shots, args, backend, qubit_list)
            geno_qs = [q4.geno_q(k) for k in range(W)]
            pheno_qs = [q4.pheno_q(k) for k in range(W)]
            joint, sep = q4.xbasis_witness_from_counts(counts, geno_qs)
            pz = [1.0 - 2.0 * (sum(c for b, c in counts.items() if b[-(pq + 1)] == "1")
                               / (sum(counts.values()) or 1)) for pq in pheno_qs]
            w_reps.append(joint); s_reps.append(sep)
            alive_reps.append(q4.alive_population(pz, args.alive_thresh))
            deep_reps.append(q4.deepest_surviving_lineage(pz, args.alive_thresh))

        wm, ws = float(np.mean(w_reps)), float(np.std(w_reps))
        sm = float(np.mean(s_reps))
        # shot-noise floor added in quadrature to the repeat spread
        ws = math.sqrt(ws ** 2 + 1.0 / args.shots)
        witness_mean.append(wm); witness_sig.append(ws); sep_mean.append(sm)
        signal = wm - sm
        survives = signal > args.k * ws
        result["by_width"][str(W)] = {
            "witness_joint_mean": wm, "witness_joint_sigma": ws, "separable_mean": sm,
            "entanglement_signal": signal, "survives": bool(survives),
            "alive_mean": float(np.mean(alive_reps)), "deepest_mean": float(np.mean(deep_reps)),
        }
        print(f"  W={W:2}  witness<X^W>={wm:+.3f}+-{ws:.3f}  sep={sm:+.3f}  "
              f"signal={signal:+.3f}  {'ALIVE' if survives else 'dead '}  | "
              f"pop alive~{np.mean(alive_reps):.1f}/{W} deepest~{np.mean(deep_reps):.1f}")

    depth = q4.entanglement_depth(witness_mean, sep_mean, witness_sig, k=args.k)
    depth_W = widths[depth] if depth >= 0 else None
    result["meta"]["genealogical_entanglement_depth_W"] = depth_W
    print(f"\n  HEADLINE genealogical entanglement depth: "
          f"{'W=' + str(depth_W) if depth_W else 'none survived'} "
          f"(deepest width whose witness beats the classical null by {args.k}sigma)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tag = timestamp() if not args.sim else "sim"
    out = os.path.join(OUTPUT_DIR, f"{args.name}_{args.interaction}_{args.death}_{backend_name}_{tag}.json")
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
