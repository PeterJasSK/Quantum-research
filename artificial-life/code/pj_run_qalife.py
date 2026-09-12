#!/usr/bin/env python3
"""PJ0 germ/soma hardware driver -- BUILD + EVALUATE STATICALLY (no run in this ticket).

Mirrors ``run_qalife.py`` structure but for the germ/soma organism (``pj_qalife.py``). This
ticket delivers a transpile-ready, chain-quality-gated, measured germ/soma circuit at ANY W
(W12 anchor) whose correctness is shown by ``--dump-circuit`` + scheduled-circuit inspection --
NOT by submitting to hardware (OQ-4). The sampler run path is WIRED BUT DORMANT: the developer
runs the sweeps later. ``--dump-circuit`` NEVER submits (draw-only is implied); the live path is
reachable only with an explicit ``--run`` + ``--backend`` (still gated so nothing fires here).

What this driver builds + evaluates statically:
  * build_measured_germsoma -- H on GENOTYPE qubits only (separable soma stays in Z; entangled
    A/B H's phenotypes too), classical register, measure. Witness = genotype-only (CD-3).
  * transpile-readiness + fail-closed chain-quality gate (CD-5) so the circuit is submit-ready.
  * selective DD (rung 2, AC-PJ0.3): PadDynamicalDecoupling targeted at GENOTYPE physical qubits
    only; phenotypes DD-free (the physical Weismann barrier). Verified by inspecting the
    SCHEDULED circuit.
  * natural-decay aging clock (rung 2, AC-PJ0.2): per-soma delay scaled by age; aging_order
    deviation measured statically, gated on AGING_ORDER_TOL (bounded, not rigid -- Q6).
  * JSON run schema (dormant) extended with soma_death / phenotype / selective_dd / kept_fraction
    / meta.calibration / meta.t1_band / witness_soma_on|off for the developer's later runs.

Usage (static evaluation only -- no hardware fired):
    cd artificial-life/code
    python pj_run_qalife.py --dump-circuit --widths 12 --steps 6
    python pj_run_qalife.py --dump-circuit --widths 4 --phenotype entangled
    python pj_run_qalife.py --schedule-report --widths 12 --steps 6   # DD + aging-order (needs --backend for real timing)
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

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import pj_qalife as pj
import qalife as q4

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
QEAAS_URL = "https://api.qeaas.eu/"

# --- fixed study parameters (edit here; not CLI knobs) -------------------------
INTERACTION = "none"        # single organism, no competition (PJ1 adds it)
REPEATS = 1                 # repeats per width for sigma error bars (developer's runs)
K = 2.0                     # witness must beat the separable null by K*sigma to survive
MUT_SCALE = 0.0             # faithful 2018: clean GHZ witness (Q5)
SOMA_DEATH = "natural"      # acceptance gate (Q6); 'local_damping' selectable as reference
PHENOTYPE = "separable"     # faithful diagonal soma; 'entangled' is the A/B contrast
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
    from pipeline_common import connect  # noqa: E402  (run_sampler/timestamp: dormant run path)
except Exception:
    _stub = types.ModuleType("pipeline_common")
    _stub.connect = lambda *x, **k: None
    _stub.run_sampler = lambda *x, **k: None
    _stub.timestamp = lambda: "sim"
    sys.modules["pipeline_common"] = _stub
    from pipeline_common import connect  # noqa: E402

from qrng_client import QRNGClient  # noqa: E402  (QRNGUnavailable used by the dormant run path)


def qrng_thetas(client: QRNGClient, width: int, mut_scale: float, repeat: int) -> list[float]:
    """`width` mutation angles in [0, mut_scale*pi) from certified quantum entropy (CD-6
    fail-closed). Same slicing as run_qalife.qrng_thetas."""
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


# ---------------------------------------------------------------------------
# Selective DD (rung 2, AC-PJ0.3) -- DD on GENOTYPE physical qubits only.
# ---------------------------------------------------------------------------
def schedule_with_selective_dd(qc: QuantumCircuit, backend: Any, width: int, *,
                               soma_death: str = SOMA_DEATH) -> QuantumCircuit:
    """Transpile + schedule with dynamical decoupling padded on the GENOTYPE physical qubits
    only (phenotypes DD-free = the Weismann barrier). Needs a real backend for gate timing;
    returns the scheduled circuit for static inspection. No submission."""
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
    static correctness report, save the drawing. NEVER submits (draw-only)."""
    qc = build_measured_germsoma(width, steps, thetas, soma_death=soma_death,
                                 phenotype=phenotype, annotate=True)
    has_bath = soma_death in pj._BATH_MODES
    # rung-0 / Static-Test-1 concern the BIOLOGY -> report on the bare build (the readout-basis
    # H on genotypes legitimately lands after the soma phase and is not gene-passing).
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
    print(f"\n  circuit saved -> {txt}")


