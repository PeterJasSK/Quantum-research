#!/usr/bin/env python3
"""PJ2.2b 1D-LINE vivarium driver -- a walking occupancy field + germ witness (DEPTH SCAN).

The 1D sibling of ``2D_alive.py`` (the square-lattice driver). Identical honest model and data
contract; the ONLY difference is the substrate: the organism is a unary occupancy field on a
length-L CHAIN that WALKS (an excitation-conserving rxx+ryy quantum walk between linear neighbours
i-1 / i+1) instead of a 2D grid. The single quantum claim is the germ-line genealogical witness
<X^W>. Three modes (solo / replicate / duo) x two arms (isolated germ line / coupled = the
soma->germ wound).
Same defining lock as 2D: CERTIFIED FRAMES VIA A DEPTH SCAN. On hardware each generation
d in {0..gens-1} is its OWN measured circuit with d walk layers, measured once for occupancy (Z)
+ germ witness (X) with a separable-null control -- NO interpolation on the certified path. Sim
shares the same depth-scan code path on a statevector Aer backend.

Design: imports the shared MODEL from ``pj_qalife`` (``build_line_vivarium`` + the ``line_*``
helpers, the 1D parallel of the ``lat_*`` lattice section) and REUSES PJ0's driver infra BY
IMPORT (``gated_chain``, ``qrng_thetas``, ``connect`` / ``run_sampler`` / ``timestamp``,
``OUTPUT_DIR``). Selective DD on the germ line only, re-used from the lattice pattern.

Usage:
    cd artificial-life/code
    python 1D_alive.py --length 9 --gens 6 --repeats 1            # sim, all 3 modes x 2 arms
    python 1D_alive.py --length 16 --movement-only --gens 6       # sim, L=16 solo (just the movement)
    python 1D_alive.py --dump-circuit --draw-only --length 9 --mode solo
    python 1D_alive.py --backend <heron> --length 9 --mode solo --gens 6 --shots 8192
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import statistics
from typing import Any

from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

import pj_qalife as pj
import qalife as q4

from pj_run_qalife import (          # noqa: E402  -- reuse PJ0 infra, no edit
    OUTPUT_DIR, connect, gated_chain, qrng_thetas, run_sampler, timestamp,
)
from qrng_client import QRNGClient, QRNGUnavailable  # noqa: E402

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))

# --- study parameters -------------------------------------------------------
LENGTH = 9                           # chain length L (9 cells == the 3x3 qubit budget)
WIDTH = 3                            # germ width W (the witness set)
GENS = 6                            # generations 0..5 (the depth axis)
MODES = ("solo", "replicate", "duo")
ARMS = ("isolated", "coupled")
HOP = pj.LINE_HOP                    # isotropic quantum-walk hop angle
K = 2.0                             # significance multiplier (k=2 headline, k=3 reported)
MUT_SCALE = 0.0                     # faithful clean GHZ -> isolate the walk's witness cost
DD_DEFAULT = "x2"                   # PJ2.5: germ-selective DD mode default (off|x2|xy4); x2 == prior behaviour
DD_MODES = ("off", "x2", "xy4")     # off = plain opt-3; x2 = CPMG [X,X]; xy4 = [X,Y,X,Y]
REPEATS = 1
QEAAS_URL = os.environ.get("QEAAS_API_URL", "https://api.qeaas.eu")

LINE_SIM = AerSimulator(method="statevector")
_SV_MAX_QUBITS = 27                  # statevector feasibility cap


# ---------------------------------------------------------------------------
# Measured build -- germ loci in X (witness), body cells in Z (occupancy). ONE circuit.
# ---------------------------------------------------------------------------
def active_witness_qubits(width: int, length: int, mode: str, gens: int) -> list[int]:
    """The germ loci carrying the joint <X^W> at THIS depth. For replicate the daughter germ line
    does not exist until the clone at gen LINE_REP_GEN, so before then the witness is the parent
    block only (H-ing the still-|0> daughter germ would inject random X-parity and null the joint)."""
    if mode == "replicate" and gens < pj.LINE_REP_GEN:
        return [pj.line_witness_q(0, k, width, length) for k in range(width)]
    return pj.line_witness_qubits(width, length, mode)


def build_measured_line(width: int, length: int, gens: int, thetas: list[float], *, mode: str,
                        arm: str, start: int = 0, hop: float = HOP,
                        pokes: list[tuple[int, int, float]] | None = None) -> QuantumCircuit:
    """Build the walk to depth `gens`, rotate the ACTIVE germ loci into X (witness), leave the body
    cells in Z (occupancy), add a classical register, measure all -- one circuit per certified frame."""
    qc = pj.build_line_vivarium(width, length, gens, thetas, mode=mode, arm=arm, start=start,
                                hop=hop, pokes=pokes)
    for q in active_witness_qubits(width, length, mode, gens):
        qc.h(q)                                                   # X-basis readout on the germ only
    n_data = qc.num_qubits
    creg = ClassicalRegister(n_data, "c")
    qc.add_register(creg)
    qc.measure(range(n_data), creg)
    return qc


def _marginal_p1(counts: dict[str, int], q: int, total: int) -> float:
    return sum(c for bits, c in counts.items() if bits[-(q + 1)] == "1") / total


def reduce_counts(counts: dict[str, int], width: int, length: int, *, mode: str,
                  gens: int) -> dict[str, Any]:
    """Measured observables from ONE counts dict: the germ witness + the 1D occupancy field."""
    total = sum(counts.values()) or 1
    joint, sep = q4.xbasis_witness_from_counts(counts,
                                               active_witness_qubits(width, length, mode, gens))
    fields: list[list[float]] = []
    for o in range(pj.line_n_organisms(mode)):
        occ = [round(_marginal_p1(counts, pj.line_body_q(o, i, width, length), total), 4)
               for i in range(length)]
        fields.append(occ)
    overlap = 0.0
    if mode == "duo":
        overlap = sum(min(fields[0][i], fields[1][i]) for i in range(length))
    return {"witness_joint": joint, "separable_null": sep, "fields": fields,
            "overlap": round(float(overlap), 4)}


# ---------------------------------------------------------------------------
# Selective DD on the germ line only -- the EM1 witness lever (PJ2.5, CD-11).
# DD is pure pulse suppression on the IDLE germ (witness) physical qubits; the
# body/vitality/energy qubits stay DD-free (the Weismann barrier). It is NOT
# post-selection -> kept_fraction = 1, the witness stays an unconditional claim.
# ---------------------------------------------------------------------------
def _dd_sequence(dd: str) -> list[Any] | None:
    """Resolve a --dd mode to a PadDynamicalDecoupling pulse sequence (None == no DD)."""
    from qiskit.circuit.library import XGate, YGate
    if dd == "x2":
        return [XGate(), XGate()]                                  # CPMG (prior default)
    if dd == "xy4":
        return [XGate(), YGate(), XGate(), YGate()]                # robust to pulse miscalibration
    return None                                                    # "off"


def _schedule_germ_dd(qc: QuantumCircuit, backend: Any, germ_virtual: list[int], *,
                      dd: str) -> tuple[QuantumCircuit, list[int]]:
    """Transpile at opt-3 then pad DD (dd_sequence) on the germ physical qubits only. Returns the
    submit-ready circuit and the germ PHYSICAL qubit list (barrier evidence). dd='off' -> opt-3 only."""
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling

    routed = generate_preset_pass_manager(optimization_level=3, backend=backend).run(qc)
    germ_physical: list[int] = []
    if routed.layout is not None:
        v2p = routed.layout.final_index_layout()
        germ_physical = [v2p[v] for v in germ_virtual if v < len(v2p)]

    seq = _dd_sequence(dd)
    if seq is None:
        return routed, germ_physical
    durations = getattr(backend.target, "durations", lambda: None)()
    passes = [ALAPScheduleAnalysis(durations=durations),
              PadDynamicalDecoupling(durations=durations, dd_sequence=seq,
                                     qubits=germ_physical or None)]
    return PassManager(passes).run(routed), germ_physical


def schedule_line_selective_dd(qc: QuantumCircuit, backend: Any, width: int, length: int, *,
                               mode: str, dd: str = DD_DEFAULT) -> QuantumCircuit:
    """Germ-only DD for the line path (PJ2.2b). Thin wrapper over _schedule_germ_dd."""
    submit, _phys = _schedule_germ_dd(qc, backend, pj.line_witness_qubits(width, length, mode), dd=dd)
    return submit


def schedule_motile_selective_dd(qc: QuantumCircuit, backend: Any, organisms: int, length: int,
                                 gens: int, rep_gen: int, *,
                                 dd: str = DD_DEFAULT) -> tuple[QuantumCircuit, list[int]]:
    """Germ-only DD for the PJ2.4 motile path -- the lever PJ2.4's hardware runs lacked. Targets the
    ACTIVE germ (witness) set at this depth; body/vitality/energy stay bare (Weismann barrier)."""
    germ_virtual = pj.motile_witness_qubits(organisms, length, gens, rep_gen)
    return _schedule_germ_dd(qc, backend, germ_virtual, dd=dd)


# ---------------------------------------------------------------------------
# The certified depth scan -- one measured circuit per (mode, arm, gen, repeat).
# ---------------------------------------------------------------------------
def _run_counts(qc: QuantumCircuit, *, sim: bool, backend: Any, shots: int, width: int, length: int,
                mode: str, dd: str = DD_DEFAULT) -> dict[str, int]:
    if sim:
        return LINE_SIM.run(transpile(qc, LINE_SIM), shots=shots).result().get_counts()
    if dd != "off":
        submit_qc = schedule_line_selective_dd(qc, backend, width, length, mode=mode, dd=dd)
    else:
        submit_qc = generate_preset_pass_manager(optimization_level=3, backend=backend).run(qc)
    raw_meas, _jobs, _qs = run_sampler(backend, submit_qc, shots)
    counts: dict[str, int] = {}
    for s in raw_meas:
        counts[s] = counts.get(s, 0) + 1
    return counts


def depth_scan(width: int, length: int, gens: int, thetas: list[float], *, mode: str, arm: str,
               start: int, hop: float, sim: bool, backend: Any, shots: int, repeats: int,
               pokes: list[tuple[int, int, float]] | None = None,
               dd: str = DD_DEFAULT) -> list[dict[str, Any]]:
    """The honest frames: for d in range(gens) build a circuit with d walk layers, measure it once
    per repeat, reduce -> one certified frame {gen, fields, w, w_sigma, sep, survives, overlap, n}."""
    sigma_shot = math.sqrt(1.0 / shots)
    frames: list[dict[str, Any]] = []
    for d in range(gens):
        qc = build_measured_line(width, length, d, thetas, mode=mode, arm=arm, start=start,
                                 hop=hop, pokes=pokes)
        joints: list[float] = []
        reduced: dict[str, Any] = {}
        for _rep in range(max(1, repeats)):
            counts = _run_counts(qc, sim=sim, backend=backend, shots=shots, width=width,
                                 length=length, mode=mode, dd=dd)
            reduced = reduce_counts(counts, width, length, mode=mode, gens=d)
            joints.append(reduced["witness_joint"])
        w = statistics.fmean(joints)
        spread = statistics.pstdev(joints) if len(joints) > 1 else 0.0
        w_sigma = math.sqrt(spread ** 2 + sigma_shot ** 2)
        fields = reduced["fields"]
        n_alive = sum(1 for f in fields if sum(f) > 0.05)
        frames.append({
            "gen": d,
            "fields": fields,
            "w": round(float(w), 4),
            "w_sigma": round(float(w_sigma), 4),
            "sep": round(float(reduced["separable_null"]), 4),
            "overlap": reduced["overlap"],
            "n": n_alive,
            "survives": bool(w - reduced["separable_null"] > K * w_sigma),
        })
    return frames


# ---------------------------------------------------------------------------
# QRNG-certified environment (start cell + hop), fail-closed on hardware.
# ---------------------------------------------------------------------------
def qrng_environment(client: QRNGClient | None, length: int, sim: bool) -> tuple[int, float]:
    """Draw the start cell + hop angle from certified quantum entropy (fixed per run). Sim may fall
    back to deterministic defaults; hardware is fail-closed (QRNGUnavailable propagates)."""
    if client is None:
        return 0, HOP
    try:
        resp = client.fetch(size=32, fmt="hex")
    except QRNGUnavailable:
        if sim:
            return 0, HOP                                          # sim PRNG-fallback
        raise                                                     # fail-closed on hardware
    raw = bytes.fromhex(resp.data)
    start = int.from_bytes(raw[0:4], "big") % length
    hop = 0.45 + 0.30 * (int.from_bytes(raw[4:8], "big") / 2 ** 32)   # isotropic angle in [0.45,0.75)
    return start, round(hop, 4)


def _read_env_key(name: str) -> str | None:
    for envp in (os.path.join(_HERE, "..", ".env"), os.path.join(_HERE, ".env")):
        p = os.path.normpath(envp)
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if line.strip().startswith(f"{name}="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None


def dump_circuits(width: int, length: int, gens: int, thetas: list[float], *, modes: tuple[str, ...],
                  arms: tuple[str, ...]) -> None:
    for mode in modes:
        for arm in arms:
            pj.print_line_report(width, length, gens, thetas, mode=mode, arm=arm)


# ===========================================================================
# PJ2.4 -- MOTILE VIVARIUM driver path (2018-faithful life that moves).
# ===========================================================================
def _run_counts_simple(qc: QuantumCircuit, *, sim: bool, backend: Any, shots: int,
                       dd: str = "off", dd_ctx: dict[str, int] | None = None) -> dict[str, int]:
    """Run ONE motile circuit. On hardware with dd != 'off' and a dd_ctx (organisms/length/gens/
    rep_gen), pad germ-only DD (the PJ2.5 lever); else plain opt-3. Sim ignores DD (noiseless == id)."""
    if sim:
        return LINE_SIM.run(transpile(qc, LINE_SIM), shots=shots).result().get_counts()
    if dd != "off" and dd_ctx is not None:
        submit, _phys = schedule_motile_selective_dd(qc, backend, dd=dd, **dd_ctx)
    else:
        submit = generate_preset_pass_manager(optimization_level=3, backend=backend).run(qc)
    raw_meas, _jobs, _qs = run_sampler(backend, submit, shots)
    counts: dict[str, int] = {}
    for s in raw_meas:
        counts[s] = counts.get(s, 0) + 1
    return counts


def build_measured_motile(organisms: int, length: int, gens: int, thetas: list[float], *, arm: str,
                          start: int, hop: float, food: tuple[int, ...], rep_gen: int,
                          basis: str = "x",
                          pokes: list[tuple[int, int, float]] | None = None) -> QuantumCircuit:
    """One measured motile circuit at depth `gens`. basis='x' rotates the ACTIVE germ into X (the
    <X^W> witness setting); basis='z' leaves the germ in Z (for the ghz2 Z-sector). Body/vitality/
    energy are always read in Z."""
    qc = pj.build_motile_vivarium(organisms, length, gens, thetas, arm=arm, start=start, hop=hop,
                                  food=food, rep_gen=rep_gen, pokes=pokes)
    if basis == "x":
        for q in pj.motile_witness_qubits(organisms, length, gens, rep_gen):
            qc.h(q)
    n = qc.num_qubits
    creg = ClassicalRegister(n, "c")
    qc.add_register(creg)
    qc.measure(range(n), creg)
    return qc


def _zz_mean_from_counts(counts: dict[str, int], qubits: list[int]) -> float:
    """Mean <Z_i Z_j> over ADJACENT germ pairs from Z-basis counts (the ghz2 Z-sector correlation)."""
    if len(qubits) < 2:
        return 0.0
    total = sum(counts.values()) or 1
    acc = 0.0
    pairs = list(zip(qubits, qubits[1:]))
    for bits, c in counts.items():
        for a, b in pairs:
            sa = 1 - 2 * (bits[-(a + 1)] == "1")
            sb = 1 - 2 * (bits[-(b + 1)] == "1")
            acc += sa * sb * c
    return acc / (total * len(pairs))


def reduce_motile(cx: dict[str, int], cz: dict[str, int] | None, organisms: int, length: int, *,
                  gens: int, rep_gen: int, certify: str) -> dict[str, Any]:
    """Observables from the measured counts: per-individual body field + alive + energy, the germ
    witness (X-parity vs product null), and (ghz2) the Z-sector -> a real entanglement certificate."""
    total = sum(cx.values()) or 1
    active = pj.motile_witness_qubits(organisms, length, gens, rep_gen)
    joint, sep = q4.xbasis_witness_from_counts(cx, active)
    fields = [[round(_marginal_p1(cx, pj.mot_body_q(o, i, length), total), 4) for i in range(length)]
              for o in range(organisms)]
    alive = [round(_marginal_p1(cx, pj.mot_vit_q(o, length), total), 4) for o in range(organisms)]
    energy = [round(_marginal_p1(cx, pj.mot_energy_q(o, length), total), 4) for o in range(organisms)]
    born = pj.motile_n_born(gens, rep_gen, organisms)              # zero out not-yet-born individuals
    for o in range(born, organisms):                              # (their idle qubits are just noise)
        fields[o] = [0.0] * length
        alive[o] = 0.0
        energy[o] = 0.0
    n_alive = sum(1 for a in alive if a > 0.5)
    overlap = (sum(min(fields[0][i], fields[1][i]) for i in range(length)) if organisms > 1 else 0.0)
    zz = _zz_mean_from_counts(cz, active) if (certify == "ghz2" and cz is not None) else None
    return {"witness_joint": joint, "separable_null": sep, "fields": fields, "alive": alive,
            "energy": energy, "n_alive": n_alive, "overlap": round(float(overlap), 4), "zz": zz}


def depth_scan_motile(organisms: int, length: int, gens: int, thetas: list[float], *, arm: str,
                      start: int, hop: float, food: tuple[int, ...], rep_gen: int, certify: str,
                      sim: bool, backend: Any, shots: int, repeats: int,
                      pokes: list[tuple[int, int, float]] | None = None,
                      dd: str = DD_DEFAULT, dd_ab: bool = False) -> list[dict[str, Any]]:
    """The honest frames: for d in range(gens) build+measure the motile circuit(s), reduce to one
    certified frame carrying the moving fields AND the acting life (alive/energy/born) + witness.
    PJ2.5: runs through germ-only DD (mode `dd`); with `dd_ab` each frame is measured twice
    (DD-off then DD-on) and banks `witness_dd_off/on` (+ `zz_dd_off/on`) side by side (EM1 rule)."""
    sigma_shot = math.sqrt(1.0 / shots)
    frames: list[dict[str, Any]] = []
    for d in range(gens):
        qcx = build_measured_motile(organisms, length, d, thetas, arm=arm, start=start, hop=hop,
                                    food=food, rep_gen=rep_gen, basis="x", pokes=pokes)
        qcz = (build_measured_motile(organisms, length, d, thetas, arm=arm, start=start, hop=hop,
                                     food=food, rep_gen=rep_gen, basis="z", pokes=pokes)
               if certify == "ghz2" else None)
        dd_ctx = {"organisms": organisms, "length": length, "gens": d, "rep_gen": rep_gen}

        def one_pass(dd_mode: str) -> tuple[float, float, dict[str, Any]]:
            joints: list[float] = []
            reduced: dict[str, Any] = {}
            for _rep in range(max(1, repeats)):
                cx = _run_counts_simple(qcx, sim=sim, backend=backend, shots=shots,
                                        dd=dd_mode, dd_ctx=dd_ctx)
                cz = (_run_counts_simple(qcz, sim=sim, backend=backend, shots=shots,
                                         dd=dd_mode, dd_ctx=dd_ctx) if qcz else None)
                reduced = reduce_motile(cx, cz, organisms, length, gens=d, rep_gen=rep_gen,
                                        certify=certify)
                joints.append(reduced["witness_joint"])
            w = statistics.fmean(joints)
            spread = statistics.pstdev(joints) if len(joints) > 1 else 0.0
            return w, spread, reduced

        ab: dict[str, Any] = {}
        if dd_ab:
            on_mode = dd if dd != "off" else "x2"                  # can't A/B off-vs-off
            w_off, _s_off, red_off = one_pass("off")
            w_on, spread, reduced = one_pass(on_mode)              # headline = the mitigated pass
            w = w_on
            ab = {
                "witness_dd_off": round(float(w_off), 4),
                "witness_dd_on": round(float(w_on), 4),
                "zz_dd_off": (round(float(red_off["zz"]), 4) if red_off["zz"] is not None else None),
                "zz_dd_on": (round(float(reduced["zz"]), 4) if reduced["zz"] is not None else None),
            }
        else:
            w, spread, reduced = one_pass(dd)

        w_sigma = math.sqrt(spread ** 2 + sigma_shot ** 2)
        active_w = len(pj.motile_witness_qubits(organisms, length, d, rep_gen))
        zz = reduced["zz"]
        certified = None
        if zz is not None and active_w >= 2:
            val = w + zz                                           # Bell/GHZ two-sector sum
            certified = bool(val - 1.0 > K * w_sigma)             # separable bound: <XX>+<ZZ> <= 1
        frame = {
            "gen": d, "fields": reduced["fields"], "alive": reduced["alive"],
            "energy": reduced["energy"], "born": pj.motile_n_born(d, rep_gen, organisms),
            "w": round(float(w), 4), "w_sigma": round(float(w_sigma), 4),
            "sep": round(float(reduced["separable_null"]), 4), "overlap": reduced["overlap"],
            "zz": (round(float(zz), 4) if zz is not None else None),
            "certified": certified, "n": reduced["n_alive"],
            "survives": bool(w - reduced["separable_null"] > K * w_sigma),
        }
        frame.update(ab)
        frames.append(frame)
    return frames


def run_motile(args: Any, thetas: list[float], start: int, hop: float, sim: bool,
               pokes: list[tuple[int, int, float]] | None = None) -> None:
    """PJ2.4 flow: connect (if hardware), depth-scan each arm, bank the moving-life run JSON."""
    food = tuple(int(x) for x in args.food.split(",") if x.strip() != "")
    length = args.length
    arms = (args.arm,) if args.arm else ARMS
    pokes = pokes or []
    nq = pj.motile_segment_len(args.organisms, length, food)

    backend = None
    backend_name = "statevector_sim"
    if not sim:
        backend = connect(args.backend)
        backend_name = backend.name
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits); motile needs {nq}")
        gated_chain(backend, nq)
    elif nq > _SV_MAX_QUBITS:
        print(f"[PJ2.4 ABORT] {nq} qubits > sim cap {_SV_MAX_QUBITS} (shrink --length/--organisms).")
        raise SystemExit(1)

    poke_str = (" pokes=" + ",".join(f"g{g}@c{p}({a})" for g, p, a in pokes)) if pokes else ""
    dd_str = f"dd={args.dd}{'(A/B)' if args.dd_ab else ''}"
    print(f"=== PJ2.4 motile: org={args.organisms} L={length} gens={args.gens} arms={arms} "
          f"food={list(food)} rep_gen={args.rep_gen} certify={args.certify} start={start} hop={hop} "
          f"{dd_str}{poke_str} on {backend_name} ({nq} qubits) ===")

    # --- PJ2.5 DD targeting evidence (AC-3): germ-only, body/vitality/energy excluded ---
    germ_v = pj.motile_witness_qubits(args.organisms, length, args.gens - 1, args.rep_gen)
    body_v = [pj.mot_body_q(o, i, length) for o in range(args.organisms) for i in range(length)]
    vit_v = [pj.mot_vit_q(o, length) for o in range(args.organisms)]
    en_v = [pj.mot_energy_q(o, length) for o in range(args.organisms)]
    dd_physical: list[int] = []
    if args.dd != "off":
        print(f"  DD [{args.dd}={_dd_sequence(args.dd) and [g.name for g in _dd_sequence(args.dd)]}] "
              f"targets germ(witness) virtual={germ_v}; DD-FREE body={body_v} vit={vit_v} energy={en_v}")
        if not sim:                                               # physical map needs the real target
            rep_qc = build_measured_motile(args.organisms, length, args.gens - 1, thetas,
                                           arm=arms[0], start=start, hop=hop, food=food,
                                           rep_gen=args.rep_gen, basis="x", pokes=pokes)
            _sched, dd_physical = schedule_motile_selective_dd(
                rep_qc, backend, args.organisms, length, args.gens - 1, args.rep_gen, dd=args.dd)
            print(f"  DD germ physical qubits = {dd_physical}")
        else:
            dd_physical = germ_v                                  # sim: no layout; virtual set as evidence
    if args.dump_circuit:
        pj.print_motile_report(args.organisms, length, args.gens, thetas, arm=arms[0],
                               food=food, rep_gen=args.rep_gen)
        if args.draw_only:
            raise SystemExit(0)

    scenarios: dict[str, Any] = {"motile": {}}
    endpoint: dict[str, Any] = {}
    any_certified = False
    for arm in arms:
        frames = depth_scan_motile(args.organisms, length, args.gens, thetas, arm=arm, start=start,
                                   hop=hop, food=food, rep_gen=args.rep_gen, certify=args.certify,
                                   sim=sim, backend=backend, shots=args.shots, repeats=args.repeats,
                                   pokes=pokes, dd=args.dd, dd_ab=args.dd_ab)
        scenarios["motile"][arm] = frames
        last = frames[-1]
        endpoint[arm] = {"w": last["w"], "n_alive": last["n"], "certified": last["certified"],
                         "survives": last["survives"]}
        any_certified = any_certified or any(f["certified"] for f in frames)
        print(f"  {arm:9} witness[0..{args.gens - 1}]={[f['w'] for f in frames]}")
        print(f"  {arm:9} alive(count)/gen={[f['n'] for f in frames]}  born/gen={[f['born'] for f in frames]}")
        if args.certify == "ghz2":
            print(f"  {arm:9} zz/gen={[f['zz'] for f in frames]}  certified/gen={[f['certified'] for f in frames]}")
        if args.dd_ab:
            print(f"  {arm:9} DD-off w/gen={[f.get('witness_dd_off') for f in frames]}")
            print(f"  {arm:9} DD-on  w/gen={[f.get('witness_dd_on') for f in frames]}")

    # --- PJ2.5 A/B summary: mean witness delta + certified-gen delta (DD-on vs DD-off) ---
    dd_ab_summary: dict[str, Any] | None = None
    if args.dd_ab:
        deltas: list[float] = []
        cert_on = cert_off = 0
        for arm in arms:
            for f in scenarios["motile"][arm]:
                w_on, w_off = f.get("witness_dd_on"), f.get("witness_dd_off")
                if w_on is None or w_off is None:
                    continue
                deltas.append(w_on - w_off)
                zz_on, zz_off, sig = f.get("zz_dd_on"), f.get("zz_dd_off"), f["w_sigma"]
                if zz_on is not None and (w_on + zz_on) - 1.0 > K * sig:
                    cert_on += 1
                if zz_off is not None and (w_off + zz_off) - 1.0 > K * sig:
                    cert_off += 1
        dd_ab_summary = {
            "delta_witness": round(statistics.fmean(deltas), 4) if deltas else 0.0,
            "delta_certified_gens": cert_on - cert_off,
            "certified_gens_dd_on": cert_on, "certified_gens_dd_off": cert_off,
        }
        print(f"  A/B: delta_witness(on-off)={dd_ab_summary['delta_witness']}  "
              f"certified gens on={cert_on} off={cert_off} (delta={cert_on - cert_off})")

    result: dict[str, Any] = {
        "meta": {
            "stage": "PJ2.5", "model": "motile_vivarium", "backend": backend_name,
            "organisms": args.organisms, "length": length, "gens": args.gens, "food": list(food),
            "rep_gen": args.rep_gen, "arms": list(arms), "shots": args.shots, "sim": sim, "k": K,
            "hop": hop, "start": start, "age_step": pj.MOTILE_AGE, "certify": args.certify,
            "certified_entangled": (any_certified if args.certify == "ghz2" else None),
            "repeats": args.repeats, "certified_frames": True, "calibration": None,
            "dd": args.dd, "dd_ab": args.dd_ab, "dd_physical_qubits": dd_physical,
            "kept_fraction": 1.0,                                 # DD is suppression, not post-selection
            "pokes": [{"gen": g, "pos": p, "amp": round(a, 4)} for g, p, a in pokes],
        },
        "scenarios": scenarios, "endpoint": endpoint,
        "summary": {"dd_ab": dd_ab_summary},
    }
    os.makedirs(os.path.join(OUTPUT_DIR, "pj2_motile"), exist_ok=True)
    tag = timestamp() if not sim else "sim"
    out = os.path.join(OUTPUT_DIR, "pj2_motile",
                       f"{args.name}_org{args.organisms}L{length}_{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ2.2b 1D-line vivarium driver -- a walking occupancy field + germ witness; "
                    "banks the certified depth-scan frames (the 1D sibling of 2D_alive.py).")
    ap.add_argument("--backend", type=str, default=None,
                    help="hardware backend name; omit to run on the statevector Aer sim")
    ap.add_argument("--model", choices=("line", "motile"), default="line",
                    help="line = movement+witness only (PJ2.2b); motile = 2018-faithful life that moves "
                         "(PJ2.4: reproduction/selection/metabolism/death acting)")
    ap.add_argument("--certify", choices=("xonly", "ghz2"), default="xonly",
                    help="motile witness: xonly = single-basis <X^W> (fast, weak); ghz2 = add the "
                         "Z-sector for a real entanglement certificate")
    ap.add_argument("--organisms", type=int, default=2, help="motile: individuals (founder + daughter)")
    ap.add_argument("--food", type=str, default="1,3",
                    help="motile: comma-separated food-site cells; empty ('') = barren (starvation demo)")
    ap.add_argument("--rep-gen", dest="rep_gen", type=int, default=2,
                    help="motile: generation the fed founder buds the daughter")
    ap.add_argument("--length", type=int, default=LENGTH, help="chain length L (line cells)")
    ap.add_argument("--width", type=int, default=WIDTH, help="germ width W (the witness set)")
    ap.add_argument("--mode", choices=list(MODES), default=None,
                    help="run one mode; default = run all three (solo when --movement-only)")
    ap.add_argument("--arm", choices=list(ARMS), default='isolated',
                    help="run one arm; default = both")
    ap.add_argument("--gens", type=int, default=GENS, help="generations (depth scan 0..gens-1); "
                    "more = more movement + deeper (push until the witness finally falls)")
    ap.add_argument("--hop", type=float, default=None,
                    help="walk hop angle = movement per generation; overrides the QRNG value. "
                         "bigger = the field travels farther each step (default ~0.45-0.75 QRNG / 0.6)")
    ap.add_argument("--start", type=int, default=None,
                    help="force the seed cell (default: QRNG-drawn) -- e.g. 0 to start at one end")
    ap.add_argument("--repeats", type=int, default=REPEATS, help="repeats for sigma")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--dd", choices=list(DD_MODES), default=DD_DEFAULT,
                    help="PJ2.5 germ-selective dynamical decoupling (EM1): off = plain opt-3; "
                         "x2 = CPMG [X,X] (prior behaviour); xy4 = [X,Y,X,Y] (robust). DD pads the "
                         "idle germ/witness qubits only (Weismann barrier); kept_fraction stays 1.")
    ap.add_argument("--dd-ab", dest="dd_ab", action="store_true",
                    help="motile only: bank an A/B comparison per gen -- measure DD-off AND DD-on "
                         "(the --dd mode), recording witness_dd_off/on side by side (EM1 honesty rule)")
    ap.add_argument("--movement-only", dest="movement_only", action="store_true",
                    help="force mode=solo (the long-chain 'just the movement' run)")
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print the annotated line circuits then run")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="with --dump-circuit: draw and exit, do NOT run")
    ap.add_argument("--poke", action="append", default=None, metavar="SPEC",
                    help="sudden perturbation that SETS a cell's occupancy; REPEATABLE. Each SPEC is "
                         "'N', 'N:POS' or 'N:POS:AMP' (gen : cell : target 0..1). Repeat for pokes at "
                         "different gens; reuse the same gen for several spots set at once. "
                         "e.g. --poke 5:3:0.01 (set cell 3 to 1%% at gen 5)")
    ap.add_argument("--poke-position", dest="poke_position", type=int, default=None,
                    help="default cell for a bare '--poke N' (default: chain centre)")
    ap.add_argument("--poke-amp", dest="poke_amp", type=float, default=1.0,
                    help="default target 0..1 for pokes without :AMP (1.0 = set to 100%%; 0.01 = 1%%)")
    ap.add_argument("--name", type=str, default="pj2_line")
    args = ap.parse_args()
    sim = args.backend is None
    modes = ("solo",) if args.movement_only else ((args.mode,) if args.mode else MODES)
    arms = (args.arm,) if args.arm else ARMS

    # --- pokes (sudden perturbations): repeatable --poke N|N:POS|N:POS:AMP -----------------------
    default_pos = args.poke_position if args.poke_position is not None else args.length // 2
    pokes: list[tuple[int, int, float]] = []
    for spec in (args.poke or []):
        parts = spec.strip().split(":")
        g = int(parts[0])
        p = int(parts[1]) if len(parts) > 1 and parts[1] != "" else default_pos
        a = float(parts[2]) if len(parts) > 2 and parts[2] != "" else args.poke_amp
        if not 0 <= g <= args.gens:
            print(f"[PJ2.2b ABORT] --poke gen {g} out of range 0..{args.gens}"); raise SystemExit(1)
        pokes.append((g, max(0, min(args.length - 1, p)), max(0.0, min(1.0, a))))

    # --- certified entropy (fail-closed on hardware; sim may PRNG-fallback) ---
    client = None
    api_key = os.environ.get("QEAAS_API_KEY") or _read_env_key("QEAAS_API_KEY")
    qrng_url = os.environ.get("QEAAS_API_URL") or QEAAS_URL
    if api_key:
        client = QRNGClient(qrng_url, api_key)
        try:
            h = client.health()
            print(f"Q-EaaS  : {qrng_url}  health: {h.status}")
            if h.status != "ok" and not sim:
                print("[PJ2.2b ABORT] Q-EaaS not ok (fail-closed on hardware)."); raise SystemExit(1)
        except QRNGUnavailable as exc:
            if not sim:
                print(f"[PJ2.2b ABORT] Q-EaaS unavailable (fail-closed on hardware): {exc}")
                raise SystemExit(1)
            client = None
    elif not sim:
        print("[PJ2.2b ABORT] QEAAS_API_KEY not set (fail-closed on hardware)."); raise SystemExit(1)

    thetas = (qrng_thetas(client, args.width, MUT_SCALE, 0) if client is not None
              else q4._sim_thetas(args.width, args.width, mut_scale=MUT_SCALE))
    start, hop = qrng_environment(client, args.length, sim)
    if args.hop is not None:                                       # force the movement rate
        hop = args.hop
    if args.start is not None:                                     # force the seed cell
        start = args.start % args.length

    if args.model == "motile":                                     # PJ2.4 branch (2018-faithful life)
        run_motile(args, thetas, start, hop, sim, pokes)
        return

    if args.dump_circuit:
        dump_circuits(args.width, args.length, args.gens, thetas, modes=modes, arms=arms)
        if args.draw_only:
            raise SystemExit(0)

    backend = None
    backend_name = "statevector_sim"
    if not sim:
        backend = connect(args.backend)
        backend_name = backend.name
        nq = max(pj.line_segment_len(args.width, args.length, m) for m in modes)
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits); line needs {nq}")
        gated_chain(backend, nq)                       # chain-quality gate; aborts if bad
    else:
        nq = max(pj.line_segment_len(args.width, args.length, m) for m in modes)
        if nq > _SV_MAX_QUBITS:
            print(f"[PJ2.2b ABORT] {nq} qubits > sim cap {_SV_MAX_QUBITS} "
                  f"(long-chain replicate/duo are out of scope; use --movement-only).")
            raise SystemExit(1)

    poke_str = (" pokes=" + ",".join(f"g{g}@c{p}(a{a})" for g, p, a in pokes)) if pokes else ""
    print(f"=== PJ2.2b line: W={args.width} L={args.length} gens={args.gens} "
          f"modes={modes} arms={arms} start={start} hop={hop}{poke_str} on {backend_name} ===")

    scenarios: dict[str, Any] = {}
    endpoint: dict[str, Any] = {}
    for mode in modes:
        scenarios[mode] = {}
        endpoint[mode] = {}
        for arm in arms:
            frames = depth_scan(args.width, args.length, args.gens, thetas, mode=mode, arm=arm,
                                start=start, hop=hop, sim=sim, backend=backend, shots=args.shots,
                                repeats=args.repeats, pokes=pokes, dd=args.dd)
            scenarios[mode][arm] = frames
            last = frames[-1]
            endpoint[mode][arm] = {"w": last["w"], "survives": last["survives"]}
            depth = q4.entanglement_depth([f["w"] for f in frames], [f["sep"] for f in frames],
                                          [f["w_sigma"] for f in frames], k=K)
            print(f"  {mode:10} {arm:9} witness[0..{args.gens - 1}]="
                  f"{[f['w'] for f in frames]}  collapse@gen>{depth}  "
                  f"{'SURVIVES' if last['survives'] else 'at-null'}")

    result: dict[str, Any] = {
        "meta": {
            "stage": "PJ2.2b", "model": "line_vivarium", "backend": backend_name,
            "length": args.length, "width": args.width, "gens": args.gens,
            "modes": list(modes), "arms": list(arms), "shots": args.shots, "sim": sim,
            "k": K, "hop": hop, "start": start, "mut_scale": MUT_SCALE,
            "dd": args.dd, "kept_fraction": 1.0, "repeats": args.repeats,
            "certified_frames": True, "calibration": None,
            "pokes": [{"gen": g, "pos": p, "amp": round(a, 4)} for g, p, a in pokes],
        },
        "scenarios": scenarios,
        "endpoint": endpoint,
    }

    os.makedirs(os.path.join(OUTPUT_DIR, "pj2_line"), exist_ok=True)
    tag = timestamp() if not sim else "sim"
    out = os.path.join(OUTPUT_DIR, "pj2_line", f"{args.name}_L{args.length}_"
                       f"{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
