"""E7 classical-twin test for the procedurally generated CT nodules of the live run (no QPU).

Three levels, all against the live run research_runs/dscale_live_100_20261031-170957:
  roll   the 8 independent quantum-rolled parameter words vs the rulebook, judged against 200,000 classical
         (PRNG) cohorts of the same size drawn from the same rulebook.
  seeds  per tile, the 4,000 hardware QCA snapshots (bits.npz) vs classical twins of the same logical circuit:
         ideal sampler (exact MPS), noisy sampler (FakeMarrakesh noise model, same physical layout) and an
         independent-marginals sampler (each site an independent coin with the hardware marginal). Each
         snapshot is lifted to the 3-D seed exactly as dscale.live does.
  cohort writes seed_shapes.npz for K replicate cohorts per arm (hardware shots vs ideal-twin shots) into
         copies of the run, ready for imaging.build_tiles (render step: --part render).

    cd QuantumPhantoms/code && /home/peter/anaconda3/bin/python3 \
        ../../THESIS/QuantumEvolutionFrontier/analysis/ct_twin.py --part roll|seeds|cohort|render|features
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[3]
RUN = REPO / "QuantumPhantoms/research_runs/dscale_live_100_20261031-170957"
OUTD = REPO / "THESIS/QuantumEvolutionFrontier/runs"
COH = OUTD / "ct_twin_cohorts"
sys.path[:0] = [str(REPO / "QuantumPhantoms/code")]
PY = "/home/peter/anaconda3/bin/python3"
K_REP = 4                                    # replicate cohorts per arm


# ---------------------------------------------------------------- roll vs rulebook
def part_roll() -> dict:
    from f1_quantum.rulebook import LOBE_FREQS, MARGIN_GIVEN_TYPE, SIZE_BANDS, TYPE_GIVEN_SIZE
    from common.datamodel import LOBES, MARGINS, TYPES
    cohort = json.loads((RUN / "cohort_params.json").read_text())
    indep = [t for t in cohort if t["lineage_id"].startswith("tile")]
    size_mm = [b[1] for b in SIZE_BANDS]
    p_size = np.array([b[2] for b in SIZE_BANDS])
    obs = Counter(size_mm.index(t["size_mm"]) for t in indep)
    n = len(indep)
    o = np.array([obs.get(i, 0) for i in range(4)])

    def g_stat(counts, p):
        e = p * counts.sum()
        m = counts > 0
        return float(2 * (counts[m] * np.log(counts[m] / e[m])).sum())

    g_obs = g_stat(o, p_size)
    rng = np.random.default_rng(7)
    sims = rng.multinomial(n, p_size, size=200_000)
    g_sim = np.array([g_stat(s, p_size) for s in sims])
    p_mc = float((g_sim >= g_obs - 1e-12).mean())
    # joint log-likelihood of the full parameter word under the rulebook
    def loglik(t):
        si = size_mm.index(t["size_mm"])
        band = SIZE_BANDS[si][0]
        lp = np.log(p_size[si]) + np.log(TYPE_GIVEN_SIZE[band][TYPES.index(t["type"])])
        lp += np.log(MARGIN_GIVEN_TYPE[t["type"]][MARGINS.index(t["margin"])]) + np.log(LOBE_FREQS[t["lobe"]])
        return lp
    ll_obs = float(sum(loglik(t) for t in indep))
    ll_sim = []
    for _ in range(50_000):
        tot = 0.0
        for _ in range(n):
            si = rng.choice(4, p=p_size)
            band = SIZE_BANDS[si][0]
            ti = rng.choice(4, p=TYPE_GIVEN_SIZE[band])
            mi = rng.choice(3, p=MARGIN_GIVEN_TYPE[TYPES[ti]])
            li = rng.choice(5, p=[LOBE_FREQS[l] for l in LOBES])
            tot += (np.log(p_size[si]) + np.log(TYPE_GIVEN_SIZE[band][ti]) + np.log(MARGIN_GIVEN_TYPE[TYPES[ti]][mi])
                    + np.log(LOBE_FREQS[LOBES[li]]))
        ll_sim.append(tot)
    ll_sim = np.array(ll_sim)
    res = {"n_independent": n, "size_band_mm": size_mm, "rulebook_p": p_size.tolist(), "observed": o.tolist(),
           "expected": (p_size * n).tolist(), "G": g_obs, "p_mc_G": p_mc, "mc_cohorts": len(g_sim),
           "loglik_obs": ll_obs, "loglik_pctile_vs_prng": float((ll_sim <= ll_obs).mean()),
           "loglik_prng_mean": float(ll_sim.mean()), "loglik_prng_sd": float(ll_sim.std()),
           "draws": [{k: t[k] for k in ("size_mm", "type", "margin", "lobe")} for t in indep]}
    print(json.dumps({k: v for k, v in res.items() if k != "draws"}, indent=1))
    return res


def part_roll_noise() -> dict:
    """Same 9-qubit roll circuit, simulated: ideal vs FakeMarrakesh noise. Size-band mix after decode."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
    from f1_quantum.circuit import build_tumor_circuit
    from f1_quantum.decode import decode_memory
    from f1_quantum.rulebook import SIZE_BANDS, Rulebook, angles_from_rulebook
    rb = Rulebook.default() if hasattr(Rulebook, "default") else Rulebook()
    qc = build_tumor_circuit(angles_from_rulebook(rb))
    size_mm = [b[1] for b in SIZE_BANDS]
    out = {"circuit": {"n_qubits": qc.num_qubits, "ops": dict(qc.count_ops())}}
    shots = 100_000
    fake = FakeMarrakesh()
    for name, sim, circ in (("ideal", AerSimulator(seed_simulator=3), qc),
                            ("noisy_fake_marrakesh", AerSimulator.from_backend(fake, seed_simulator=3),
                             transpile(qc, backend=fake, optimization_level=3, seed_transpiler=1))):
        mem = sim.run(circ, shots=shots, memory=True).result().get_memory()
        ps = decode_memory(mem, rb, generation=0, shot_start=0, lineage_prefix="x", n_qubits=9)
        c = Counter(size_mm.index(p.size_mm) for p in ps)
        out[name] = {"shots": shots, "size_band_freq": [c.get(i, 0) / shots for i in range(4)],
                     "depth": circ.depth(), "two_q": sum(v for k, v in circ.count_ops().items() if k in ("cx", "cz", "ecr"))}
        print(name, out[name], flush=True)
    obs = json.loads((OUTD / "ct_twin.json").read_text())["roll"]["observed"]
    for name in ("ideal", "noisy_fake_marrakesh"):
        p = np.clip(np.array(out[name]["size_band_freq"]), 1e-9, 1)
        out[name]["loglik_observed_sizes"] = float((np.array(obs) * np.log(p)).sum())
    return out


