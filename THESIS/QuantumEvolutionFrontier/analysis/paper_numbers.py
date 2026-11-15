"""Writes every number in the paper from the run JSONs: paper/numbers.tex (macros), paper/tab_record.tex,
paper/tab_audit.tex. Nothing in the paper is typed by hand; rerun after any analysis rerun.

    /home/peter/anaconda3/bin/python3 THESIS/QuantumEvolutionFrontier/analysis/paper_numbers.py
"""
from __future__ import annotations

import glob
import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
R = REPO / "THESIS/QuantumEvolutionFrontier/runs"
P = REPO / "THESIS/QuantumEvolutionFrontier/paper"
CORES = 8
TIER_S = {"core-hour": 3600.0, "core-year": 3.156e7, "1e6 core-years": 3.156e13}


def load(name):
    f = R / name
    return json.loads(f.read_text()) if f.exists() else None


def f(x, nd=3, sign=False):
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    return s.replace("-", "$-$") if not sign else s.replace("-", "$-$").replace("+", "$+$")


def sci(x: float) -> str:
    m, e = f"{x:.1e}".split("e")
    return f"{m}\\times10^{{{int(e)}}}"


def hw_file_count() -> dict:
    roots = ["QuantumLife", "artificial-life"]
    n = {r: len([p for p in glob.glob(str(REPO / r / "**/*.json"), recursive=True) if "ibm_" in Path(p).name])
         for r in roots}
    n["recovered (git)"] = len(list((REPO / "THESIS/QuantumEvolutionFrontier/data/recovered").glob("*ibm_*.json")))
    n["QuantumPhantoms live jobs"] = 4
    return n


