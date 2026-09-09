#!/usr/bin/env python3
"""Critical Quantum Life — F8: tiered Sandpile presets + the manual hardware batch harness.

The three LEAP budget tiers (LEAP-candidates-ranked.md section 10.7) as named presets, plus the
sim-first go/no-go gate and the manual QC emission pipeline (reusing F5's chain picker +
calibration gate from hardware_batches.py). It writes NO new physics -- it composes sandpile.py's
dynamic-circuit builder, sandpile_analysis.py's DP analysis, and F5's layout/calibration/QPY
plumbing.

Budgets are counted in SHOTS, not in wall-clock or QPU-seconds. A tier's cost is just its circuit
count x shots/circuit (x ZNE factors when on); the run log spends against a shot budget, and QC
queue/allocation time is the user's concern at submit time, not something this file estimates.
  verify  6 circuits x ~4000 shots  first-indication pass: does the mechanism run + does closed
                       differ from yoked? (submit the 10min tier's 6 circuits at reduced shots)
  10min  go/no-go     one width, T-sweep, closed + matched yoked; existence + the decisive contrast.
  30min  decisive     one large width, long T, closed vs yoked + avalanche/sigma/witness at the
                       self-organized point; the letter-grade headline.
  180min full paper    3 widths for finite-size scaling, T-sweep, closed/yoked/(classical
                       surrogate), grain/relaxation robustness sweep, >=5 seeds, error mitigation
                       (TREX readout + ZNE); the DP-universality (PRL-grade) claim.

MANUAL SUBMISSION BOUNDARY (epic section 3 -- LAW). `emit` writes transpiled QPY circuits + a submit
bundle and STOPS; it NEVER auto-submits. The ONLY unattended run path is `signcheck` (the Aer
dynamic-sim go/no-go), which is MANDATORY before any hardware artifact is emitted (AC-F8.7).

Run:
    cd THESIS/CriticalQuantumLife/code
    python sandpile_batches.py signcheck --tier 10min                 # Aer go/no-go (free)
    python sandpile_batches.py emit --tier 10min --backend ibm_kingston   # QPY + bundle, then STOP
    python sandpile_batches.py ingest --bundle ../research_runs/sandpile_10min_..._submit.json \\
        --memory <circ0_memory.json> <circ1_memory.json> ...          # counts/memory -> run-JSON
    python sandpile_batches.py analyze --tier 10min --name sandpile_10min   # DP report
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

import closed_loop as cl                          # OUTPUT_DIR (reused)
import sandpile as sp                             # F8 dynamic-circuit builder + runner
import sandpile_analysis as spa                   # F8 DP analysis
import hardware_batches as hb                     # F5 connect + gated_chain_with_stats (reused)

from qiskit import qpy
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# ---- the budget tiers (LEAP section 10.7) -----------------------------------
# Budgets are in SHOTS. The `verify` tier is the cheap first-indication pass (Run log 1): the same 6
# W=14 circuits as `10min` but at 4000 shots each == 24k shots, to confirm the mechanism runs and
# closed differs from yoked, before spending the full-shot statistical passes.
TIERS: dict[str, dict[str, Any]] = {
    "verify": {
        "widths": [14], "steps": [40, 60, 80], "seeds": 1, "shots": 4000,
        "arms": ["closed", "yoked"], "witness": False, "surrogate": False,
        "error_mitigation": None,
        "claim": "first-indication pass: the dynamic circuit transpiles + runs on hardware and the "
                 "closed arm parks at a different density than the yoked control (no statistics).",
    },
    "10min": {
        "widths": [14], "steps": [40, 60, 80], "seeds": 1, "shots": 8192,
        "arms": ["closed", "yoked"], "witness": False, "surrogate": False,
        "error_mitigation": None,
        "claim": "activity self-organizes to a nonzero steady density; the yoked control does not "
                 "(existence + the decisive contrast).",
    },
    "30min": {
        "widths": [24], "steps": [120], "seeds": 3, "shots": 8192,
        "arms": ["closed", "yoked"], "witness": True, "surrogate": True,
        "both_sides": True, "error_mitigation": None,
        "claim": "at a fixed size the processor self-organizes to criticality (sigma->1, avalanche "
                 "alpha~1.5) ONLY under drive-when-quiet, and the state is certified quantum "
                 "(cluster witness > null).",
    },
    "180min": {
        "widths": [12, 20, 30], "steps": [60, 100, 140], "seeds": 5, "shots": 8192,
        "arms": ["closed", "yoked"], "witness": True, "surrogate": True,
        "both_sides": True, "error_mitigation": ["trex", "zne"],
        "robustness": {"grain_size": [1, 2], "relax_p": [0.25, 0.45], "width": 20, "steps": 100},
        "claim": "the self-organized critical point is in the directed-percolation universality "
                 "class (alpha, z=1.58, beta via finite-size scaling), reached without fine-tuning, "
                 "certified quantum, robust to grain/relaxation, and beats both classical controls.",
    },
}
WITNESS_CLUSTER_FRAC = 0.5    # cluster witness spans the central half of the chain (Q2 sub-block)
ZNE_FACTORS = 3               # noise factors for ZNE (each triples that circuit's executions)
SIGNCHECK_MAX_W = 8           # cap the Aer go/no-go width: laptop-cheap statevector dynamic sim
SIGNCHECK_MAX_T = 40          # cap the Aer go/no-go steps (the sim gate, NOT the hardware circuits)


# ---------------------------------------------------------------------------
# Circuit list + budget arithmetic (drives the run logs)
# ---------------------------------------------------------------------------
def circuit_specs(tier: str) -> list[dict[str, Any]]:
    """The (arm, width, steps, seed) trajectory circuits + witness circuits a tier emits. Yoked
    shares the closed circuit's (width, steps, seed) so its matched drive_rate is well-defined."""
    cfg = TIERS[tier]
    specs: list[dict[str, Any]] = []
    for w in cfg["widths"]:
        for T in cfg["steps"]:
            for s in range(cfg["seeds"]):
                seed = 100 + s
                for arm in cfg["arms"]:
                    # both-basins: the closed arm also runs the hot (chaotic-side) start so the
                    # cold/hot convergence test can prove the set-point is a self-organized attractor.
                    inits = (["cold", "hot"] if arm == "closed" and cfg.get("both_sides") else ["cold"])
                    for init in inits:
                        specs.append({"kind": "trajectory", "arm": arm, "width": w,
                                      "steps": T, "seed": seed, "init": init})
        if cfg["witness"]:
            for s in range(cfg["seeds"]):
                specs.append({"kind": "witness", "arm": "closed", "width": w,
                              "steps": max(cfg["steps"]), "seed": 100 + s})
    for rob in _robustness_specs(cfg):
        specs.append(rob)
    return specs