# ---------------------------------------------------------------- seed-shape twins
def _live_context():
    from qiskit import qpy
    from dscale import run as R, targets as T
    from dscale.families import ch_qca as Q
    with open(RUN / "dscale/live/components.qpy", "rb") as f:
        comps = qpy.load(f)
    qca = [c for c in comps if c.metadata.get("family") == "ch-qca" and c.metadata.get("tile_id")]
    z = np.load(RUN / "dscale/live/bits.npz")
    hw = [z[f"ch-qca_{10 + j}"] for j in range(len(qca))]
    alloc = json.loads((RUN / "dscale/allocation.json").read_text())
    tg = T.get("marrakesh")
    patch = Q.patch_of(alloc, tg)
    params = json.loads((RUN / "cohort_params.json").read_text())
    qrun = json.loads((RUN / "quantum_run.json").read_text())
    return qca, hw, patch, params, qrun


def features(occ: np.ndarray, bits_row: np.ndarray) -> dict:
    idx = np.argwhere(occ > 0).astype(float)
    ev = np.sort(np.linalg.eigvalsh(np.cov(idx.T) + 1e-9 * np.eye(3)))[::-1] if len(idx) > 3 else np.ones(3)
    ext = (idx.max(0) - idx.min(0) + 1) if len(idx) else np.zeros(3)
    return {"n_active": int(bits_row.sum()), "seed_vox": int(occ.sum()), "elong": float(np.sqrt(ev[0] / ev[2])),
            "extent_vox": float(ext.max())}