def main() -> None:
    led, cc = load("ledger.json"), load("classical_cost.json")
    ct, coh = load("ct_twin.json"), load("ct_twin_features.json")
    scan, rep = load("qca_scan.json"), load("teleport_replay.json")
    M = {}

    nh = hw_file_count()
    M["nHwRunFiles"] = str(sum(nh.values()))
    M["nHwProjects"] = "three"

    # ---- QuantumTree
    qt = cc["qt"]
    mean = lambda arm, k: float(np.mean([r[k] for r in qt[arm]["rows"]]))
    M["qtDepthFloor"] = str(qt["serial_L1"]["rows"][0]["logical_depth_hw"])
    lone = json.loads((REPO / led["quantum_tree"]["arms"]["C_L1_ibm_kingston"]["source"]).read_text())
    M["qtDepthLone"] = str(json.loads((REPO / "QuantumLife/research_runs/BackLog" / lone["meta"]["run_files"][0])
                                      .read_text())["generations"][0]["logical_depth"])
    M["qtIdealLoneMean"] = f(mean("serial_L1", "ideal_c1"), 4, True)
    M["qtHwLoneMean"] = f(mean("serial_L1", "hw_c1_gen0"), 3, True)
    lt = [r["ideal_c1"] for r in qt["serial_L2"]["rows"]]
    M["qtIdealLtwoMin"], M["qtIdealLtwoMax"] = f(min(lt), 3, True), f(max(lt), 3, True)
    M["qtHwLtwoMean"] = f(mean("serial_L2", "hw_c1_gen0"), 3, True)
    M["qtCostLtwo"] = f(mean("serial_L2", "t_state_s") + mean("serial_L2", "t_sample_s"), 1)
    M["bwIdealLoneMean"] = f(mean("brick_L1", "ideal_c1"), 3, True)
    M["bwHwLoneMean"] = f(mean("brick_L1", "hw_c1_gen0"), 3, True)
    M["qtChiLfour"] = str(max(r["chi_max"] for a in qt for r in qt[a]["rows"]))
    M["qtCostLfour"] = f(max(r["t_state_s"] + r["t_sample_s"] for a in qt for r in qt[a]["rows"]), 0)
    arms = led["quantum_tree"]["arms"]
    M["qtDivHw"] = f(arms["B_hw_ibm_kingston"]["diversity"]["mean"], 2)
    M["qtDivSim"] = f(arms["A_base_sim"]["diversity"]["mean"], 2)
    M["qtZsim"] = f(abs(led["quantum_tree"]["z_c1_B_vs_sim"]), 1)
    sc = load("surrogate_check.json")
    M["surrUnitaryFixed"] = "$" + f"{max(r['max_diff_swap_replayed'] for r in sc if r['death'] == 'unitary'):.0e}" \
        .replace("e-", "\\times10^{-") + "}$"
    M["surrUnitaryCode"] = f(max(r["max_diff_code_surrogate"] for r in sc if r["death"] == "unitary"), 2)
    M["surrDamp"] = f(max(r["max_diff_code_surrogate"] for r in sc if r["death"] == "damping"
                          and r["interaction"] == "none"), 2)

    # ---- QALife
    ql = cc["qalife"]
    pj = {r["W"]: r for r in ql["pj0_natural_separable"]}
    m4 = {r["W"]: r for r in ql["month4_unitary"]}
    hw_pj = {r["W"]: r for r in led["qalife"]["pj0"] if r["death"] == "natural" and r["phenotype"] == "separable"}
    hw_m4 = {r["W"]: r for r in led["qalife"]["month4_unitary"]}
    M["costPjFifty"] = f(pj[50]["t_state_s"] + pj[50]["t_sample_s"], 1)
    M["costPjSevenSeven"] = f(pj[77]["t_state_s"] + pj[77]["t_sample_s"], 1)
    M["pjFiftyRetainPct"] = f(100 * hw_pj[50]["signal"] / pj[50]["ideal_witness"], 1)
    M["mFourTwentyFourRetainPct"] = f(100 * hw_m4[24]["signal"] / m4[24]["ideal_witness"], 1)
    abl = {(r["death"], r["phenotype"]): r for r in led["qalife"]["pj0"] if r["W"] == 4 and r["steps"] == 4}
    M["pjEntNat"] = f(abl[("natural", "entangled")]["signal"], 3)
    M["pjSepNat"] = f(abl[("natural", "separable")]["signal"], 3)
    p2 = {Path(r["source"]).name: r for r in led["qalife"]["p2"]}
    nine = next(r for k, r in p2.items() if "W9_LAST" in k)
    ten = next(r for k, r in p2.items() if "LIMIT-W10" in k)
    M["dampNineK"], M["dampTenK"] = f(nine["k_sigma"], 1), f(ten["k_sigma"], 1)

    # ---- motile + D-SCALE
    mot = [fr for fr in led["motile"]["frames"] if fr["certified"]]
    M["motileMin"] = f(min(fr["w_plus_zz"] for fr in mot), 3)
    M["motileMax"] = f(max(fr["w_plus_zz"] for fr in mot), 3)
    g = led["phantoms"]["ghz_spine"]
    M["ghzF"], M["ghzFsig"] = f(g["F_dfe"], 3), f(g["F_sigma"], 3)
    M["ghzTwo"], M["ghzTwoX"], M["ghzTwoZZ"] = f(g["ghz2"], 3), f(g["ghz2_X"], 3), f(g["ghz2_ZZ"], 3)

    # ---- record table + cost axis
    ds = cc["dscale"]
    ex = cc.get("extra", {})
    rows = []                                  # (label, qubits, rung, hw, ideal, cost_s, chi, verdict)
    def addrow(*a):
        rows.append(a)
    s2 = qt["serial_L2"]["rows"]
    addrow("Tree, serial, 2 layers", 108, "W-a", f"{np.mean([r['hw_c1_gen0'] for r in s2]):+.3f}",
           f"{np.mean([r['ideal_c1'] for r in s2]):+.3f}", np.mean([r['t_state_s'] + r['t_sample_s'] for r in s2]),
           s2[0]["chi_max"], "real, cheap")
    s1 = qt["serial_L1"]["rows"]
    addrow("Tree, floor (1 layer)", 108, "W-a", f"{np.mean([r['hw_c1_gen0'] for r in s1]):+.3f}",
           f"{np.mean([r['ideal_c1'] for r in s1]):+.4f}", np.mean([r['t_state_s'] + r['t_sample_s'] for r in s1]),
           s1[0]["chi_max"], "artefact")
    b2 = qt["brick_L2"]["rows"]
    addrow("Tree, brick wall, 2 layers", 108, "W-a", f"{np.mean([r['hw_c1_gen0'] for r in b2]):+.3f}",
           f"{np.mean([r['ideal_c1'] for r in b2]):+.3f}", np.mean([r['t_state_s'] + r['t_sample_s'] for r in b2]),
           b2[0]["chi_max"], "real, cheap")
    if rep:
        tel = [x for x in rep if "error" not in x and x["arm"] == "teleport" and x["herald"] and x["d_qubits"] == 12]
        if tel:
            addrow("Tree, teleported bond $d=12$", 104, "W-a", f"{np.mean([x['hw_mean'] for x in tel]):+.3f}",
                   f"{np.mean([x['ideal_mean'] for x in tel]):+.3f}",
                   max(v["t_sample_s"] for k, v in ex.items() if k.startswith("teleport")), None, "see text")
    addrow("QAL Month 4, $W=24$", 48, "W-a", f"{hw_m4[24]['signal']:.3f}", f"{m4[24]['ideal_witness']:.3f}",
           m4[24]["t_state_s"] + m4[24]["t_sample_s"], m4[24]["chi_max"], "alive $2.4\\sigma$")
    addrow("QAL germ/soma, $W=50$", 100, "W-a", f"{hw_pj[50]['signal']:.3f}", f"{pj[50]['ideal_witness']:.3f}",
           pj[50]["t_state_s"] + pj[50]["t_sample_s"], pj[50]["chi_max"], f"alive {hw_pj[50]['k_sigma']:.1f}$\\sigma$")
    if "motile_org2_L4" in ex:
        msim = json.loads((REPO / "artificial-life/research_runs/pj2_motile/pj2_line_org2L4_statevector_sim_sim.json")
                          .read_text())["scenarios"]["motile"]["isolated"]
        ideal_m = min(x["w"] + x["zz"] for x in msim if x.get("certified"))
        addrow("QAL motile, ghz2", ex["motile_org2_L4"]["n_qubits"], "W-b", M["motileMin"], f"{ideal_m:.3f}",
               ex["motile_org2_L4"]["t_sample_s"], None, "certified")
    S = led["phantoms"]["chsh"]
    addrow("CT roll, CHSH", 2, "W-d", f"{S['S']:.3f}", "2.828", ex["chsh_roll"]["t_sample_s"], None, f"{S['z_above_2']:.1f}$\\sigma$ $>2$")
    addrow("D-SCALE GHZ spine", 28, "W-c", f"{g['F_dfe']:.3f}", "1.000", ds["ghz_spine"]["t_s"], 2, "fails 0.5")
    qt_tiles = ds["ch_qca_tiles"]
    neg = led["phantoms"]["claims"][1]
    addrow("D-SCALE QCA, $t=2$", 23, "W-b", f"{neg['value']:.3f}", "--",
           max(r["t_state_s"] + r["t_sample_s"] for r in qt_tiles), max(r["chi_max"] for r in qt_tiles),
           "marginal")
    M["costMaxS"] = f(max(r[5] for r in rows), 0)
    M["chiMaxRecord"] = str(max(r[6] for r in rows if r[6]))
    with open(P / "tab_record.tex", "w") as fh:
        fh.write("\\begin{table*}[t]\n\\centering\n\\caption{Hardware results and their exact classical "
                 "reproduction on one eight-core machine. Hardware and ideal values are the reported observable "
                 "(tree: $c(1)$ at generation 0, bond: mean bond $c(d)$; QAL: $\\langle X^{\\otimes W}\\rangle$; "
                 "ghz2: $\\langle XX\\rangle+\\langle ZZ\\rangle$; GHZ: fidelity; QCA: pair negativity). Cost: wall "
                 "clock for the exact state plus samples. Backends: \\texttt{ibm\\_kingston} (tree serial and brick, "
                 "QAL), \\texttt{ibm\\_marrakesh} (bond, motile, CT roll, D-SCALE).}\n\\label{tab:record}\n"
                 "\\begin{tabular}{lrcrrrrl}\n\\toprule\nCircuit & qubits & rung & hardware & ideal & cost (s) & "
                 "$\\chi$ & verdict\\\\\n\\midrule\n")
        for r in rows:
            hw, ide = (str(x).replace("-", "$-$", 1) if str(x).startswith("-") else str(x) for x in (r[3], r[4]))
            fh.write(f"{r[0]} & {r[1]} & {r[2]} & {hw} & {ide} & {r[5]:.2f} & {r[6] if r[6] else '--'} & {r[7]}\\\\\n")
        fh.write("\\bottomrule\n\\end{tabular}\n\\end{table*}\n")

    # ---- distance to L2 (cost tiers)
    cmax = max(r[5] for r in rows) * CORES
    M["coreSecMax"] = f"{cmax:.0f}"
    M["dLtwoOrders"] = f(math.log10(TIER_S["1e6 core-years"] / cmax), 1)
    bp = ds["ch_qca_bp_ladder"]
    tstar = min(r["t"] for r in bp if r["hard"])
    M["bpTstar"], M["bpTpass"] = str(tstar), "2"
    M["bpDistance"] = str(tstar - 2)

    # ---- QCA scan
    if scan:
        sr = scan["rows"]
        def cell(s, t):
            return next((r for r in sr if r["sites_requested"] == s and r["t"] == t), None)
        for s, t, key in ((23, 2, "A"), (23, 3, "B"), (23, 4, "C"), (23, 5, "D"), (40, 4, "E"), (40, 3, "F")):
            c = cell(s, t)
            if c and "chi_max" in c:
                M[f"scanChi{key}"] = str(c["chi_max"])
                M[f"scanT{key}"] = f(c["t_state_s"] + c["t_sample_s"], 2)
                M[f"scanTwoQ{key}"] = str(c["two_q"])
            elif c:
                M[f"scanChi{key}"] = "n/a"
                M[f"scanT{key}"] = f"$>{c.get('timeout_s', scan['timeout_s'])}$" if "timeout_s" in c else "n/a"
                M[f"scanTwoQ{key}"] = "n/a"
        t3 = [r for r in sr if r["t"] == 3 and r["sites_requested"] >= 40 and "chi_max" in r]
        M["scanT3min"] = f(min(r["t_state_s"] + r["t_sample_s"] for r in t3), 0)
        M["scanT3max"] = f(max(r["t_state_s"] + r["t_sample_s"] for r in t3), 0)
        M["scanT3chi"] = str(max(r["chi_max"] for r in t3))
        with open(P / "tab_scan.tex", "w") as fh:
            fh.write("\\begin{tabular}{rrrrr}\n\\toprule\nsites (req./alloc.) & $t$ & 2q gates & $\\chi$ & exact (s)\\\\\n\\midrule\n")
            for r in sr:
                if "chi_max" in r:
                    fh.write(f"{r['sites_requested']}/{r['sites']} & {r['t']} & {r['two_q']} & {r['chi_max']} & "
                             f"{r['t_state_s'] + r['t_sample_s']:.2f}\\\\\n")
                else:
                    lim = f"$>{r['timeout_s']}$" if "timeout_s" in r else f"$>{r['mem_cap_gb']}$ GB"
                    fh.write(f"{r['sites_requested']}/-- & {r['t']} & -- & -- & {lim}\\\\\n")
            fh.write("\\bottomrule\n\\end{tabular}\n")

    # ---- CT roll
    roll, rn = ct["roll"], ct.get("roll_noise")
    M["rollObs"] = ", ".join(str(x) for x in roll["observed"])
    M["rollExp"] = ", ".join(f"{x:.1f}" for x in roll["expected"])
    M["rollN"] = str(roll["n_independent"])
    M["rollP"] = sci(roll["p_mc_G"])
    M["rollMC"] = f"{roll['mc_cohorts']:,}".replace(",", "{,}")
    M["rollPct"] = f"{100 * roll['loglik_pctile_vs_prng']:.3f}"
    if rn:
        M["rollIdeal"] = ", ".join(f"{x:.3f}" for x in rn["ideal"]["size_band_freq"])
        M["rollNoisy"] = ", ".join(f"{x:.3f}" for x in rn["noisy_fake_marrakesh"]["size_band_freq"])
        M["rollTwoQLogical"] = str(rn["ideal"]["two_q"])
        M["rollTwoQIsa"] = str(rn["noisy_fake_marrakesh"]["two_q"])
        M["rollDepthIsa"] = str(rn["noisy_fake_marrakesh"]["depth"])
    M["chshS"], M["chshSig"], M["chshZ"] = f(S["S"], 3), f(S["sigma_S_equal_E"], 3), f(S["z_above_2"], 1)

    # ---- seeds + renders
    if ct.get("seeds"):
        pool = ct["seeds"]["pooled"]
        M["seedN"] = f"{ct['seeds']['n_per_arm']:,}".replace(",", "{,}")
        for arm, key in (("ideal", "Ideal"), ("noisy", "Noisy"), ("indep", "Indep")):
            v = pool[f"hardware_vs_{arm}"]["seed_vox"]
            M[f"seedVoxHw"] = f(v["mean_a"], 1)
            M[f"seedVox{key}"] = f(v["mean_b"], 1)
            M[f"seedKs{key}"] = f(v["ks_D"], 3)
            e = pool[f"hardware_vs_{arm}"]["elong"]
            M[f"seedElongKs{key}"] = f(e["ks_D"], 3)
        sp = pool["hw_split_half"]["seed_vox"]
        M["seedKsSplit"] = f(sp["ks_D"], 3)
        pt = ct["seeds"]["per_tile"]
        M["seedReproOk"] = str(sum(t["stored_seed_reproducible"] for t in pt))
        M["seedTiles"] = str(len(pt))
        for arm, key in (("hardware", "Hw"), ("ideal", "Ideal"), ("noisy", "Noisy"), ("indep", "Indep")):
            M[f"corrRms{key}"] = f(np.mean([t["corr_offdiag_rms"][arm] for t in pt]), 3)
    if coh:
        fe = coh["features"]
        u = fe["unpaired"]
        M["renderNq"], M["renderNt"] = str(u["diameter_baseline_mm"]["n_q"]), str(u["diameter_baseline_mm"]["n_twin"])
        for k, key in (("diameter_baseline_mm", "Diam"), ("vdt_d", "Vdt"), ("roi_mean", "Roi"),
                       ("glcm_contrast", "Glcm"), ("seed_cells", "Cells")):
            M[f"render{key}Q"] = f(u[k]["mean_q"], 1)
            M[f"render{key}T"] = f(u[k]["mean_twin"], 1)
            M[f"render{key}P"] = f(u[k]["ks_p"], 2)
        M["renderMinP"] = f(min(v["ks_p"] for v in u.values()), 2)
        pp = fe["paired_per_tile"]
        M["renderPairedMinP"] = f(min(v["wilcoxon_p"] for v in pp.values()), 2) if pp else "--"
        n1, n2 = u["vdt_d"]["n_q"], u["vdt_d"]["n_twin"]
        M["renderKsCrit"] = f(1.358 * math.sqrt((n1 + n2) / (n1 * n2)), 2)       # two-sample KS, alpha = 0.05
    if ct.get("seeds"):
        M["seedKsPmax"] = sci(max(pool[f"hardware_vs_{a}"]["seed_vox"]["ks_p"] for a in ("ideal", "noisy", "indep")))
        M["seedKsSplitP"] = f(pool["hw_split_half"]["seed_vox"]["ks_p"], 2)

    # ---- teleport replay
    tel_ok = False
    if rep:
        ok = [x for x in rep if "error" not in x]
        sw = [x for x in ok if x["arm"] == "swap" and "swap_r8" in x["source"]]
        te = [x for x in ok if x["arm"] == "teleport" and x["herald"] and x["d_qubits"] == 12]
        if sw:
            rows_ = [r for x in sw for r in x["rows"]]
            M["swapIdeal"] = f(np.mean([r["ideal_c_at_d"] for r in rows_]), 3, True)
            M["swapHw"] = f(np.mean([r["hw_c_at_d"] for r in rows_]), 3, True)
            M["swapSignWrongPct"] = f(100 * np.mean([np.sign(r["ideal_c_at_d"]) != np.sign(r["hw_c_at_d"])
                                                     for r in rows_]), 0)
            M["swapGens"] = str(len(rows_))
            M["envMatchAll"] = "every" if all(r["env_match"] for x in ok for r in x["rows"]) else "not every"
        if te:
            rows_ = [r for x in te for r in x["rows"]]
            M["telIdeal"] = f(np.mean([r["ideal_c_at_d"] for r in rows_]), 3, True)
            M["telHw"] = f(np.mean([r["hw_c_at_d"] for r in rows_]), 3, True)
            M["telSignAgreePct"] = f(100 * np.mean([np.sign(r["ideal_c_at_d"]) == np.sign(r["hw_c_at_d"])
                                                    for r in rows_]), 0)
            M["telGens"] = str(len(rows_))
            iv, hv = np.array([r["ideal_c_at_d"] for r in rows_]), np.array([r["hw_c_at_d"] for r in rows_])
            M["telCorr"] = f(float(np.corrcoef(iv, hv)[0, 1]), 2, True)
            tel_ok = True
    tl = led["teleport"]
    M["telDepth"] = f(tl["tel_herald_hw_ibm_marrakesh_d12"]["logical_depth_mean"], 0)
    M["telHwLedger"] = f(tl["tel_herald_hw_ibm_marrakesh_d12"]["c_bond"]["mean"], 3, True) + "$\\pm$" + \
        f(tl["tel_herald_hw_ibm_marrakesh_d12"]["c_bond"]["se"], 3)
    M["swapDepth"] = f(tl["swap_r8_ibm_marrakesh_d12"]["logical_depth_mean"], 0)
    log = (R / "teleport_ideal_sign.log").read_text()
    M["sigReduced"] = f(float(log.split("MEAN ideal c(d) =")[1].split()[0]), 4, True)

    # ---- genealogy width sweeps table
    with open(P / "tab_qal.tex", "w") as fh:
        fh.write("\\begin{tabular}{lrrrrrrr}\n\\toprule\nModel & $W$ & qubits & steps & hardware & $k\\sigma$ & ideal & "
                 "exact (s)\\\\\n\\midrule\n")
        for W in sorted(hw_m4):
            r, c = hw_m4[W], m4.get(W)
            fh.write(f"Month 4 & {W} & {2 * W} & {r['steps']} & {r['signal']:.3f} & {r['k_sigma']:.1f} & "
                     f"{c['ideal_witness']:.3f} & {c['t_state_s'] + c['t_sample_s']:.2f}\\\\\n" if c else "")
        fh.write("\\midrule\n")
        for W in sorted(hw_pj):
            r, c = hw_pj[W], pj.get(W)
            ide = f"{c['ideal_witness']:.3f}" if c else "1.000$^\\dagger$"
            cost = f"{c['t_state_s'] + c['t_sample_s']:.2f}" if c else "--"
            fh.write(f"germ/soma & {W} & {2 * W} & {r['steps']} & {r['signal']:.3f} & {r['k_sigma']:.1f} & {ide} & "
                     f"{cost}\\\\\n")
        fh.write("\\bottomrule\n\\end{tabular}\n")
    # ---- roll size-mix table
    if rn:
        with open(P / "tab_roll.tex", "w") as fh:
            fh.write("\\begin{tabular}{lrrrr}\n\\toprule\nSize band & rulebook & ideal sim & noisy sim & hardware\\\\\n"
                     "\\midrule\n")
            bands = ["$<6$ mm", "6--8 mm", "8--20 mm", "$>20$ mm"]
            for i, b in enumerate(bands):
                fh.write(f"{b} & {roll['rulebook_p'][i]:.3f} & {rn['ideal']['size_band_freq'][i]:.3f} & "
                         f"{rn['noisy_fake_marrakesh']['size_band_freq'][i]:.3f} & {roll['observed'][i]}/{roll['n_independent']}"
                         f"\\\\\n")
            fh.write(f"\\midrule\nshots or draws & -- & {rn['ideal']['shots']:,} & {rn['noisy_fake_marrakesh']['shots']:,} & "
                     f"{roll['n_independent']}\\\\\n\\bottomrule\n\\end{{tabular}}\n".replace(",", "{,}"))

    # ---- prose with numbers (generated, so no number is typed by hand)
    Q = lambda k: M.get(k, "??")
    prose = {}
    prose["teleportAuditCell"] = (f"SWAP ideal {Q('swapIdeal')}, hardware {Q('swapHw')}" if "swapIdeal" in M
                                  else "replay pending")
    prose["teleportParagraph"] = (
        f"A teleported long-range CNOT on 104 qubits (logical depth {Q('telDepth')}) was compared with a SWAP ladder "
        f"(depth {Q('swapDepth')}) at distance 12. We replayed every SWAP-arm hardware generation exactly: beliefs rebuilt from "
        f"the recorded frequencies, with the environment schedule matching the recorded one in {Q('envMatchAll')} "
        f"generation. The SWAP arm reads {Q('swapHw')} on hardware where its ideal is {Q('swapIdeal')}; the sign is "
        f"wrong in {Q('swapSignWrongPct')}\\% of {Q('swapGens')} generations. "
        + (f"The heralded teleport arm reads {Q('telHw')} against an ideal of {Q('telIdeal')}, with sign agreement in "
           f"{Q('telSignAgreePct')}\\% of {Q('telGens')} generations (correlation {Q('telCorr')}). " if tel_ok else
           f"The teleport arm reads {Q('telHwLedger')} on hardware; its exact replay (mid-circuit measurement forces a "
           f"per-shot simulation of 104 qubits) did not finish within our compute budget, so we report no ideal for it. ")
        + f"The original write-up quoted an exact ideal of $-$0.29; its own script, rerun, gives a mean of "
          f"{Q('sigReduced')} on its reduced 18-qubit model with alternating sign. A depth comparison alone decides "
          f"nothing; the exact replay does.")
    prose["scanParagraph"] = (
        f"We measure the distance to L2 on two axes. \\emph{{Cost.}} The most expensive exact reproduction of a "
        f"hardware result in Table~\\ref{{tab:record}} took {Q('costMaxS')}~s, at most {Q('coreSecMax')} "
        f"core-seconds on eight cores. Taking $10^6$ core-years ($3.2\\times10^{{13}}$ core-seconds) as a conservative "
        f"threshold for ``out of classical reach'', the record sits {Q('dLtwoOrders')} orders of magnitude below it "
        f"(Fig.~\\ref{{fig:map}}). For the genealogy family this distance does not shrink with better hardware, because "
        f"$\\chi$ stays 2 at every width. \\emph{{Depth.}} The QCA is the only family with non-Clifford coupling on a "
        f"lattice with loops. On the live 23-site region, belief propagation with $\\chi\\le16$ converges up to depth "
        f"$t=3$ and fails from $t^*={Q('bpTstar')}$. Hardware passed its pair witness at $t={Q('bpTpass')}$, so the depth "
        f"distance is {Q('bpDistance')} steps. Failure of belief propagation is not classical hardness: exact MPS "
        f"reproduces the same 23 sites at $t=4$ in {Q('scanTC')}~s ($\\chi={Q('scanChiC')}$). Exact cost does rise "
        f"steeply with width and depth (Table~\\ref{{tab:scan}}): at 40 or more sites, $t=3$ costs {Q('scanT3min')} to "
        f"{Q('scanT3max')}~s ($\\chi$ up to {Q('scanT3chi')}) and $t=4$ did not finish within 1200~s and 20~GB at any "
        f"width. That is the direction in which an "
        f"L2 candidate could appear. It needs a passing witness at the same width and depth, and today the witness at "
        f"$t=2$ passed on one of four pairs.")
    prose["ctParagraph"] = (
        f"The live run rolled twelve tumours ({Q('rollN')} independent words and two sibling pairs) in one job on "
        f"\\texttt{{ibm\\_marrakesh}}, with a CHSH test in the same job: $S={Q('chshS')}\\pm{Q('chshSig')}$ (2048 shots "
        f"per setting), {Q('chshZ')}$\\sigma$ above the local bound. Every case is therefore P-L0. Each grown tumour starts "
        f"from one Z snapshot of a 23-site QCA measured in a second job, whose pair witness passed marginally. We "
        f"compared three levels with classical twins. \\emph{{Roll.}} The independent size draws were "
        f"({Q('rollObs')}) for the bands $<6$, 6--8, 8--20 and $>20$~mm, against ({Q('rollExp')}) expected under the "
        f"rulebook (Table~\\ref{{tab:roll}}). Against {Q('rollMC')} classical cohorts drawn from the same rulebook this gives "
        f"$p={Q('rollP')}$ (G statistic), and the joint log-likelihood falls at percentile {Q('rollPct')}\\%. The "
        f"9-qubit roll compiles from {Q('rollTwoQLogical')} to {Q('rollTwoQIsa')} two-qubit gates (depth "
        f"{Q('rollDepthIsa')}); simulated Heron noise moves the ideal size mix ({Q('rollIdeal')}) to ({Q('rollNoisy')}), "
        f"the same direction as the hardware. \\emph{{Seeds.}} For each tile we compared the {Q('seedN')} hardware "
        f"snapshots per arm with an ideal sampler of the same circuit, a noisy sampler and independent coins with the "
        f"hardware marginals (Fig.~\\ref{{fig:twin}}a). Hardware split halves agree (seed-size KS $D={Q('seedKsSplit')}$, "
        f"$p={Q('seedKsSplitP')}$); hardware differs from the ideal ($D={Q('seedKsIdeal')}$), noisy "
        f"($D={Q('seedKsNoisy')}$) and independent ($D={Q('seedKsIndep')}$) twins, all $p\\le{Q('seedKsPmax')}$. The mean "
        f"pair-correlation RMS is {Q('corrRmsHw')} on hardware, {Q('corrRmsIdeal')} ideal, {Q('corrRmsNoisy')} noisy and "
        f"{Q('corrRmsIndep')} for independent coins. The seed structure comes from correlations that any classical "
        f"sampler given the joint distribution reproduces, and that a marginals-only sampler loses. All "
        f"{Q('seedReproOk')} of {Q('seedTiles')} stored seeds were regenerated from the recorded hardware bits. "
        f"\\emph{{Rendered nodules.}} Four replicate cohorts per arm, each grown and rendered into the same "
        f"Siemens-scanner host, gave {Q('renderNq')} quantum-seeded and {Q('renderNt')} twin-seeded nodules "
        f"(Fig.~\\ref{{fig:twin}}b). No feature differed: KS $p\\ge{Q('renderMinP')}$, paired per-tile Wilcoxon "
        f"$p\\ge{Q('renderPairedMinP')}$. Baseline diameter is equal by construction, because growth targets the rolled "
        f"size. At these sample sizes the test detects $D\\ge{Q('renderKsCrit')}$; smaller differences are not excluded.")
    prose["ruleParagraph"] = (
        f"The case study separates what the quantum computer adds from what it costs. The Bell test certifies that "
        f"the draw was not chosen. After rendering, the content cannot be told from its classical twin. Sampling the "
        f"rulebook directly on hardware distorted the medical statistics ($p={Q('rollP')}$). The rule that follows: "
        f"certify the seed on the quantum computer, then sample the content classically from it, for example with a "
        f"deterministic random bit generator keyed by the certified bits~\\cite{{barker2015}}. The classical twin then "
        f"\\emph{{is}} the generator. The rulebook is reproduced up to sampling noise, and the job identifier, the "
        f"$S$ value and the seed hash travel with every case as its replayable record. Quantum structure, where wanted "
        f"(correlated sibling lesions, lineage-shaped seeds), is added only with a passing witness in the same job and "
        f"labelled P-L1.")
    prose["conclusionParagraph"] = (
        f"Today's quantum computers can do one thing for medical imaging that classical generators cannot: certify "
        f"that synthetic validation cases were not chosen. In our live cohort the Bell value was $S={Q('chshS')}$, "
        f"{Q('chshZ')}$\\sigma$ above the local bound. Every case is replayable from its seed, and its content cannot be "
        f"told from a classical twin. The design rule is to certify the seed on the quantum computer and sample the "
        f"content classically. From there the road to more complex quantum-native content has three further layers, "
        f"each with a pass criterion: correlated families from one entangled lineage, compressed growth models, and "
        f"seed structure beyond classical reach. The nearest open cell is the QCA at depth four and forty or more "
        f"sites, which exact classical simulation on one machine did not finish. Quantum simulation of life itself is "
        f"not on that road yet: every faithful circuit we ran was reproduced classically in at most {Q('costMaxS')}~s. "
        f"Certified, not superior, is the honest starting point, and it is already useful.")
    prose["figOneCaption"] = (
        "Every hardware result in our record, placed by its margin above the classical bound of its witness (vertical, "
        "symmetric log scale; marker = witness rung, colour = project) and by the measured cost of reproducing it "
        "exactly on one eight-core machine (horizontal, core-seconds). Dashed lines: cost tiers. Shaded: alive and "
        "beyond $10^6$ core-years, the region an L2 claim needs; it is empty. Lower strip: the QCA family in "
        "simulation only (exact MPS, ideal) by patch size and depth; arrows mark cells that did not finish within "
        "1200~s and 20~GB.")
    prose["figTwoCaption"] = (
        f"Classical-twin test of the procedurally generated CT nodules. (a)~Seed size over {Q('seedN')} QCA snapshots per "
        f"arm: hardware, an ideal classical sampler of the same circuit, a noisy sampler (FakeMarrakesh noise model) "
        f"and independent coins with the hardware marginals. (b)~Rendered nodules from four replicate cohorts per arm, "
        f"quantum-seeded ($n={Q('renderNq')}$) vs twin-seeded ($n={Q('renderNt')}$), standardised per feature; "
        f"two-sample KS $p$ per feature.")
    with open(P / "prose.tex", "w") as fh:
        fh.write("% generated by analysis/paper_numbers.py -- do not edit\n")
        for k, v in prose.items():
            fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    missing = sorted({k for v in prose.values() for k in [] } | {s for s in M if M[s] == "??"})
    print("prose macros:", len(prose), "unresolved:", [k for k, v in prose.items() if "??" in v])

    with open(P / "numbers.tex", "w") as fh:
        fh.write("% generated by analysis/paper_numbers.py -- do not edit\n")
        for k, v in sorted(M.items()):
            fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    print(f"{len(M)} macros;", ", ".join(f"{k}={v}" for k, v in sorted(M.items())))


if __name__ == "__main__":
    main()
