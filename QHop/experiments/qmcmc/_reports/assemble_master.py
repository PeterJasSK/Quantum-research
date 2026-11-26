"""Assemble the master table for QHop/plans/qmcmc-applied-review.txt.

Reads screening rows C1..C4 (17 columns, " | " separated), applies post-experiment overrides
(Wave 4 + red team), adds new rows, sorts by wall-clock likelihood then steps likelihood, and
writes master_rows.txt next to this script. Run: python assemble_master.py
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
COLS = ["ID", "KNOWN/NEW", "Application", "Regime", "Mapping", "Variant", "Energy cost", "Spins",
        "HW fit", "Best classical", "Beats best classical", "S*", "Measured/estimated S", "Evidence",
        "Likelihood", "Verdict", "Main risk"]
C = {name: i for i, name in enumerate(COLS)}

OVERRIDES = {
    "B4-04": {"Measured/estimated S": "D6 matched beta: median 1.10 (n=8), 1.31 (n=10) vs best classical; 0.67-0.94 at load >= 1.5",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0) / steps 2% (0-5)", "Verdict": "KILL",
              "Main risk": "Nishimori prediction confirmed (D6): matched posteriors show no step gain at typical loads; overlap check q(x0)=q(replica) 0.657/0.656"},
    "B4-03": {"Measured/estimated S": "D6 alpha=0.5 window: 2.7-5.3 vs weak classical (n=10); E1 vs tempering/pair-flip/TAP/mode-jump: 0.17 (n=8), 0.20 (n=10), 0.02-0.15 (n=12); S<1 in 48/54 cells",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0) / steps 1% (0-3)", "Verdict": "KILL",
              "Main risk": "red team E1: posterior has only 1-4 nearby basins (2.5-4 flips apart); structure-aware classical proposals cross them"},
    "B6-01": {"Measured/estimated S": "D6 3x3 tomography: S 1.13 (2 views), 0.98 (3), 0.64 (4) vs local+ghost-swap",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0) / steps 1% (0-3)", "Verdict": "KILL",
              "Main risk": "matched posterior has no glass phase (Nishimori); classical ghost-swap moves remove the barriers"},
    "B6-18": {"Measured/estimated S": "D6 10-SNP LD block: S 0.33 [0.24,0.54] vs add/delete+swap",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0) / steps 0.5% (0-2)", "Verdict": "KILL",
              "Main risk": "the classical LD-partner swap move is 2-3x better per step than QeMCMC"},
    "B5-01": {"Measured/estimated S": "analogue D6 exp3 (correlated-predictor selection, g-prior): S 0.33 vs swap move",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0) / steps 1% (0-3)", "Verdict": "KILL",
              "Main risk": "same structure as B6-18; classical swap moves designed for collinearity win"},
    "K14": {"Measured/estimated S": "D6 control: 0.14 vs exact Swendsen-Wang at the usual MEDIUM T (0.10 hotter, 2.1 at 2x C-peak beta)",
            "Evidence": "SIMULATED", "Beats best classical": "N",
            "Likelihood": "wall-clock 0% (0-0) / steps 0% (0-1)", "Verdict": "KILL",
            "Main risk": "kept as the harness negative control; Swendsen-Wang dominates ferromagnetic MRFs"},
    "B3-07": {"S*": "7e7/1e8/1e27 (D8: ~2.2e4 CZ per proposal, F ~1e-19)", "Measured/estimated S": "D8 n=12 fixed composition: 1.72 [1.68,1.93] vs best swap mixture at 1.1 Tc; 0.95 vs PT per proposal; 5-8x worse per PT round",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0.1) / steps 2% (0-5)", "Verdict": "KILL",
              "Main risk": "meets the kill rule (S<2 at 1.1 Tc, <1.5 vs PT); ~2.2e4 CZ per proposal on heavy-hex"},
    "K15": {"S*": "7e7/1e8/1e27 (D8: ~2.2e4 CZ per proposal, F ~1e-19)", "Measured/estimated S": "as B3-07 (D8 CuAu-like): 1.72 vs swaps, 0.95 vs PT at 1.1 Tc",
            "Evidence": "SIMULATED", "Beats best classical": "N",
            "Likelihood": "wall-clock 0% (0-0.1) / steps 2% (0-5)", "Verdict": "KILL",
            "Main risk": "canonical any-pair swaps + PT already equilibrate real cathode SRO runs"},
    "B3-09": {"Measured/estimated S": "D8 Coulomb n=12: 4.28 [3.78,4.51] vs swaps at 1.1 Tc, 91 at 0.5 Tc; vs PT 1.60 (1.1 Tc), 1.02 (0.5 Tc) per proposal",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0.1) / steps 4% (1-10)", "Verdict": "QUANTUM-INSPIRED ONLY",
              "Main risk": "gain vs PT ~1x and fully classically computed at n=12; S* 1e5/3e6/3e25 (t_C ~1 us; D8 ~2.2e4 CZ per proposal, F ~1e-19)", "S*": "1e5/3e6/3e25 (D8 ~2.2e4 CZ, F ~1e-19)"},
    "B3-01": {"Measured/estimated S": "D2: S vs tuned PT LOW 7.9-18, MED 3.7-5.9, HIGH 1.1-3.5 (n=12-14); best quantum-move fraction p_q = 0 for move cost R >= 1e6 flips (one SK n=12 LOW instance 0.01 at 1e3)",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0.1) / steps 15% (5-30)", "Verdict": "KILL",
              "Main risk": "a quantum step is worth 1-20 classical flips; break-even needs ~7e7 (C3 bound: PT relaxation must exceed S*/2)"},
    "B1-14": {"Measured/estimated S": "D2 hybrid PT+quantum move: tau ratio 0.58-0.89 at p_q=1 (1.13 at SK n=14 MEDIUM), decohered 0.6-1.0; optimum p_q = 0",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0.1% (0-0.5) / steps 3% (1-8)", "Verdict": "KILL",
              "Main risk": "as B3-01; surrogate arm dominated classically (D5, E2)"},
    "B1-10": {"Measured/estimated S": "D5/E2 surrogate family: S_free 2.1-16 only at LOW with beta*sigma>1.5; vs hotter surrogate draw S_ext 0.04-0.6; vs K=100 classical inner chain quantum wins 4/182 cells (max 1.43)",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0.3% (0-1) / steps 3% (1-8)", "Verdict": "SIMULATE MORE",
              "Main risk": "classical delayed acceptance with ~100 inner surrogate steps matches quantum at n<=10; only a scaling question at tens of spins remains"},
    "B5-08": {"Measured/estimated S": "D5/E2 generic surrogate result (classically dominated at n<=10-12); grid-specific not run",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0.3% (0-1) / steps 3% (1-8)", "Verdict": "SIMULATE MORE",
              "Main risk": "same as B1-10; must also beat Random Chemistry; energy 0.3-0.5 s per cascade (arXiv:1405.4213)"},
    "B6-02": {"Measured/estimated S": "D5/E2 generic surrogate result (classically dominated at n<=12)",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0.2% (0-1) / steps 2% (0-6)", "Verdict": "KILL",
              "Main risk": "fold into B1-10 scaling question; no imaging-specific glassy surrogate identified"},
    "B6-08": {"Measured/estimated S": "D5/E2 generic surrogate result (classically dominated at n<=12)",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0.2% (0-1) / steps 2% (0-6)", "Verdict": "KILL",
              "Main risk": "fold into B1-10; delayed acceptance on the same surrogate is the fair rival"},
    "K0": {"S*": "7e7/1e8/3e10 (IBM; D4 SK n=10 t=6 2,160 CZ, F 3e-3); D-Wave-class 1e6/1.7e7",
           "Measured/estimated S": "D1 SK n=10: vs best mixture HIGH 0.90, MED 3.0, LOW 9.9; D2 vs tuned PT LOW 8-18, MED 4-6, HIGH 1-3.5; E3 vs mixture+exact 2-3-spin heat-bath n=6-8 LOW 0.62-1.06; FakeMarrakesh n=6 0.30-0.66",
           "Evidence": "SIMULATED", "Beats best classical": "N",
           "Likelihood": "wall-clock 0% (0-0) / steps 15% (5-30)", "Verdict": "BUILD NOW",
           "Main risk": "BUILD NOW only as calibration/thesis measurement (noise-induced bias, fidelity collapse); E3: a Heron run shows a fidelity-collapse curve, not an advantage threshold"},
    "B3-04": {"Measured/estimated S": "D4/E3 heavy-hex-native subset: 2.6-3.3x vs local/uniform, 1.67x vs tuned mixture, 0.18-0.24 vs native-tree classical moves; noisy (F model) 0.91-1.11",
              "Evidence": "SIMULATED", "Beats best classical": "N",
              "Likelihood": "wall-clock 0% (0-0) / steps 2% (0-5)", "Verdict": "BUILD NOW",
              "Main risk": "BUILD NOW only as exact bias/noise calibration bed (CZ 6-19x lower); not an advantage"},
    "B3-05": {"Likelihood": "wall-clock 0.2% (0-1%) / steps 2% (0-5%)",
              "Measured/estimated S": "vs surrogate-importance S <= 1 (own argument); D5/E2 generic surrogate result: classically dominated at n<=12"},
    "B3-06": {"Likelihood": "wall-clock 0.2% (0-1%) / steps 3% (0-8%)",
              "Measured/estimated S": "none measured for this energy; D5/E2 generic surrogate result: classically dominated at n<=12"},
    "B6-13": {"Likelihood": "wall-clock 0.2% (0-1) / steps 2% (0-5)",
              "Measured/estimated S": "~1x vs surrogate-driven classical proposal (reasoned); D5/E2 generic surrogate result"},
    "K3": {"Main risk": "BUILD NOW only as small hardware calibration (n<=8 tomography ~$126, E3); full 4096-start tomography ~$30k: drop at full size"},
}

NEW_ROWS = [
    ["N-S1", "NEW", "Classical basin-difference mask library (spin-off of mask-donation variant V24) as a general sampler",
     "MEDIUM / LOW", "any Ising: masks = XOR of pairs of greedy local minima, state-independent", "classical only (no QPU)",
     "cheap", "32-64 full", "3", "tuned PT, Metropolis, Houdayer/ICM",
     "N", "n/a (classical)", "E2: 0 wins / 80 vs PT/Metropolis per CPU second, 7-68x slower; mask acceptance 0.04 (n=32) to 0 (n=64)",
     "SIMULATED", "wall-clock 0% (0-0) / steps 0% (0-1)", "KILL",
     "special case of Houdayer / ICM / differential-evolution MCMC; library only enumerates the few minima at n<=12"],
    ["N-S2", "NEW", "Quantum mask-donation library (variant V24) for SK-type sampling: QPU in throughput mode",
     "MEDIUM / LOW", "any Ising; masks from QeMCMC outcomes on uniform reference states", "V24 fixed library L>=1024",
     "cheap", "<=27 full", "1", "weight-matched random masks, percolation masks, basin-difference library + local",
     "N", "~1 after library (amortised); library $1.6-11 for L=8192", "D9: 0.77-1.31 vs best classical library; with 50% local 0.08-0.94; k drifts to uniform (0.82 vs 1.00 at beta=1)",
     "SIMULATED", "wall-clock 0% (0-0.1) / steps 1% (0-3)", "KILL",
     "state-independent masks lose the state-dependence that gives QeMCMC its gain (58% -> 14% of full gap, n=6 -> 10)"],
]


def pct(field, which):
    m = re.search(which + r"\s*([0-9.]+)%", field)
    return float(m.group(1)) if m else 0.0


def main():
    rows = []
    for f in sorted(HERE.glob("C?-rows.txt")):
        for line in f.read_text().splitlines():
            if line.strip():
                parts = line.split(" | ")
                assert len(parts) == 17, (f, parts[0], len(parts))
                rows.append(parts)
    rows += NEW_ROWS
    by_id = {r[0]: r for r in rows}
    for rid, ov in OVERRIDES.items():
        for k, v in ov.items():
            by_id[rid][C[k]] = v
    rows.sort(key=lambda r: (-pct(r[C["Likelihood"]], "wall-clock"), -pct(r[C["Likelihood"]], "steps"), r[0]))
    out = [" | ".join(COLS)] + [" | ".join(r) for r in rows]
    (HERE / "master_rows.txt").write_text("\n".join(out) + "\n")
    from collections import Counter
    print(len(rows), "rows;", Counter(r[C["Verdict"]] for r in rows))


if __name__ == "__main__":
    main()