def sample_twins(qc, layout, shots: int, seed: int) -> dict:
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
    ideal = AerSimulator(method="matrix_product_state", seed_simulator=seed)
    mem = ideal.run(qc, shots=shots, memory=True).result().get_memory()
    b_ideal = np.array([[int(c) for c in s.replace(" ", "")[::-1]] for s in mem], dtype=np.uint8)
    fake = FakeMarrakesh()
    noisy = AerSimulator.from_backend(fake, method="matrix_product_state", seed_simulator=seed)
    isa = transpile(qc, backend=fake, initial_layout=layout, optimization_level=1, seed_transpiler=1)
    mem = noisy.run(isa, shots=shots, memory=True).result().get_memory()
    b_noisy = np.array([[int(c) for c in s.replace(" ", "")[::-1]] for s in mem], dtype=np.uint8)
    return {"ideal": b_ideal, "noisy": b_noisy}


def dist_compare(a: list[dict], b: list[dict]) -> dict:
    out = {}
    for k in ("n_active", "seed_vox", "elong", "extent_vox"):
        x, y = np.array([r[k] for r in a], float), np.array([r[k] for r in b], float)
        ks = stats.ks_2samp(x, y)
        out[k] = {"mean_a": float(x.mean()), "mean_b": float(y.mean()), "sd_a": float(x.std()), "sd_b": float(y.std()),
                  "ks_D": float(ks.statistic), "ks_p": float(ks.pvalue)}
    return out


def tvd_bits(a: np.ndarray, b: np.ndarray) -> float:
    ca, cb = Counter(map(bytes, a)), Counter(map(bytes, b))
    keys = set(ca) | set(cb)
    return 0.5 * sum(abs(ca[k] / len(a) - cb[k] / len(b)) for k in keys)


def part_seeds() -> dict:
    from dscale import seedlift as SL
    qca, hw, patch, params, qrun = _live_context()
    stored = np.load(RUN / "dscale/seed_shapes.npz")
    rng = np.random.default_rng(11)
    per_tile, pooled = [], {"hardware": [], "ideal": [], "noisy": [], "indep": [], "hw_half_a": [], "hw_half_b": []}
    t0 = time.time()
    for qc, bh in zip(qca, hw):
        tid = qc.metadata["tile_id"]
        layout = json.loads(qc.metadata["layout"]) if isinstance(qc.metadata["layout"], str) else qc.metadata["layout"]
        shots = len(bh)
        tw = sample_twins(qc, layout, shots, seed=1000 + len(per_tile))
        marg = bh.mean(0)
        b_ind = (rng.random(bh.shape) < marg).astype(np.uint8)
        arms = {"hardware": bh, "ideal": tw["ideal"], "noisy": tw["noisy"], "indep": b_ind}
        feats = {}
        for name, bits in arms.items():
            fs = []
            for row in bits:
                active = [q for q, v in zip(layout, row) if v]
                fs.append(features(SL.lift(patch, active), row))
            feats[name] = fs
            pooled[name] += fs
        half = shots // 2
        pooled["hw_half_a"] += feats["hardware"][:half]
        pooled["hw_half_b"] += feats["hardware"][half:]
        # reproduction check: the stored seed for this tile must be one of the hardware lifts
        sv = int(stored[tid].sum())
        rep = any(f["seed_vox"] == sv for f in feats["hardware"])
        per_tile.append({"tile": tid, "shots": shots, "stored_seed_vox": sv, "stored_seed_reproducible": rep,
                         "tvd_bits": {n: tvd_bits(bh, arms[n]) for n in ("ideal", "noisy", "indep")},
                         "tvd_bits_hw_split": tvd_bits(bh[:half], bh[half:]),
                         "corr_offdiag_rms": {n: float(np.sqrt(np.nanmean(
                             (np.corrcoef(arms[n].T.astype(float))[np.triu_indices(arms[n].shape[1], 1)]) ** 2)))
                             for n in arms},
                         "mean_seed_vox": {n: float(np.mean([f['seed_vox'] for f in feats[n]])) for n in arms}})
        print(f"  {tid}: TVD hw-ideal {per_tile[-1]['tvd_bits']['ideal']:.3f} hw-noisy {per_tile[-1]['tvd_bits']['noisy']:.3f}"
              f" hw-indep {per_tile[-1]['tvd_bits']['indep']:.3f} split {per_tile[-1]['tvd_bits_hw_split']:.3f}; "
              f"vox {per_tile[-1]['mean_seed_vox']}  ({time.time() - t0:.0f} s)", flush=True)
    res = {"per_tile": per_tile,
           "pooled": {f"hardware_vs_{n}": dist_compare(pooled["hardware"], pooled[n]) for n in ("ideal", "noisy", "indep")}
           | {"hw_split_half": dist_compare(pooled["hw_half_a"], pooled["hw_half_b"])},
           "n_per_arm": len(pooled["hardware"])}
    np.savez_compressed(OUTD / "ct_twin_seed_features.npz",
                        **{f"{n}_{k}": np.array([f[k] for f in pooled[n]]) for n in pooled
                           for k in ("n_active", "seed_vox", "elong", "extent_vox")})
    return res


