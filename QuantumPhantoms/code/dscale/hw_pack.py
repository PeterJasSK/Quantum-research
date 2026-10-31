"""D-SCALE hardware pack builder (AC-19). Builds files for Peter; it never submits anything.

    python -m dscale.hw_pack --budget 40|100|120 --backend <ibm_name> [--from-map survival_map.json]
                             [--run research_runs/<run>] [--full]

Writes <run>/dscale/hwpack-<budget>-<backend>/ (default run: research_runs/_dscale):
  manifest.json   backend + the fake stand-in used for the ISA, families, regions, circuits, shots per circuit
                  (repeats x (k / w)^2, capped at 4000 x 15 unless --full), estimated QPU seconds
                  (shots x (circuit duration + 250 us)), mitigation (DD X-X on certified idles, readout twirling +
                  TREX, gate twirling; ZNE / PEA / PEC listed as runtime options only), and the calibration-gate
                  thresholds to re-check at submit time;
  circuits/*.qasm OpenQASM 3, transpiled to the matching fake target as a stand-in ISA (re-transpile against the
                  live backend before submitting: RUNBOOK_DSCALE.md part B).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from qiskit import qasm3

from dscale import allocate as A, budget as B, families as F, lint as L, pauli_noise as PN, targets as T

ROOT = Path(__file__).resolve().parents[2]
STAND_IN = {"ibm_marrakesh": "marrakesh", "ibm_kingston": "kingston", "ibm_fez": "marrakesh",
            "ibm_boston": "boston", "ibm_pittsburgh": "boston", "ibm_aachen": "boston",
            "ibm_phoenix": "nighthawk", "ibm_berlin": "nighthawk"}
PER_SHOT_OVERHEAD_S = 250e-6
DEFAULT_MARGIN = {"ghz-spine": 0.15, "ch-qca": 0.05, "pmd-bank": 0.05, "kicked-ising": 0.1}
K = 3                                                   # k = 3 reported (shots sized for the stricter verdict)
MITIGATION = {
    "dynamical_decoupling": {"enable": True, "sequence_type": "XX", "scope": "certified (spine) idle windows"},
    "twirling": {"enable_measure": True, "enable_gates": True, "strategy": "active-accum"},
    "readout": "TREX (measure twirling) + dscale.witness_scale.trex_lite on parities; no M3 (not installed)",
    "runtime_options_only": ["ZNE", "PEA", "PEC"],
}


def shots_for(margin: float, full: bool) -> tuple[int, bool]:
    """Shots per circuit per repeat so that k sigma < w with sigma = 1 / sqrt(shots); the pack runs `repeats` of them
    (total repeats x (k / w)^2). Capped at 4000 unless --full; returns (shots, capped)."""
    need = math.ceil((K / max(margin, 1e-3)) ** 2)
    if full:
        return need, False
    return min(need, B.SHOTS), need > B.SHOTS


def margins_from_map(path: Path) -> dict[str, dict]:
    """Per family: the alive cell with the most qubits (Goldilocks cells first) and its witness margin."""
    m = json.loads(path.read_text())
    out = {}
    for i, c in enumerate(m["cells"]):
        if not c.get("alive"):
            continue
        thr = 0.5 if c["family"] == "ghz-spine" else (c.get("random_band") or 0.0)
        key = (i in m["goldilocks_zone"], c["n_qubits"])
        if c["family"] not in out or key > out[c["family"]]["_key"]:
            out[c["family"]] = {"_key": key, "margin": abs(c["value"] - thr), "cell": c}
    return out


def isa_seconds(isa, tg: T.Target) -> float:
    if tg.backend is None:
        return float("nan")
    try:
        return float(isa.estimate_duration(tg.backend.target, unit="s"))
    except Exception:                                   # unscheduled / unsupported: depth x median 2q time
        return isa.depth() * tg.durations["2q"] + tg.durations["meas"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget", type=int, default=40, choices=F.BUDGETS)
    ap.add_argument("--backend", required=True, help="IBM backend name, e.g. ibm_boston")
    ap.add_argument("--from-map", type=Path, help="survival_map.json: size shots from the alive cells' margins")
    ap.add_argument("--run", default=None, help="run dir (default research_runs/_dscale)")
    ap.add_argument("--recipe", default="composite")
    B.add_args(ap, smoke=False)
    a = ap.parse_args()
    B.check(a)
    if a.backend not in STAND_IN:
        raise SystemExit(f"no fake stand-in for {a.backend}; known: {', '.join(STAND_IN)}")
    tname = STAND_IN[a.backend]
    tg = T.get(tname)
    run_dir = (ROOT / a.run) if a.run and not Path(a.run).is_absolute() else Path(a.run or ROOT / "research_runs" / "_dscale")
    out = run_dir / ("dscale" if a.run else "") / f"hwpack-{a.budget}-{a.backend}"
    (out / "circuits").mkdir(parents=True, exist_ok=True)
    margins = margins_from_map(a.from_map) if a.from_map else {}
    alloc = A.composite(a.budget, tname, a.recipe)
    draw = F.default_draw()
    fams = sorted({r["family"] for r in alloc["regions"].values() if r["family"] != "-"})
    entries, total_s = [], 0.0
    for f in fams:
        mod = F.get(f)
        if f == "ch-qca":
            job = mod.build(alloc, mod.PRESETS[a.budget], draw, tg)
        elif f == "ghz-spine":
            job = mod.build(alloc, {}, draw)
        else:
            job = mod.build(alloc, mod.PRESETS[a.budget], draw)
        L.enforce(job, alloc["regions"], f, tg.graph)
        mg = margins.get(f, {}).get("margin", DEFAULT_MARGIN[f])
        shots, capped = shots_for(mg, a.full)
        for k, c in enumerate(job):
            isa = PN.isa(c, tname, 1, dd_qubits=c.metadata.get("dd_qubits"))
            fn = f"{f}_{k:02d}.qasm"
            (out / "circuits" / fn).write_text(qasm3.dumps(isa))
            dur = isa_seconds(isa, tg)
            qpu = shots * a.repeats * (dur + PER_SHOT_OVERHEAD_S)
            total_s += qpu
            entries.append({"file": f"circuits/{fn}", "family": f, "name": c.name, "basis": c.metadata.get("basis"),
                            "physical_qubits": c.metadata["layout"], "isa_cz": int(isa.count_ops().get("cz", 0)),
                            "isa_depth": int(isa.depth()), "duration_s": dur, "shots": shots, "repeats": a.repeats,
                            "qpu_s_estimate": qpu, "sha256": F.circuit_hash(isa)})
        print(f"  {f:12s} {len(job):3d} circuits, margin w={mg:.3f} -> shots {shots} x {a.repeats} repeats"
              + (" (capped: the k=3 target needs more; use --full)" if capped else ""))
    used = sorted({q for r in alloc["regions"].values() if r["role"] != "buffer" for q in r["qubits"]})
    manifest = {
        "backend": a.backend, "isa_stand_in": T.FAKES[tname], "budget": a.budget, "recipe": a.recipe,
        "families": fams, "regions": {k: {kk: v[kk] for kk in ("family", "role", "qubits")}
                                      for k, v in alloc["regions"].items()},
        "circuits": entries, "n_circuits": len(entries),
        "estimated_qpu_seconds": round(total_s, 1), "estimated_qpu_minutes": round(total_s / 60, 2),
        "shot_rule": f"repeats x (k / w)^2 with k = {K}; capped at {B.SHOTS} shots x {B.REPEATS} repeats unless --full",
        "mitigation": MITIGATION,
        "calibration_gate": {"prune": A.PRUNE, "min_region_distance": alloc["min_region_distance"],
                             "allocated_qubits": used,
                             "recheck": "at submit time: drop the pack if any allocated qubit has readout > 0.06 or "
                                        "sx >= 0.5, or any allocated coupler has 2q error > 0.02; re-allocate instead",
                             "stand_in_calibration": tg.calibration},
        "from_map": str(a.from_map) if a.from_map else None,
        "label_on_return": f"hardware: {a.backend}, job <id>",
        "submission": "none: this pack is files only; see code/dscale/RUNBOOK_DSCALE.md part B (Peter only)",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print(f"hardware pack {out}: {len(entries)} circuits, est. QPU time {total_s / 60:.1f} min on {a.backend} "
          f"(ISA stand-in {T.FAKES[tname]}); nothing submitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