def schedule_report(width: int, steps: int, thetas: list[float], backend: Any, *,
                    soma_death: str, phenotype: str) -> None:
    """Static rung-2 evaluation: schedule with selective DD, then confirm (a) DD lands on
    genotype qubits only (phenotypes DD-free) and (b) aging-order deviation is bounded. Reads
    the scheduled circuit -- no submission."""
    qc = build_measured_germsoma(width, steps, thetas, soma_death=soma_death, phenotype=phenotype)
    if backend is None:
        print("[PJ0] --schedule-report needs --backend for gate timing (no submission is made).")
        print("      DD/aging-order require a scheduled circuit; on an unscheduled circuit the")
        print("      aging-order deviation is trivially 0. Pass --backend to evaluate for real.")
        return
    scheduled = schedule_with_selective_dd(qc, backend, width, soma_death=soma_death)
    has_bath = soma_death in pj._BATH_MODES

    # (a) DD placement: count DD X-gate pairs per physical qubit; confirm phenotypes DD-free.
    layout = scheduled.layout
    v2p = layout.final_index_layout() if layout is not None else []
    germ_phys = {v2p[v] for v in pj.witness_qubits(width, has_bath=has_bath) if v < len(v2p)}
    soma_phys = {v2p[v] for v in pj.soma_qubits(width, has_bath=has_bath) if v < len(v2p)}
    dd_on: dict[int, int] = {}
    for inst in scheduled.data:
        if inst.operation.name != "x":
            continue
        for b in inst.qubits:
            qi = scheduled.find_bit(b).index
            dd_on[qi] = dd_on.get(qi, 0) + 1
    dd_germ = sum(v for q, v in dd_on.items() if q in germ_phys)
    dd_soma = sum(v for q, v in dd_on.items() if q in soma_phys)
    print("\n--- RUNG 2: SELECTIVE DD (AC-PJ0.3) ---")
    print(f"  DD X-gates on germ-line qubits: {dd_germ}")
    print(f"  DD X-gates on soma qubits:      {dd_soma}  ({'DD-free -> OK' if dd_soma == 0 else 'LEAK'})")

    # (b) aging-order deviation on the scheduled circuit (bounded, not rigid -- Q6).
    dev = pj.aging_order_deviation(scheduled, width, has_bath=has_bath)
    print("\n--- RUNG 2: AGING-ORDER DEVIATION (AC-PJ0.2, bounded not rigid) ---")
    print(f"  max_deviation = {dev['max_deviation']} generations  "
          f"(tolerance AGING_ORDER_TOL = {AGING_ORDER_TOL})  "
          f"{'OK' if dev['max_deviation'] <= AGING_ORDER_TOL else 'EXCEEDS -> targeted delays / fallback local_damping'}")
    for row in dev["per_soma"]:
        print(f"    ind {row['individual']:2}  q{row['qubit']:<3}  birth_rank={row['birth_rank']:2} "
              f"idle_rank={row['idle_rank']:2}  shift={row['shift']:+d}")


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
            print(f"[PJ0 ABORT] chain-quality gate failed: {'; '.join(bad)}.")
            raise SystemExit(1)
    return qubit_list


