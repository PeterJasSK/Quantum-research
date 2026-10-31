"""D-SCALE MVP orchestrator (AC-15, AC-18): add quantum growth at 40 / 100 / 120 q to any F1 / F4 run.

    python -m dscale.run --run research_runs/<run> --budget 40|100|120 --mode ideal|heron
                         [--recipe composite|ghz-spine|ch-qca|pmd-bank] [--target marrakesh] [--smoke]

Reads `cohort_params.json` + `quantum_run.json` (sampler-blind, epic §3) and writes `research_runs/<run>/dscale/`:
  dscale_run.json (DScaleRun), allocation.json, scale_detail.json, seed_shapes.npz (one 3-D uint8 occupancy per
  tile_id at 0.5 mm = params_lung.json lattice_mm, lifted with dscale.seedlift), circuits/*.qasm, figures/.
Per tile, seeds come from `imaging.seedhash.tile_seeds(run_key, shot_index, generation, raw_bits)` (the function F5
uses); every hidden choice uses a "DS-*" label. The run-level jobs use the first tile's draw, so a different F1 draw
changes the soma angles, the QCA initial set and the transpiled hashes. The same inputs reproduce byte-identically
(scale_detail.json carries the only timestamp).
Refuses (exit 6) to write into a run directory that holds git-tracked files (research_runs/ is not ignored).
Simulation only: nothing here submits to a QPU.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import qasm3

from common.datamodel import DScaleRun, QuantumRun, TumorParams
from dscale import allocate as A, budget as B, families as F, lint as L, survival as S, targets as T
from imaging.seedhash import tile_seeds

ROOT = Path(__file__).resolve().parents[2]                 # QuantumPhantoms/
EXIT_TRACKED = 6
HONEST = ("simulated; the seed shape is a quantum snapshot; growth and image are classical; no classical-hardness "
          "claim")


def resolve_run(arg: str) -> Path:
    for cand in (Path(arg), ROOT / arg, Path.cwd() / arg):
        if cand.is_dir():
            return cand.resolve()
    raise SystemExit(f"--run dir not found: {arg}")


def tracked_files(run_dir: Path) -> list[str]:
    r = subprocess.run(["git", "ls-files", "--", str(run_dir)], cwd=ROOT, capture_output=True, text=True)
    return [x for x in r.stdout.splitlines() if x.strip()]


def load_f1(run_dir: Path) -> tuple[list[TumorParams], QuantumRun]:
    cp, qr = run_dir / "cohort_params.json", run_dir / "quantum_run.json"
    if not (cp.is_file() and qr.is_file()):
        raise SystemExit(f"{run_dir} is missing cohort_params.json / quantum_run.json (not an F1 / F4 run?)")
    params = [TumorParams.from_dict(d) for d in json.loads(cp.read_text())]
    return params, QuantumRun.from_dict(json.loads(qr.read_text()))


def draws(params: list[TumorParams], run: QuantumRun, run_key: str) -> list[dict]:
    out = []
    for p in params:
        geom, app, src = tile_seeds(run_key, p.shot_index, p.generation, run.raw_bits)
        out.append({"tile_id": f"tile_{p.shot_index}_{p.generation}", "size_mm": p.size_mm, "type": p.type,
                    "margin": p.margin, "seed_hex": geom, "seed_hex_appearance": app, "morphology_source": src})
    return out


def save_npz_deterministic(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """np.savez_compressed stamps the wall clock into the zip entries; this writer fixes date_time (AC-18)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for k in sorted(arrays):
            buf = io.BytesIO()
            np.lib.format.write_array(buf, np.ascontiguousarray(arrays[k]), allow_pickle=False)
            zi = zipfile.ZipInfo(f"{k}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, buf.getvalue())


def _clean(o):
    """JSON-safe copy: drops private keys (leading underscore) and numpy scalars."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


def write_qasm(out: Path, name: str, circuits, hashes: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for k, c in enumerate(circuits):
        txt = qasm3.dumps(c)
        f = out / f"{name}_{k:02d}.qasm"
        f.write_text(txt)
        hashes[f.name] = F.circuit_hash(c)


def seed_montage(masks: dict[str, np.ndarray], info: dict, path: Path, label: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    keys = sorted(masks)
    n = len(keys)
    cols = min(6, max(n, 1))
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(2 * cols, 2.2 * rows), squeeze=False)
    for ax in axes.flat:
        ax.set_axis_off()
    for ax, k in zip(axes.flat, keys):
        m = masks[k]
        ax.imshow(m.max(0), cmap="magma", interpolation="nearest")
        i = info.get(k, {})
        ax.set_title(f"{k}\n{int(m.sum())} vox, {i.get('claim_level', '?')}", fontsize=7)
    fig.suptitle(f"D-SCALE quantum seed shapes (max projection, 0.5 mm voxels); {label}", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--budget", type=int, default=40, choices=F.BUDGETS)
    ap.add_argument("--mode", default="ideal", choices=("ideal", "heron"))
    ap.add_argument("--recipe", default="composite", choices=("composite", "ghz-spine", "ch-qca", "pmd-bank"))
    ap.add_argument("--target", default="marrakesh", choices=T.NAMES)
    B.add_args(ap)
    a = ap.parse_args()
    dl = B.check(a, default_repeats=2 if a.smoke else B.REPEATS)
    run_dir = resolve_run(a.run)
    tr = tracked_files(run_dir)
    if tr:
        print(f"refused: {run_dir} holds {len(tr)} git-tracked file(s) (e.g. {tr[0]}); D-SCALE writes only into "
              f"untracked run dirs (research_runs/ is not ignored).")
        return EXIT_TRACKED
    params, qrun = load_f1(run_dir)
    run_key = qrun.job_id or run_dir.name
    tdraws = draws(params, qrun, run_key)
    draw0 = tdraws[0]
    tname = F.mode_target(a.mode, a.target)
    tg = T.get(tname)
    out = run_dir / "dscale"
    for sub in ("circuits", "figures"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    mode = a.mode
    label = T.sim_label(mode)
    print(f"D-SCALE on {run_dir.name}: budget {a.budget}, {a.recipe} on {tg.label}, {label}; {len(params)} tiles; "
          f"shots {a.shots} x repeats {a.repeats}; cap {a.max_minutes} min")

    # ---- allocation + lint
    alloc = A.composite(a.budget, tname, a.recipe)
    A.figure(alloc, out / "figures" / f"allocation_{a.budget}_{tname}.png")
    fams = sorted({r["family"] for r in alloc["regions"].values() if r["family"] != "-"})
    jobs = {f: F.get(f).build(alloc, F.get(f).PRESETS[a.budget] if f != "ghz-spine" else {}, draw0)
            if f != "ch-qca" else F.get(f).build(alloc, F.get(f).PRESETS[a.budget], draw0, tg) for f in fams}
    alloc["lint"] = []
    for f, job in jobs.items():
        try:
            res = L.enforce(job, alloc["regions"], f, tg.graph)
        except L.LintError as e:
            print("lint:", e)
            return L.EXIT_LINT
        alloc["lint"] += [{"family": f} | r for r in res]
    (out / "allocation.json").write_text(json.dumps(_clean(alloc), indent=1))
    print(f"  allocation: used {alloc['n_used']} qubits, min region distance {alloc['min_region_distance']}, "
          f"fitted {alloc['fitted'] or 'none'}; lint ok ({len(alloc['lint'])} checks)")

    grids = S.param_grids(list(F.FAMILIES))
    detail: dict = {"param_grid": grids, "param_grid_sha256": F.grid_sha256(grids), "circuits": {},
                    "references": [], "run_key": run_key, "draw_tile": draw0["tile_id"]}
    claims = []
    hashes: dict = {}

    # ---- families
    if "ghz-spine" in fams:
        from dscale.families import ghz_spine as G
        sp = alloc["regions"]["spine"]
        params_g = {"N": len(sp["qubits"]), "checks": len(alloc["regions"].get("spine_checks", {"qubits": []})["qubits"]),
                    "soma": 0}
        cell = G.run_cell(alloc, params_g, draw0, mode, tname, a.shots, a.repeats, dl)
        if cell:
            write_qasm(out / "circuits", "ghz_spine", cell.pop("_isa")[:3], hashes)
            detail["ghz_spine"] = cell
            claims.append(G.claim(cell))
            print(f"  ghz-spine N={cell['N']} depth {cell['depth']}: F_dfe {cell['F_dfe']:.4f} +- {cell['F_sigma']:.4f} "
                  f"GME {cell['gme']}; kept {cell['kept_fraction']:.3f}; soma theta {cell['soma']['theta_fate']:.3f}")
    if "pmd-bank" in fams:
        from dscale.families import pmd_bank as P
        cell = P.run_cell(alloc, {}, draw0, mode, tname, a.shots, a.repeats, dl, control=True)
        write_qasm(out / "circuits", "pmd_bank", cell.pop("_isa", [])[:3], hashes)
        detail["pmd_bank"] = cell | {"floor": (cell["machines"][0].get("floor") if cell["machines"] else None)}
        claims.append(P.claim(cell))
        for m in cell["machines"]:
            if "gap_over_floor" in m:
                print(f"  pmd-bank {m['k']}: d_KL(q) {m['d_kl_q']:.2e}, gap/floor {m['gap_over_floor']:.2f}, "
                      f"passed {m['passed']}")
    qca_region = None
    if "ch-qca" in fams:
        from dscale.families import ch_qca as Q
        patch = Q.patch_of(alloc, tg)
        qparams = Q.PRESETS[a.budget] | {"t_max": 3, "t_w": 2}
        spq = Q.spec(patch, qparams, draw0)
        n = len(spq["nodes"])
        qca_region = f"{tname}:{n}"
        ex = None
        if not dl.expired():
            twin = mode != "ideal" and n > S.NOISY_REAL_MAX
            qmode = (f"twin:{tname}" if twin else mode) if mode != "ideal" else "ideal"
            echo = [c for c in Q.job_from_spec(spq, qparams, twin=twin) if c.metadata["echo"]]
            try:
                ex = F.execute(echo, qmode, tname, a.shots, F.sim_seed(draw0["seed_hex"], "DS-qca-region"),
                               method=None if n <= 28 or twin else "matrix_product_state", deadline=dl)
            except B.DeadlineHit:
                ex = None
        if ex is not None:
            an = Q.analyse(echo, ex["bits"], spq, a.shots, draw0["seed_hex"])
            write_qasm(out / "circuits", "ch_qca_region", ex["isa"][:2], hashes)
            detail["ch_qca_region"] = {"sites": n, "rule": spq["rule"], "alpha": spq["alpha"], "init": spq["init"],
                                       "echo": an["echo"], "random_band": an["random_band"],
                                       "sim_label": ex["sim_label"],
                                       "swaps": Q.routing_swaps(echo[-1], tname) if tg.backend else 0}
            print(f"  ch-qca region {n} sites: echo F(t) " + ", ".join(f"t{e['t']}={e['F']:.3f}" for e in an["echo"])
                  + f"  ({ex['sim_label']}); SWAPs {detail['ch_qca_region']['swaps']}")
        else:
            dl.skip("ch-qca region echo")

    # ---- seed shapes per tile (the quantum layer shapes the tumour)
    from dscale.families import ch_qca as Q
    masks, seed_tiles = {}, {}
    for d in tdraws:
        if dl.expired():
            dl.skip(f"seed shape {d['tile_id']}")
            continue
        r = Q.seed_shape(tname, mode, d, a.shots, dl, witness=True)
        masks[d["tile_id"]] = r["occupancy"]
        seed_tiles[d["tile_id"]] = {"region": r["region"], "sites": r["sites"], "init": r["init"],
                                    "active": r["active"], "seed_cells": r["seed_cells"], "t": r["t"],
                                    "claim_level": r["claim_level"], "witness_passed": r["witness_passed"],
                                    "negativity_edges": r.get("negativity_edges"), "hashes": r["hashes"],
                                    "type": d["type"], "size_mm": d["size_mm"]}
        print(f"  seed {d['tile_id']:10s} {d['type']:12s} {d['size_mm']:5.1f} mm: init {len(r['init'])} sites -> "
              f"{len(r['active'])}/{r['sites']} active, {r['seed_cells']} vox; witness {r['witness_passed']} "
              f"({r['claim_level']})", flush=True)
    if masks:
        save_npz_deterministic(out / "seed_shapes.npz", masks)
        seed_montage(masks, seed_tiles, out / "figures" / "seed_shapes.png", label)
        passed = [v["witness_passed"] for v in seed_tiles.values() if v["witness_passed"] is not None]
        claims.append({"family": "ch-qca", "claim_level": "L1" if passed and all(passed) else
                       ("L1 (some tiles)" if any(passed) else "L0"),
                       "witness": "QCA seed-region pair negativity (Bonferroni), per tile",
                       "value": float(np.mean(passed)) if passed else None, "sigma": None, "k": 2,
                       "passed": bool(passed) and all(passed), "label": label,
                       "note": f"{sum(passed)}/{len(passed)} tiles pass on the {next(iter(seed_tiles.values()))['region']}"
                               f" seed region; non-Clifford (frontier family); the seed shape is a quantum snapshot, "
                               f"growth is classical"})
    detail["seed_tiles"] = seed_tiles
    detail["circuits"] = hashes

    # ---- Goldilocks verdict from the survival map (dscale.survival) for this budget / target
    smap = S.OUT_DEFAULT / f"survival_{a.budget}_{tname}" / "survival_map.json"
    if smap.exists():
        m = json.loads(smap.read_text())
        zone = [m["cells"][i] for i in m["goldilocks_zone"]]
        gold = {"cells": [{k: c.get(k) for k in ("family", "n_qubits", "depth_or_t", "alpha", "value")} for c in zone],
                "empty": m["goldilocks_empty"], "ref_kinds": sorted({(c.get("bp") or {}).get("ref_kind", "?")
                                                                    for c in m["cells"]}),
                "map": str(smap.relative_to(ROOT)), "n_cells": len(m["cells"]), "truncated": m["truncated"]}
        png = smap.parent / "figures" / f"survival_map_{a.budget}_{tname}.png"
        if png.exists():
            shutil.copy(png, out / "figures" / png.name)
            gold["map_png"] = f"figures/{png.name}"
    else:
        gold = {"cells": [], "empty": None, "ref_kinds": [],
                "note": f"no survival map yet: python -m dscale.survival --budget {a.budget} --target {tname} --smoke"}
    rec = DScaleRun(budget=a.budget, target=tname, mode=mode, sim_label=label, recipe=a.recipe, claims=claims,
                    goldilocks=gold, seed_shapes="seed_shapes.npz" if masks else "", allocation_ref="allocation.json",
                    param_grid_sha256=detail["param_grid_sha256"], shots=a.shots, repeats=a.repeats,
                    truncated=dl.truncated, run_key=run_key)
    d = rec.to_dict() | {"honest_label": HONEST, "target_label": tg.label, "qca_region": qca_region}
    (out / "dscale_run.json").write_text(json.dumps(_clean(d), indent=1))
    detail["created_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    detail["skipped"] = dl.skipped
    (out / "scale_detail.json").write_text(json.dumps(_clean(detail), indent=1))
    print("  claims: " + "; ".join(f"{c['family']} {c['claim_level']} (passed {c['passed']})" for c in claims))
    print(f"  Goldilocks zone: {'empty' if gold.get('empty') else gold.get('cells') or gold.get('note')}")
    print(f"wrote {out}\n" + dl.report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