# ---------------------------------------------------------------- replicate cohorts for rendering
def part_cohort() -> dict:
    from dscale import seedlift as SL
    qca, hw, patch, params, qrun = _live_context()
    made = {}
    for arm in ("quantum", "twin"):
        for k in range(K_REP):
            d = COH / f"{arm}_{k}"
            if d.exists():
                shutil.rmtree(d)
            (d / "dscale").mkdir(parents=True)
            for f in ("cohort_params.json", "quantum_run.json"):
                shutil.copy(RUN / f, d / f)
            for f in ("dscale_run.json", "scale_detail.json", "allocation.json"):
                shutil.copy(RUN / "dscale" / f, d / "dscale" / f)
            rng = np.random.default_rng(100 * k + (0 if arm == "quantum" else 1))
            masks = {}
            for j, (qc, bh) in enumerate(zip(qca, hw)):
                layout = json.loads(qc.metadata["layout"]) if isinstance(qc.metadata["layout"], str) else qc.metadata["layout"]
                if arm == "quantum":
                    row = bh[int(rng.integers(len(bh)))]
                else:
                    from qiskit_aer import AerSimulator
                    mem = AerSimulator(method="matrix_product_state", seed_simulator=int(rng.integers(2 ** 31))) \
                        .run(qc, shots=1, memory=True).result().get_memory()[0]
                    row = np.array([int(c) for c in mem.replace(" ", "")[::-1]], dtype=np.uint8)
                masks[qc.metadata["tile_id"]] = SL.lift(patch, [q for q, v in zip(layout, row) if v])
            np.savez_compressed(d / "dscale/seed_shapes.npz", **masks)
            made[f"{arm}_{k}"] = {t: int(m.sum()) for t, m in masks.items()}
            print(f"  cohort {arm}_{k}: seed vox {list(made[f'{arm}_{k}'].values())}", flush=True)
    return made


def part_render() -> dict:
    """imaging.build_tiles on every replicate cohort, 4 in parallel (≈ 7 min CPU each)."""
    dirs = sorted(p for p in COH.iterdir() if p.is_dir())
    procs, logs = [], {}
    code = REPO / "QuantumPhantoms/code"
    for d in dirs:
        log = open(d / "tiles.log", "w")
        while sum(p.poll() is None for p in procs) >= 4:
            time.sleep(5)
        procs.append(subprocess.Popen([PY, "-m", "imaging.build_tiles", "--run", str(d)], cwd=code, stdout=log,
                                      stderr=subprocess.STDOUT))
        logs[d.name] = str(d / "tiles.log")
    for p in procs:
        p.wait()
    return {"cohorts": [d.name for d in dirs], "returncodes": [p.returncode for p in procs], "logs": logs}