def _run_schema(width: int, backend_name: str, soma_death: str, phenotype: str) -> dict[str, Any]:
    """The (dormant) JSON schema the developer's later runs bank into. Fields present so runs
    accumulate uniformly; no run data is produced in this ticket (OQ-4)."""
    has_bath = soma_death in pj._BATH_MODES
    return {
        "meta": {"stage": "PJ0", "model": "germsoma_weismann", "backend": backend_name,
                 "width": width, "soma_death": soma_death, "phenotype": phenotype,
                 "selective_dd": SELECTIVE_DD, "aging_order_tol": AGING_ORDER_TOL,
                 "interaction": INTERACTION, "mut_scale": MUT_SCALE, "k": K,
                 "delta": pj.AGING_DELTA, "gamma": pj.DAMP_GAMMA, "alive_thresh": pj.ALIVE_THRESH,
                 "calibration": None, "t1_band": None,          # AC-PJ0.5: filled at run time
                 "witness_qubits": pj.witness_qubits(width, has_bath=has_bath)},
        # AC-PJ0.7 comparison hooks -- soma-on / soma-off pairing (hardware analogue of Static
        # Test 1) and kept-fraction; left for the developer to execute.
        "witness_soma_on": None, "witness_soma_off": None, "kept_fraction": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ0 germ/soma driver -- build + evaluate statically (no run in this ticket).")
    ap.add_argument("--backend", type=str, default=None,
                    help="hardware backend name (only used for gate timing in --schedule-report; "
                         "NEVER submitted unless --run is also passed)")
    ap.add_argument("--widths", type=str, default="12",
                    help="comma list of widths (any W; 12 anchor/default)")
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--soma-death", dest="soma_death",
                    choices=["natural", "local_damping", "none"], default=SOMA_DEATH)
    ap.add_argument("--phenotype", choices=["separable", "entangled"], default=PHENOTYPE)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print + save the annotated measured circuit; NEVER submits (draw-only)")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="accepted for parity with run_qalife; --dump-circuit already implies it")
    ap.add_argument("--schedule-report", dest="schedule_report", action="store_true",
                    help="static rung-2 report: selective-DD placement + aging-order deviation")
    ap.add_argument("--run", action="store_true",
                    help="DORMANT in PJ0 (OQ-4): the live sampler path; refuses without --backend")
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="pj0_germsoma")
    args = ap.parse_args()

    widths = [int(w) for w in args.widths.split(",") if w.strip()]

    backend = None
    backend_name = "none"
    if args.backend is not None:
        backend = connect(args.backend)
        backend_name = getattr(backend, "name", str(args.backend))
        print(f"Backend : {backend_name} (timing/layout only; no submission unless --run)")

    def thetas_for(width: int, repeat: int = 0) -> list[float]:
        # PJ0 is static; faithful clean GHZ (MUT_SCALE=0) -> PRNG angles suffice for building.
        return q4._sim_thetas(width, 1000 * repeat + width, mut_scale=MUT_SCALE)

    # ---- static evaluation surfaces (the deliverable) ----
    if args.dump_circuit:
        for W in widths:
            dump_circuit(W, args.steps, thetas_for(W), soma_death=args.soma_death,
                         phenotype=args.phenotype, name=args.name)
        raise SystemExit(0)   # dump NEVER submits (draw-only implied)

    if args.schedule_report:
        for W in widths:
            schedule_report(W, args.steps, thetas_for(W), backend,
                            soma_death=args.soma_death, phenotype=args.phenotype)
        raise SystemExit(0)

    # ---- live run path: DORMANT in this ticket (OQ-4) ----
    if args.run:
        print("[PJ0] the live sampler run path is DORMANT in this ticket (OQ-4: no hardware).")
        print("      The developer runs the sweeps later. Build/schema is verified via")
        print("      --dump-circuit and --schedule-report. Refusing to submit.")
        raise SystemExit(2)

    print("PJ0 germ/soma driver -- static evaluation only. Choose one of:")
    print("  --dump-circuit     print + save the measured circuit (never submits)")
    print("  --schedule-report  selective-DD + aging-order (add --backend for real timing)")
    print(f"\n  (dormant run schema for W={widths[0]}):")
    print("  " + json.dumps(_run_schema(widths[0], backend_name, args.soma_death, args.phenotype),
                            indent=2, default=str))


if __name__ == "__main__":
    main()
