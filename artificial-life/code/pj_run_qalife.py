#!/usr/bin/env python3
"""PJ0 germ/soma hardware driver -- BUILD + RUN the Weismann-barrier organism.

Mirrors ``run_qalife.py`` structure but for the germ/soma organism (``pj_qalife.py``). Runs the
single-lineage germ/soma model on hardware (or the density-matrix Aer sim) and reports the
genotype-only genealogical entanglement witness <X^W>:

  * QUANTUM headline -- germ-line witness <X^{otimes W}> over the GENOTYPE qubits beats the
    separable (classical) null by k*sigma. Soma stays diagonal (Z), excluded from the witness
    (CD-3). The 'entangled' A/B mode restores cx(g,p) and folds the phenotypes into the witness
    to DEMONSTRATE the coupling would cost it.
  * POPULATION context -- alive-count + deepest-surviving-lineage from the soma Z readout
    (classical diagonal observable; reported as context, not the quantum claim). Unavailable in
    the 'entangled' arm (phenotypes are then in X).

What the driver runs:
  * build_measured_germsoma -- germ line rotated into X (witness), soma diagonal, measured.
  * transpile via opt-3 preset (VF2/Sabre layout+routing), chain-quality gate (CD-5) on hardware.
  * selective DD (AC-PJ0.3): PadDynamicalDecoupling on GENOTYPE physical qubits only; phenotypes
    DD-free (the physical Weismann barrier). Enabled on hardware via SELECTIVE_DD.
  * certified Q-EaaS entropy for mutation angles (fail-closed on hardware).
  * JSON run schema with soma_death / phenotype / selective_dd / kept_fraction / meta.calibration.

Usage (omit --backend for the Aer sim; pass one to run on that hardware):
    cd artificial-life/code
    python pj_run_qalife.py --widths 12 --steps 6
    python pj_run_qalife.py --backend ibm_kingston --widths 12 --steps 6 --name pj0_germsoma
    python pj_run_qalife.py --dump-circuit --draw-only --widths 12 --steps 6   # draw, no run
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

import pj_qalife as pj
import qalife as q4

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
SIM = AerSimulator(method="density_matrix")   # density_matrix so the local_damping arm sims too
QEAAS_URL = "https://api.qeaas.eu/"

# --- fixed study parameters (edit here; not CLI knobs) -------------------------
INTERACTION = "none"        # single organism, no competition (PJ1 adds it)
REPEATS = 1                 # repeats per width for sigma error bars
K = 2.0                     # witness must beat the separable null by K*sigma to survive
MUT_SCALE = 0.0             # faithful 2018: clean GHZ witness (Q5)

# SOMA_DEATH -- HOW the mortal soma (phenotype) qubit dies each life-cycle step.
#   "natural"       : T1 idle toward |0>; NO death operator, NO bath ancilla. The aging clock
#                     is the scheduler's idle pattern (per-soma delay + selective DD on the germ
#                     line only). Leanest segment (2W qubits: germ + soma, no bath).
#   "local_damping" : the faithful damping arm WITH the cx(g,p) back-action removed and the bath
#                     scoped to the phenotype -- controlled, reproducible rate. Segment = 3W.
#   "none"          : control arm -- no death applied, age ignored.
SOMA_DEATH = "natural"

# PHENOTYPE -- HOW the soma expresses the genotype.
#   "separable" : faithful diagonal soma via ry(aged); NO cx(g,p) -> soma excluded from the
#                 witness, the certified claim is the genotype-only <X^W>.
#   "entangled" : A/B contrast -- restores cx(g,p) before the SAME ry(aged), folding the mortal
#                 soma into the witness to show it would cost the signal.
PHENOTYPE = "separable"
SELECTIVE_DD = True         # DD on genotype (germ-line) qubits only -- the Weismann barrier (I6)
AGING_ORDER_TOL = 2         # bounded aging-order deviation, in generations (studied param, Q6)
MAX_TWOQ_ERR = 0.05         # chain-quality gate: max 2-qubit error along the chain (CD-5)
MAX_READOUT_ERR = 0.15      # chain-quality gate: max readout error along the chain (CD-5)
ALLOW_BAD_CHAIN = False     # True bypasses the chain-quality gate

# --- reuse the submission pipeline + QRNG client (same probe as run_qalife) -----
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


# Mutation angles from the certified Q-EaaS stream (CD-6 fail-closed on hardware).
def qrng_thetas(client: QRNGClient, width: int, mut_scale: float, repeat: int) -> list[float]:
    """`width` mutation angles in [0, mut_scale*pi) from certified quantum entropy. Same slicing
    as run_qalife.qrng_thetas; QRNGUnavailable propagates (fail-closed)."""
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


# ---------------------------------------------------------------------------
# Measured build -- witness = genotype-only (CD-3).
# ---------------------------------------------------------------------------
def build_measured_germsoma(width: int, steps: int, thetas: list[float], *,
                            soma_death: str = SOMA_DEATH, phenotype: str = PHENOTYPE,
                            annotate: bool = False) -> QuantumCircuit:
    """Build the germ/soma circuit, rotate genotypes into X (witness), measure. Separable soma
    stays diagonal (Z, excluded from the witness); the 'entangled' A/B mode H's phenotypes too."""
    qc = pj.build_germsoma(width, steps, thetas, phenotype=phenotype, soma_death=soma_death,
                           annotate=annotate)
    pj._bar(qc, annotate, "X-basis (witness)")
    qc = pj.to_witness_basis(qc, width, phenotype=phenotype, soma_death=soma_death)
    n_data = qc.num_qubits
    creg = ClassicalRegister(n_data, "c")
    qc.add_register(creg)
    qc.measure(range(n_data), creg)
    return qc