def _robustness_specs(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """The 180-min grain-size x relaxation-strength robustness sweep (plan section 5)."""
    rob = cfg.get("robustness")
    if not rob:
        return []
    out: list[dict[str, Any]] = []
    for g in rob["grain_size"]:
        for p in rob["relax_p"]:
            for s in range(cfg["seeds"]):
                out.append({"kind": "trajectory", "arm": "closed", "width": rob["width"],
                            "steps": rob["steps"], "seed": 100 + s,
                            "grain_size": g, "relax_p": p})
    return out


def budget_estimate(tier: str, shots: int | None = None) -> dict[str, Any]:
    """Shot budget for a tier: circuit count x shots/circuit (x ZNE factors when on). No time
    arithmetic -- the cost is counted in shots and the run log spends against a shot budget.
    `shots` overrides the tier default."""
    cfg = TIERS[tier]
    specs = circuit_specs(tier)
    shots = shots if shots is not None else cfg["shots"]
    zne = ZNE_FACTORS if (cfg.get("error_mitigation") and "zne" in cfg["error_mitigation"]) else 1
    n_circuits = len(specs)
    executions = n_circuits * zne
    total_shots = executions * shots
    return {
        "tier": tier, "n_circuits": n_circuits, "zne_factor": zne,
        "executions": executions, "shots_per_circuit": shots, "total_shots": total_shots,
    }


def _cluster(width: int) -> list[int]:
    """Central contiguous sub-block for the cluster witness (Q2): the full-chain product died at
    W=32, so certify over the central half."""
    k = max(2, int(round(width * WITNESS_CLUSTER_FRAC)))
    start = (width - k) // 2
    return list(range(start, start + k))


# ---------------------------------------------------------------------------
# signcheck (AC-F8.7) — the Aer dynamic-sim go/no-go, MANDATORY before hardware
# ---------------------------------------------------------------------------
def signcheck(tier: str, name: str, shots: int | None = None,
              width: int | None = None, steps: int | None = None) -> dict[str, Any]:
    """Run a SMALL smoke config (default W=8, short T, seed 100) closed + matched yoked on Aer's
    dynamic simulator and check the decisive contrast: does closed self-park at nonzero density
    while yoked does not? This is the internal kill-gate before any Heron time (epic section 3,
    sim-first; mirrors the F1 discipline).

    The gate runs at a laptop-cheap width, NOT the tier's hardware width: self-organization is a
    width-independent property (the W=8 smoke already parks nonzero), and a statevector dynamic sim
    at W>=12 is too heavy for a workstation. `width`/`steps` override the smoke size; they only size
    the sim check, never the emitted hardware circuits."""
    cfg = TIERS[tier]
    width = width or min(SIGNCHECK_MAX_W, cfg["widths"][0])   # laptop-cheap; hardware uses cfg width
    steps = steps or min(SIGNCHECK_MAX_T, cfg["steps"][len(cfg["steps"]) // 2])
    shots = shots or min(2048, cfg["shots"])          # cheap on sim; hardware carries the real shots
    print(f"=== F8 Sandpile signcheck [{tier}] on Aer (smoke W={width} steps={steps} shots={shots}; "
          f"hardware width={cfg['widths'][0]}) ===")
    print(f"    hardware budget: {_budget_line(budget_estimate(tier))}")

    closed = sp.run_trajectory(width, steps, "closed", None, 100, shots, init="cold")
    rate = sp.measured_drive_rate(closed)
    yoked = sp.run_trajectory(width, steps, "yoked", None, 100, shots, drive_rate=rate)
    hot = sp.run_trajectory(width, steps, "closed", None, 100, shots, init="hot")
    for r in (closed, yoked, hot):
        sp.write_run(r, f"{name}_signcheck")

    contrast = spa.compare_closed_vs_yoked(closed, yoked)
    spa._print_contrast(contrast)
    conv = spa.convergence(closed, hot)                # both-basins SOC attractor test
    print(f"\n  both-basins: cold rho={conv['cold']['density']} ({conv['cold']['transient']}) "
          f"vs hot rho={conv['hot']['density']} ({conv['hot']['transient']})  "
          f"converged={conv['converged']}  "
          f"(self-organized set-point is an attractor reached from BOTH sides)")

    go = contrast["self_organized"] and conv["converged"]
    print(f"\n  SIGN-CHECK [{tier}]: {'GO (self-organizes + both-basins converge on sim; safe to emit HW)' if go else 'NO-GO (fix before QC)'}")
    report = {"tier": tier, "width": width, "steps": steps, "shots": shots,
              "budget": budget_estimate(tier), "contrast": contrast,
              "convergence": conv, "go": bool(go)}

    if cfg["witness"]:                                # AC-F8.5 cluster-witness certification (Aer)
        cluster = _cluster(width)
        joint, sep = sp.witness_trajectory(width, steps, 100, cluster, None, shots)
        cert = spa.certify_steady_state(joint, sep, shots, cluster)
        report["certification"] = cert
        print(f"  cluster witness <X^{{{len(cluster)}}}>={cert['witness_signal']:+.3f} "
              f"vs null +/-{cert['null_band']:.3f}  margin={cert['margin']:+.3f}  "
              f"certified={cert['certified']}  (AC-F8.5, certification layer not headline)")
    path = spa.write_report(report, f"{name}_signcheck_{tier}")
    print(f"  -> {path}")
    return report


# ---------------------------------------------------------------------------
# emit (AC-F8.7) — transpile the tier's dynamic circuits, dump QPY + bundle, STOP
# ---------------------------------------------------------------------------
def emit(tier: str, backend_name: str, name: str, args: argparse.Namespace) -> str:
    """Emit every circuit the tier needs (trajectory closed/yoked + optional witness), transpiled
    to a gated low-error chain, as QPY + a submit bundle. Prints the manual-submit steps and STOPS.
    The mandatory Aer signcheck must pass first (epic section 3)."""
    if hb.connect is None:
        print("[ABORT] pipeline_common.connect unavailable (no IBM plumbing on path)")
        raise SystemExit(1)
    try:
        backend = hb.connect(backend_name)
    except Exception as exc:                          # noqa: BLE001 - manual tool: fail clean
        print(f"[ABORT] could not connect to backend {backend_name!r}: {exc}")
        raise SystemExit(1)

    cfg = TIERS[tier]
    shots = getattr(args, "shots", None) or cfg["shots"]   # verify pass overrides (--shots 4000)
    specs = circuit_specs(tier)
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)

    # one chain per width (all circuits of a width share the qubit count); calibration recorded once
    chains: dict[int, tuple[list[int], dict[str, Any]]] = {}
    entries: list[dict[str, Any]] = []
    for spec in specs:
        w = spec["width"]
        if w not in chains:
            chains[w] = hb.gated_chain_with_stats(backend, w, args)
        chain, calibration = chains[w]
        qc, drive_rate = _build_spec_circuit(spec)
        pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                          initial_layout=chain if len(chain) == qc.num_qubits else None)
        isa = pm.run(qc)
        cname = _circuit_name(name, tier, spec)
        with open(os.path.join(cl.OUTPUT_DIR, cname), "wb") as fh:
            qpy.dump([isa], fh)
        entries.append({**spec, "circuit": cname, "width": w, "chain": chain,
                        "drive_rate": drive_rate, "cluster": _cluster(w) if spec["kind"] == "witness" else None})

    bundle = {
        "study": "quantum-sandpile", "tier": tier, "backend": backend_name,
        "shots": shots, "needs_memory": True,                 # per-shot memory needed for A(t)
        "error_mitigation": cfg.get("error_mitigation"),
        "budget": budget_estimate(tier, shots),
        "calibration_by_width": {str(w): chains[w][1] for w in chains},   # AC-F8.7 live 2q/readout
        "circuits": entries,
        "claim": cfg["claim"],
    }
    bpath = os.path.join(cl.OUTPUT_DIR, f"{name}_{tier}_{backend_name}_submit.json")
    with open(bpath, "w") as fh:
        json.dump(bundle, fh, indent=2, default=str)

    b = budget_estimate(tier, shots)
    print(f"[emit] tier={tier} backend={backend_name}: {len(entries)} circuits transpiled + bundle")
    for w, (chain, cal) in chains.items():
        print(f"       W={w} chain={chain}  cal(twoq_max={cal['twoq_err_max']:.4f} "
              f"readout_max={cal['readout_max']:.4f} gated={cal['gated']})")
    print(f"       {_budget_line(b)}")
    print(f"  -> {bpath}")
    print("  MANUAL: submit each QPY on QC by hand WITH per-shot memory, save memory JSONs, then:")
    print(f"    python sandpile_batches.py ingest --bundle {os.path.basename(bpath)} "
          f"--memory <circ0.json> <circ1.json> ...")
    return bpath


def _build_spec_circuit(spec: dict[str, Any]):
    """Build one circuit for a bundle spec, honouring per-spec grain_size / relax_p overrides
    (the robustness sweep) by temporarily setting the sandpile module constants."""
    old_g, old_p = sp.GRAIN_SIZE, sp.RELAX_P
    sp.GRAIN_SIZE = int(spec.get("grain_size", sp.GRAIN_SIZE))
    sp.RELAX_P = float(spec.get("relax_p", sp.RELAX_P))
    try:
        if spec["kind"] == "witness":
            qc = sp.build_cluster_witness(spec["width"], spec["steps"], spec["seed"],
                                          _cluster(spec["width"]))
            return qc, None
        drive_rate = None
        if spec["arm"] == "yoked":                    # match the closed loop's realised drive rate
            closed = sp.run_trajectory(spec["width"], spec["steps"], "closed", None,
                                       spec["seed"], min(1024, 2048))
            drive_rate = sp.measured_drive_rate(closed)
        qc, _sites = sp.build_trajectory(spec["width"], spec["steps"], spec["arm"], spec["seed"],
                                         drive_rate, spec.get("init", "cold"))
        return qc, drive_rate
    finally:
        sp.GRAIN_SIZE, sp.RELAX_P = old_g, old_p


def _circuit_name(name: str, tier: str, spec: dict[str, Any]) -> str:
    tag = f"W{spec['width']}_T{spec['steps']}_s{spec['seed']}"
    if spec["kind"] == "witness":
        return f"{name}_{tier}_witness_{tag}.qpy"
    extra = ""
    if "grain_size" in spec:
        extra = f"_g{spec['grain_size']}_p{spec['relax_p']}"
    return f"{name}_{tier}_{spec['arm']}_{spec.get('init', 'cold')}_{tag}{extra}.qpy"


# ---------------------------------------------------------------------------
# ingest — user-submitted per-shot memory -> sandpile run-JSON (via sandpile.assemble_run)
# ---------------------------------------------------------------------------
def _load_memory(path: str) -> list[str]:
    """Accept a raw list of per-shot bitstrings, or an object with a 'memory' key."""
    with open(path) as fh:
        obj = json.load(fh)
    if isinstance(obj, dict) and "memory" in obj:
        obj = obj["memory"]
    return [str(x) for x in obj]


def ingest(bundle_path: str, memory_paths: list[str], name: str) -> list[str]:
    """Map each submitted per-shot memory file back onto its trajectory bundle entry and build a
    sandpile run-JSON via sandpile.assemble_run. Witness circuits are skipped here (their parity is
    read by analyze). Returns the written run-JSON paths."""
    with open(bundle_path) as fh:
        bundle = json.load(fh)
    traj_entries = [e for e in bundle["circuits"] if e["kind"] == "trajectory"]
    if len(memory_paths) != len(traj_entries):
        print(f"[ABORT] {len(memory_paths)} memory files for {len(traj_entries)} trajectory circuits")
        raise SystemExit(1)
    written: list[str] = []
    for entry, mpath in zip(traj_entries, memory_paths):
        memory = _load_memory(mpath)
        run = sp.assemble_run(memory, entry["width"], entry["steps"], entry["arm"], entry["seed"],
                              int(bundle["shots"]), sp._drive_sites(entry["width"], entry["steps"],
                              entry["seed"]), entry.get("drive_rate"), entry.get("chain"),
                              bundle["calibration_by_width"].get(str(entry["width"])),
                              bundle["backend"], entry.get("init", "cold"))
        written.append(sp.write_run(run, f"{name}_{bundle['tier']}"))
    print(f"[ingest] {len(written)} sandpile run-JSONs from hardware memory")
    for w in written:
        print(f"  -> {w}")
    return written


# ---------------------------------------------------------------------------
# analyze — assemble the tier's DP report from its run-JSONs
# ---------------------------------------------------------------------------
def analyze(tier: str, name: str) -> str:
    """Pair the tier's closed/yoked run-JSONs by (width, steps, seed) and assemble the DP report:
    the closed-vs-yoked contrast per config, and (180-min) finite-size scaling across widths."""
    pattern = os.path.join(cl.OUTPUT_DIR, f"{name}_{tier}_*_run.json")
    runs = [spa.load_run(p) for p in sorted(glob.glob(pattern))]
    by_key: dict[tuple, dict[tuple, dict[str, Any]]] = {}
    for r in runs:
        m = r["meta"]
        key = (m["width"], m["steps"], m["seed"])
        by_key.setdefault(key, {})[(m["arm"], m.get("init", "cold"))] = r
    contrasts = []
    closed_by_width: dict[int, dict[str, Any]] = {}
    for key, arms in sorted(by_key.items()):
        closed_cold = arms.get(("closed", "cold"))
        yoked_cold = arms.get(("yoked", "cold"))
        closed_hot = arms.get(("closed", "hot"))
        if closed_cold is not None:
            closed_by_width[key[0]] = closed_cold        # last seed wins for the FSS table
        if closed_cold is not None and yoked_cold is not None:
            entry: dict[str, Any] = {
                "config": {"width": key[0], "steps": key[1], "seed": key[2]},
                "contrast": spa.compare_closed_vs_yoked(closed_cold, yoked_cold),
            }
            if closed_hot is not None:                   # both-basins convergence for this config
                entry["convergence"] = spa.convergence(closed_cold, closed_hot)
            contrasts.append(entry)
    report: dict[str, Any] = {"tier": tier, "n_configs": len(contrasts), "contrasts": contrasts}
    if len(TIERS[tier]["widths"]) >= 3 and len(closed_by_width) >= 3:
        report["finite_size_scaling"] = spa.finite_size_scaling(closed_by_width)
    path = spa.write_report(report, f"{name}_{tier}")
    print(f"[analyze] tier={tier}: {len(contrasts)} closed-vs-yoked config(s)")
    for c in contrasts:
        cfg = c["config"]
        so = c["contrast"]["self_organized"]
        conv = c.get("convergence", {}).get("converged")
        print(f"  W{cfg['width']} T{cfg['steps']} s{cfg['seed']}: self_organized={so}"
              f"{'' if conv is None else f'  both_basins_converged={conv}'}")
    print(f"  -> {path}")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _budget_line(b: dict[str, Any]) -> str:
    zne = f" x {b['zne_factor']} (ZNE)" if b["zne_factor"] > 1 else ""
    return (f"{b['n_circuits']} circuits x {b['shots_per_circuit']} shots{zne} = "
            f"{b['total_shots']:,} shots total")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F8 — tiered Sandpile presets + hardware harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("budget", help="print the shot budget arithmetic for a tier")
    pb.add_argument("--tier", choices=list(TIERS), default="10min")
    pb.add_argument("--shots", type=int, default=None, help="override shots/circuit")

    ps = sub.add_parser("signcheck", help="Aer dynamic-sim go/no-go (MANDATORY before hardware)")
    ps.add_argument("--tier", choices=list(TIERS), default="10min")
    ps.add_argument("--name", type=str, default="sandpile")
    ps.add_argument("--shots", type=int, default=None)
    ps.add_argument("--width", type=int, default=None,
                    help=f"smoke-sim width (default min({SIGNCHECK_MAX_W}, tier width); shrink if the "
                         f"sim is too heavy for your machine)")
    ps.add_argument("--steps", type=int, default=None, help="smoke-sim steps override")

    pe = sub.add_parser("emit", help="transpile the tier's dynamic circuits + submit bundle, STOP")
    pe.add_argument("--tier", choices=list(TIERS), default="10min")
    pe.add_argument("--backend", type=str, required=True, help="pinned Heron device")
    pe.add_argument("--name", type=str, default="sandpile")
    pe.add_argument("--shots", type=int, default=None,
                    help="override shots/circuit for the bundle")
    pe.add_argument("--max-twoq-err", dest="max_twoq_err", type=float, default=hb.MAX_TWOQ_ERR)
    pe.add_argument("--max-readout-err", dest="max_readout_err", type=float, default=hb.MAX_READOUT_ERR)
    pe.add_argument("--allow-bad-chain", dest="allow_bad_chain", action="store_true")

    pi = sub.add_parser("ingest", help="per-shot memory JSONs -> sandpile run-JSONs")
    pi.add_argument("--bundle", type=str, required=True)
    pi.add_argument("--memory", type=str, nargs="+", required=True, help="per-circuit memory JSONs")
    pi.add_argument("--name", type=str, default="sandpile")

    pa = sub.add_parser("analyze", help="assemble the tier's DP report from its run-JSONs")
    pa.add_argument("--tier", choices=list(TIERS), default="10min")
    pa.add_argument("--name", type=str, default="sandpile")

    args = ap.parse_args()
    if args.cmd == "budget":
        print(_budget_line(budget_estimate(args.tier, args.shots)))
    elif args.cmd == "signcheck":
        signcheck(args.tier, args.name, args.shots, args.width, args.steps)
    elif args.cmd == "emit":
        emit(args.tier, args.backend, args.name, args)
    elif args.cmd == "ingest":
        ingest(args.bundle, args.memory, args.name)
    elif args.cmd == "analyze":
        analyze(args.tier, args.name)


if __name__ == "__main__":
    main()