def roi_stats(png: Path, bbox) -> dict:
    from skimage import io
    from skimage.feature import graycomatrix, graycoprops
    im = io.imread(png)
    im = im if im.ndim == 2 else im[..., 0]
    h, w = im.shape
    c = im[h // 2 - 12: h // 2 + 12, w // 2 - 12: w // 2 + 12]
    glcm = graycomatrix(c, [1], [0, np.pi / 2], levels=256, symmetric=True, normed=True)
    p = np.bincount(c.ravel(), minlength=256) / c.size
    return {"roi_mean": float(c.mean()), "roi_sd": float(c.std()), "roi_entropy": float(-(p[p > 0] * np.log2(p[p > 0])).sum()),
            "glcm_contrast": float(graycoprops(glcm, "contrast").mean()),
            "glcm_homogeneity": float(graycoprops(glcm, "homogeneity").mean())}


def part_features() -> dict:
    rows = []
    for d in sorted(p for p in COH.iterdir() if p.is_dir()):
        tj = d / "tiles.json"
        if not tj.exists():
            continue
        arm = d.name.split("_")[0]
        for t in json.loads(tj.read_text())["tiles"]:
            if t.get("renderer") != "grown+fitted":
                continue
            dg = t["diag"]
            rows.append({"cohort": d.name, "arm": arm, "tile": t["tile_id"], "type": t["type"], "size_mm": t["size_mm"],
                         "seed_cells": dg.get("seed_cells"), "diameter_baseline_mm": dg.get("diameter_baseline_mm"),
                         "vdt_d": dg.get("vdt_d"), "day_baseline": dg.get("day_baseline"),
                         "filled_holes_vox": dg.get("filled_holes_vox"), "volume_pd_pct": dg.get("volume_pd_pct"),
                         **roi_stats(d / t["png_path"], t.get("bbox"))})
    keys = ["seed_cells", "diameter_baseline_mm", "vdt_d", "day_baseline", "roi_mean", "roi_sd", "roi_entropy",
            "glcm_contrast", "glcm_homogeneity"]
    comp = {}
    for k in keys:
        q = np.array([r[k] for r in rows if r["arm"] == "quantum" and r[k] is not None], float)
        tw = np.array([r[k] for r in rows if r["arm"] == "twin" and r[k] is not None], float)
        if len(q) and len(tw):
            ks = stats.ks_2samp(q, tw)
            mw = stats.mannwhitneyu(q, tw)
            comp[k] = {"n_q": len(q), "n_twin": len(tw), "mean_q": float(q.mean()), "mean_twin": float(tw.mean()),
                       "sd_q": float(q.std()), "sd_twin": float(tw.std()), "ks_D": float(ks.statistic),
                       "ks_p": float(ks.pvalue), "mw_p": float(mw.pvalue)}
    # paired per tile: quantum-arm mean vs twin-arm mean over replicates
    paired = {}
    for k in ("diameter_baseline_mm", "vdt_d", "roi_mean", "glcm_contrast"):
        diffs = []
        for tile in sorted({r["tile"] for r in rows}):
            q = [r[k] for r in rows if r["tile"] == tile and r["arm"] == "quantum" and r[k] is not None]
            tw = [r[k] for r in rows if r["tile"] == tile and r["arm"] == "twin" and r[k] is not None]
            if q and tw:
                diffs.append(np.mean(q) - np.mean(tw))
        if len(diffs) > 2:
            w = stats.wilcoxon(diffs)
            paired[k] = {"n_tiles": len(diffs), "mean_diff": float(np.mean(diffs)), "wilcoxon_p": float(w.pvalue)}
    print(json.dumps(comp, indent=1)); print(json.dumps(paired, indent=1))
    return {"rows": rows, "unpaired": comp, "paired_per_tile": paired}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=["roll", "roll_noise", "seeds", "cohort", "render", "features"])
    a = ap.parse_args()
    out = OUTD / ("ct_twin.json" if a.part in ("roll", "roll_noise", "seeds") else f"ct_twin_{a.part}.json")
    res = json.loads(out.read_text()) if out.exists() else {}
    res[a.part] = {"roll": part_roll, "roll_noise": part_roll_noise, "seeds": part_seeds, "cohort": part_cohort, "render": part_render,
                   "features": part_features}[a.part]()
    out.write_text(json.dumps(res, indent=1, default=float))
    print("wrote", out)


if __name__ == "__main__":
    main()