def witness_qs_for(width: int, soma_death: str, phenotype: str) -> list[int]:
    """Witness qubit set fed to xbasis_witness_from_counts. Genotype only (separable); genotype
    + phenotype for the entangled A/B arm (the soma then carries half the GHZ)."""
    has_bath = soma_death in pj._BATH_MODES
    qs = pj.witness_qubits(width, has_bath=has_bath)
    if phenotype == "entangled":
        qs = qs + [pj.pheno_q(0, k, width, has_bath) for k in range(width)]
    return qs


def soma_z_from_counts(counts: dict[str, int], width: int, has_bath: bool) -> list[float]:
    """Soma <sigma_z> per individual from counts (germ/soma layout). Only meaningful in the
    separable arm, where phenotypes stay diagonal (Z)."""
    total = sum(counts.values()) or 1
    out = []
    for k in range(width):
        q = pj.pheno_q(0, k, width, has_bath)
        p1 = sum(c for bits, c in counts.items() if bits[-(q + 1)] == "1") / total
        out.append(1.0 - 2.0 * p1)
    return out


# ---------------------------------------------------------------------------
# Selective DD (rung 2, AC-PJ0.3) -- DD on GENOTYPE physical qubits only.
# ---------------------------------------------------------------------------
def schedule_with_selective_dd(qc: QuantumCircuit, backend: Any, width: int, *,
                               soma_death: str = SOMA_DEATH) -> QuantumCircuit:
    """Transpile + schedule with dynamical decoupling padded on the GENOTYPE physical qubits
    only (phenotypes DD-free = the Weismann barrier). Returns the scheduled, submit-ready
    circuit."""
    from qiskit.circuit.library import XGate
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling

    has_bath = soma_death in pj._BATH_MODES
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    routed = pm.run(qc)

    # map virtual genotype qubits -> physical qubits via the final layout.
    layout = routed.layout
    germ_virtual = pj.witness_qubits(width, has_bath=has_bath)
    germ_physical: list[int] = []
    if layout is not None:
        v2p = layout.final_index_layout()            # virtual index -> physical index
        germ_physical = [v2p[v] for v in germ_virtual if v < len(v2p)]

    target = backend.target
    durations = getattr(target, "durations", lambda: None)()
    dd_seq = [XGate(), XGate()]
    passes = [ALAPScheduleAnalysis(durations=durations),
              PadDynamicalDecoupling(durations=durations, dd_sequence=dd_seq,
                                     qubits=germ_physical or None)]
    scheduled = PassManager(passes).run(routed)
    return scheduled


def dump_circuit(width: int, steps: int, thetas: list[float], *, soma_death: str,
                 phenotype: str, name: str) -> None:
    """Build the measured germ/soma circuit, annotate operators, print the diagram + legend +
    static correctness report, save the drawing + QASM."""
    qc = build_measured_germsoma(width, steps, thetas, soma_death=soma_death,
                                 phenotype=phenotype, annotate=True)
    has_bath = soma_death in pj._BATH_MODES
    bare = pj.build_germsoma(width, steps, thetas, phenotype=phenotype, soma_death=soma_death)
    rep = pj.germsoma_coupling_report(bare, width, has_bath=has_bath)

    print("\n--- PJ0 GERM/SOMA MEASURED CIRCUIT (each barrier = one operator) ---")
    print(f"  W={width} steps={steps} soma_death={soma_death} phenotype={phenotype}")
    print("  gate -> Darwinian operator:")
    print("    Ry(pi/2) on g_0     = FOUNDER            Ry(theta_k) on g_k  = MUTATION")
    print("    CX(g_{k-1}->g_k)    = SELF-REPLICATION   Ry(aged) on p_k     = PHENOTYPE(+aging)")
    if soma_death == "local_damping":
        print("    CRY+CX(p_k,bath)    = ISOLATED SOMA DEATH (local damping; bath on phenotype)")
    elif soma_death == "natural":
        print("    (no death op)       = ISOLATED SOMA DEATH (natural T1 idle + selective DD on germ)")
    if phenotype == "entangled":
        print("    CX(g_k->p_k)        = A/B WOUND (gratuitous; costs the witness)")
    print("    H on g_k + measure  = SELECTIVE-DD target + witness readout (genotypes in X)")
    draw = qc.draw(output="text", fold=-1)
    print("\n" + str(draw))

    print("\n--- STATIC CORRECTNESS ---")
    print(f"  Static Test 1 (geno/soma disjoint): {'YES' if rep['disjoint'] else 'NO'}")
    print(f"  gene-first ordering (rung 0):       {'YES' if rep['gene_first'] else 'NO'}")
    print(f"  witness qubits (genotype only):     {rep['witness_set']}")
    print(f"  gate counts:                        {rep['gate_counts']}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    txt = os.path.join(OUTPUT_DIR, f"{name}_circuit_w{width}_s{steps}_{soma_death}_{phenotype}.txt")
    with open(txt, "w") as f:
        f.write(str(draw))
    try:
        from qiskit.qasm3 import dumps
        with open(os.path.join(OUTPUT_DIR,
                               f"{name}_circuit_w{width}_s{steps}_{soma_death}_{phenotype}.qasm"),
                  "w") as f:
            f.write(dumps(qc))
    except Exception as e:
        print(f"  (qasm export skipped: {e})")
    print(f"\n  circuit saved -> {txt}")


# ---------------------------------------------------------------------------
# Chain-quality gate (CD-5) -- reused from run_qalife.
# ---------------------------------------------------------------------------
def gated_chain(backend: Any, nq: int) -> list[int]:
    from layout import best_chain
    try:
        qubit_list, qstats = best_chain(backend, nq)
    except RuntimeError as exc:
        print(f"[PJ0 ABORT] no clean chain of {nq} qubits: {exc}")
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
            print(f"[PJ0 ABORT] chain-quality gate failed: {'; '.join(bad)}. "
                  f"Pin a cleaner --backend or set ALLOW_BAD_CHAIN=True.")
            raise SystemExit(1)
    return qubit_list


def _read_env_key(name: str) -> str | None:
    for envp in (os.path.join(_HERE, "..", ".env"), os.path.join(_HERE, ".env")):
        p = os.path.normpath(envp)
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if line.strip().startswith(f"{name}="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ0 germ/soma driver -- run the Weismann-barrier organism on hardware "
                    "(or the density-matrix Aer sim) and report the genotype-only witness <X^W>.")
    ap.add_argument("--backend", type=str, default=None,
                    help="hardware backend name; omit to run on the density-matrix Aer sim")
    ap.add_argument("--widths", type=str, default="12",
                    help="comma list of widths (any W; 12 anchor/default)")
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print + save the annotated measured circuit then run")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="with --dump-circuit: draw and exit, do NOT submit")
    ap.add_argument("--name", type=str, default="pj0_germsoma")
    args = ap.parse_args()
    args.sim = args.backend is None      # no --backend => density-matrix Aer sim

    widths = [int(w) for w in args.widths.split(",") if w.strip()]
    has_bath = SOMA_DEATH in pj._BATH_MODES

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
                print("[PJ0 ABORT] Q-EaaS not ok (fail-closed on hardware)."); raise SystemExit(1)
        except QRNGUnavailable as exc:
            if not args.sim:
                print(f"[PJ0 ABORT] Q-EaaS unavailable (fail-closed on hardware): {exc}")
                raise SystemExit(1)
            client = None
    elif not args.sim:
        print("[PJ0 ABORT] QEAAS_API_KEY not set (fail-closed on hardware)."); raise SystemExit(1)

    def thetas_for(width: int, repeat: int = 0) -> list[float]:
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

    # --- print circuit ---------------------------------------------------------
    if args.dump_circuit:
        for W in widths:
            dump_circuit(W, args.steps, thetas_for(W), soma_death=SOMA_DEATH,
                         phenotype=PHENOTYPE, name=args.name)
        if args.draw_only:
            raise SystemExit(0)

    result: dict[str, Any] = {
        "meta": {"stage": "PJ0", "model": "germsoma_weismann", "backend": backend_name,
                 "steps": args.steps, "soma_death": SOMA_DEATH, "phenotype": PHENOTYPE,
                 "selective_dd": SELECTIVE_DD, "aging_order_tol": AGING_ORDER_TOL,
                 "interaction": INTERACTION, "mut_scale": MUT_SCALE, "k": K,
                 "delta": pj.AGING_DELTA, "gamma": pj.DAMP_GAMMA, "alive_thresh": pj.ALIVE_THRESH,
                 "shots": args.shots, "repeats": REPEATS, "widths": widths, "sim": args.sim,
                 "calibration": None, "t1_band": None},
        "by_width": {},
    }

    print(f"=== PJ0 germ/soma: widths={widths} steps={args.steps} soma_death={SOMA_DEATH} "
          f"phenotype={PHENOTYPE} on {backend_name} ===")

    witness_mean: list[float] = []
    witness_sig: list[float] = []
    sep_mean: list[float] = []

    # ---- main run ----
    for W in widths:
        nq = pj.segment_len(W, has_bath)
        qubit_list: list[int] = []
        if not args.sim:
            qubit_list = gated_chain(backend, nq)

        w_reps, s_reps, alive_reps, deep_reps = [], [], [], []
        for r in range(REPEATS):
            thetas = thetas_for(W, r)
            qc = build_measured_germsoma(W, args.steps, thetas, soma_death=SOMA_DEATH,
                                         phenotype=PHENOTYPE)
            # run: density-matrix Aer sim, or the hardware backend via the sampler pipeline
            if args.sim:
                counts = SIM.run(transpile(qc, SIM), shots=args.shots).result().get_counts()
            else:
                # opt-3 (VF2/Sabre) layout+routing; selective DD on genotype qubits only.
                if SELECTIVE_DD:
                    submit_qc = schedule_with_selective_dd(qc, backend, W, soma_death=SOMA_DEATH)
                else:
                    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
                    submit_qc = pm.run(qc)
                raw_meas, _jobs, _qs = run_sampler(backend, submit_qc, args.shots)
                counts = {}
                for s in raw_meas:               # run_sampler returns per-shot 'c' strings
                    counts[s] = counts.get(s, 0) + 1

            witness_qs = witness_qs_for(W, SOMA_DEATH, PHENOTYPE)
            joint, sep = q4.xbasis_witness_from_counts(counts, witness_qs)
            w_reps.append(joint); s_reps.append(sep)
            # alive-count needs soma in Z -- only the separable arm reads it that way
            if PHENOTYPE != "entangled":
                pz = soma_z_from_counts(counts, W, has_bath)
                alive_reps.append(q4.alive_population(pz))
                deep_reps.append(q4.deepest_surviving_lineage(pz))

        wm, ws = float(np.mean(w_reps)), float(np.std(w_reps))
        sm = float(np.mean(s_reps))
        ws = math.sqrt(ws ** 2 + 1.0 / args.shots)      # shot-noise floor in quadrature
        witness_mean.append(wm); witness_sig.append(ws); sep_mean.append(sm)
        signal = wm - sm
        survives = signal > K * ws
        alive_mean = float(np.mean(alive_reps)) if alive_reps else None
        deep_mean = float(np.mean(deep_reps)) if deep_reps else None
        result["by_width"][str(W)] = {
            "witness_joint_mean": wm, "witness_joint_sigma": ws, "separable_mean": sm,
            "entanglement_signal": signal, "survives": bool(survives),
            "alive_mean": alive_mean, "deepest_mean": deep_mean,
        }
        pop = (f"pop alive~{alive_mean:.1f}/{W} deepest~{deep_mean:.1f}"
               if alive_mean is not None else "pop n/a (phenotypes in X for the witness)")
        wlabel = "X^2W" if PHENOTYPE == "entangled" else "X^W"
        print(f"  W={W:2}  witness<{wlabel}>={wm:+.3f}+-{ws:.3f}  sep={sm:+.3f}  "
              f"signal={signal:+.3f}  {'ALIVE' if survives else 'dead '}  | {pop}")

    depth = q4.entanglement_depth(witness_mean, sep_mean, witness_sig, k=K)
    depth_W = widths[depth] if depth >= 0 else None
    result["meta"]["genealogical_entanglement_depth_W"] = depth_W
    print(f"\n  genealogical entanglement depth: "
          f"{'W=' + str(depth_W) if depth_W else 'none survived'} "
          f"(deepest width whose witness beats the classical null by {K}sigma)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tag = timestamp() if not args.sim else "sim"
    out = os.path.join(OUTPUT_DIR, f"{args.name}_{SOMA_DEATH}_{PHENOTYPE}_{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
